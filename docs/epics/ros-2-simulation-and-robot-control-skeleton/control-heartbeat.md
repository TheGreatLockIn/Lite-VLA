# Low-level control heartbeat

**Epic:** ROS 2 Simulation and Robot Control Skeleton (102) · **Jira epic:** VLA-3 · **Story:** VLA-27 / 1015 · **Subtasks:** 10045 (timer), 10046 (timeouts), 10047 (diagnostics)

**Human-readable version (browser):** [`control-heartbeat.html`](control-heartbeat.html)

## Executive summary

`heartbeat_controller` is the **safety and timing layer** between slow action sources and the diff-drive controller. It republishes the latest desired twist on `/cmd_vel` at a fixed rate, enforces action and camera freshness timeouts, clamps velocities, and emits JSON diagnostics. Every Epic 102 command source (dummy, teleop, future model) converges here before actuation.

This node is the **single owner of `/cmd_vel`** in integrated stacks—not teleop, not dummy.

## Mental model

Think of the heartbeat as **the robot's reflex arc**: it keeps sending the last safe command until told otherwise, and slams to STOP when inputs go stale.

It exists because keyboard and model outputs are irregular, but `ros2_control` diff-drive expects continuous commands.

The key engineering tension is **responsiveness vs safety**—tighter timeouts stop faster but feel twitchy in teleop.

A beginner mistake is publishing `/cmd_vel` from teleop or dummy "just to test," bypassing timeouts and competing with the heartbeat.

A senior engineer watches **`timed_out` in diagnostics**, `control_mode` alignment, and heartbeat rate vs action source rate.

## Backstory: why this exists

Before this module existed, each command source could publish `/cmd_vel` at its own rate. Keyboard polling at 50 Hz and dummy steps every 2 s produced jerky motion; stale commands could persist after a source crashed.

The naive solution would be to increase publish rates in every source.

That breaks because safety logic duplicates, races persist, and no single place owns STOP-on-stale behavior.

So this design chooses a **timer-driven heartbeat** that subscribes to `/litevla/desired_twist`, optionally watches `/image_raw`, and publishes clamped `/cmd_vel` via `CmdVelPublisher`.

This pattern appears in real systems as **watchdog-controlled actuation gateways**.

## Prerequisites

- [velocity-command-publisher.md](velocity-command-publisher.md) — `CmdVelPublisher`.
- [dummy-action-generator.md](dummy-action-generator.md) and [manual-teleoperation.md](manual-teleoperation.md) — intent publishers.
- [camera-frame-subscriber.md](camera-frame-subscriber.md) — optional frame freshness.

## Concept primer / vocabulary

| Term | Meaning in this project |
|------|-------------------------|
| **`desired_twist`** | Latest intent from the active source (`geometry_msgs/Twist`). |
| **`/cmd_vel`** | Actuation output; only heartbeat should publish here in production. |
| **`heartbeat_hz`** | Timer rate for republishing `/cmd_vel`. |
| **`action_timeout_sec`** | Max age of desired twist before STOP. |
| **`frame_timeout_sec`** | Max age of camera frame when `require_frame:=true`. |
| **`control_mode`** | Gate: only process matching source (`dummy`, `teleop`, `model`). |
| **`/litevla/diagnostics`** | JSON string with ages, mode, timeout flag. |
| **`CommandSmoother`** | Optional rate limiter on velocity changes. |

## Guided code reading

Read these in order:

1. `litevla_bridge/heartbeat_utils.py`
   - `is_timed_out`, `select_velocities`, `build_diagnostics` — pure logic.

2. `test/test_heartbeat_utils.py`
   - Executable spec for timeout math.

3. `litevla_bridge/heartbeat_controller.py`
   - Subscriptions, timer callback, `CmdVelPublisher` usage.

4. `launch/heartbeat.launch.py` and `launch/dummy_sim.launch.py`
   - Parameter sets for dummy vs teleop stacks.

While reading, ask:

- Where does data enter?
- Where is it validated?
- Who owns the final side effect?
- What happens if the upstream producer crashes mid-command?

## File and artifact index

| File or artifact | What it is | Why it matters | First thing to inspect |
|------------------|------------|----------------|------------------------|
| `heartbeat_utils.py` | Pure timeout/smoothing helpers | Testable without ROS | `select_velocities` |
| `heartbeat_controller.py` | Main ROS node | Single `/cmd_vel` owner | Timer callback |
| `cmd_vel_publisher.py` | Actuation sink | Called only from heartbeat in prod | `publish_twist` |
| `test/test_heartbeat_utils.py` | Unit tests | Timeout contracts | Stale input cases |
| `launch/heartbeat.launch.py` | Standalone launch | Parameter defaults | `heartbeat_hz` |

## API contract and data flow

### What "contract" means here

**Contract** = at `heartbeat_hz`, publish a clamped `Twist` on `/cmd_vel` reflecting the latest **safe** desired velocities. If action or required frame is stale, or `control_mode` mismatches, publish zero velocity. Emit diagnostics JSON each tick.

### Task-local flow

```text
/litevla/desired_twist  ──┐
/litevla/current_action ──┼──> heartbeat_controller (timer @ heartbeat_hz)
/image_raw (optional)   ──┘         │
                                      ├──> clamp + timeout gate
                                      ├──> /cmd_vel
                                      └──> /litevla/diagnostics (JSON)
```

### Contract table

| Row label | Meaning |
|-----------|---------|
| **Parameter** | ROS parameter. |
| **Default** | Typical value in repo. |
| **Notes** | Mode-specific overrides. |

| Parameter | Default | Notes |
|-----------|---------|-------|
| `heartbeat_hz` | `10.0` | Teleop stack uses `25.0` for lower latency |
| `action_timeout_sec` | `0.5` | Teleop uses `0.2` |
| `frame_timeout_sec` | `2.0` | Stale camera → STOP |
| `require_frame` | `true` | `false` for teleop / cmd-only benches |
| `control_mode` | `dummy` | `dummy` \| `teleop` \| `model` |
| `teleop_startup_grace_sec` | `0.0` | `20.0` in teleop script — avoids immediate STOP before keys |

**Invariant:** On timeout or mode mismatch, published twist is zero (`STOP`).

### Naive approach vs chosen approach

| Approach | Why it seems attractive | Why we did or did not choose it |
|----------|-------------------------|---------------------------------|
| Direct publish from each source | Fewer nodes | Jerky motion; race conditions; duplicated safety |
| Single heartbeat owner | Adds routing step | One safety boundary; steady `/cmd_vel` |
| No camera timeout | Simpler teleop setup | Blind motion if perception dies — `require_frame` optional |
| High heartbeat rate always | Lower latency | CPU cost; teleop tunes 25 Hz vs dummy 10 Hz |

## Implementation breakdown

### Pure helpers (`heartbeat_utils.py`)

```python
def is_timed_out(age_sec, timeout_sec) -> bool: ...
def select_velocities(desired, *, timed_out, ...) -> tuple[float, float]: ...
def build_diagnostics(...) -> dict: ...
```

**What to notice:** Timeout math is testable without spinning ROS.

**Why it is written this way:** Documents safety policy in one place.

**Risks and gotchas:** `select_velocities` must return zeros when any gate trips—tests should cover combinations.

### Controller node (`heartbeat_controller.py`)

**What to notice:** Uses `CmdVelPublisher` (VLA-25) for all `/cmd_vel` output. Subscribes desired twist, action label, and optionally camera with sensor QoS. `control_mode` gate ignores sources not matching active mode.

**Why it is written this way:** Single actuation path with shared clamps.

**Risks and gotchas:** `CommandSmoother` adds latency—disable for latency debugging. Initial state is timed out until first valid message.

### Diagnostics JSON

```json
{
  "heartbeat_hz": 25.0,
  "last_cmd": "MOVE_FORWARD",
  "action_age_ms": 12.3,
  "frame_age_ms": 45.0,
  "timed_out": false,
  "control_mode": "teleop"
}
```

## Engineering decisions

**ADR: Fixed-rate cmd_vel publisher**

- **Status:** Accepted
- **Context:** Model and keyboard inputs are event-driven; `ros2_control` expects continuous commands.
- **Decision:** Timer-driven republish of last safe command.
- **Alternatives rejected:** Direct publish from each source (jerky motion, race conditions).
- **Consequences:** Tune `heartbeat_hz` and `action_timeout_sec` per mode (teleop vs dummy).

## Verification patterns

```bash
colcon test --packages-select litevla_bridge   # test_heartbeat_utils.py
ros2 launch litevla_bridge dummy_sim.launch.py
ros2 topic hz /cmd_vel
ros2 topic echo /litevla/diagnostics --once
```

Stop dummy node or camera → `timed_out: true` → zero `/cmd_vel`.

| Contract defended | Where |
|-------------------|-------|
| Stale action → STOP | `test_heartbeat_utils.py` |
| Steady `/cmd_vel` rate | `ros2 topic hz` |
| Diagnostics truthfulness | Echo JSON while starving input |

## Failure modes and debugging path

| Symptom | Likely cause | How to investigate | Fix |
|---------|--------------|--------------------|-----|
| Robot does not move | Heartbeat timed out or wrong mode | `ros2 topic echo /litevla/diagnostics` | Match `control_mode`; press keys / start dummy |
| Immediate STOP in teleop | `action_timeout` too tight | Check `action_age_ms` in diagnostics | Use teleop script params; grace period |
| STOP despite driving | `require_frame` + stale camera | `frame_age_ms` in diagnostics | Set `require_frame:=false` for cmd-only |
| Jerky motion | Multiple `/cmd_vel` publishers | `ros2 topic info /cmd_vel` | Remove direct publishers from sources |
| `/cmd_vel` hz ≠ heartbeat | Another node publishing | List publishers | Stop tester nodes |

## Engineering principle taught by this task

This task teaches the **single owner of side effects** pattern: many producers may express intent; one gateway converts intent into steady, safe actuation with explicit timeout policy.

## Active learning checks

1. Why does this component subscribe to intent instead of being the keyboard node?
2. What happens if the upstream producer crashes mid-command?
3. Which component detects stale data?
4. How would you test that stale data becomes safe output?

## Small modification exercise

Set `action_timeout_sec:=1.0` in dummy launch. Run dummy sim, kill the dummy node mid-sequence, and confirm diagnostics show `timed_out: true` within ~1 s and `/cmd_vel` goes to zero.

## Related

- [dummy-action-generator.md](dummy-action-generator.md) (VLA-26)
- [manual-teleoperation.md](manual-teleoperation.md) (VLA-28)
- [velocity-command-publisher.md](velocity-command-publisher.md) (VLA-25)
