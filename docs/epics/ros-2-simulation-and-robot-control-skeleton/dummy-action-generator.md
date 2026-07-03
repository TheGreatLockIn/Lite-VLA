# Dummy action generator

**Epic:** ROS 2 Simulation and Robot Control Skeleton (102) · **Jira epic:** VLA-3 · **Story:** VLA-26 / 1014 · **Subtasks:** 10042 (forward), 10043 (sequence), 10044 (dummy mode config)

**Human-readable version (browser):** [`dummy-action-generator.html`](dummy-action-generator.html)

## Executive summary

`dummy_action_generator` is the **pre-ML command source** for Epic 102: it steps through a configurable list of Epic 103 discrete actions, maps each to nominal velocities via `action_to_twist()`, and publishes **desired twists** for the heartbeat—not `/cmd_vel` directly. This proves the full perception–action loop before Epic 104/108 connect a VLA model.

## Mental model

Think of this node as **a scripted stand-in for the future VLA model**.

It exists because the team needs to validate ROS wiring, heartbeat timing, and action vocabulary before ML inference exists.

The key engineering tension is **slow, discrete action steps vs continuous diff-drive control**—resolved by publishing intent and letting the heartbeat republish steadily.

A beginner mistake is making the dummy publish `/cmd_vel`, bypassing timeouts and creating a second actuation owner.

A senior engineer watches **`control_mode` gates** so teleop and dummy never compete as active sources.

## Backstory: why this exists

Before this module existed, developers could move the robot with `cmd_vel_tester` or manual twists, but nothing exercised the Epic 103 discrete action vocabulary through the full stack.

The naive solution would be a ROS node that maps `MOVE_FORWARD` directly to `/cmd_vel` every two seconds.

That breaks because diff-drive controllers expect steady commands; one-shot publishes cause jerky motion, and there is no shared path with teleop or the future model.

So this design chooses **`/litevla/desired_twist` + `/litevla/current_action`** consumed by `heartbeat_controller` (VLA-27).

This pattern appears in real systems as **intent vs actuation separation**.

## Prerequisites

- [action-schema.md](../action-interface-parser-and-safety-layer/action-schema.md) — `DiscreteAction`, `action_to_twist()`.
- [control-heartbeat.md](control-heartbeat.md) — consumes desired twist.
- [velocity-command-publisher.md](velocity-command-publisher.md) — owns `/cmd_vel`.

## Concept primer / vocabulary

| Term | Meaning in this project |
|------|-------------------------|
| **`desired_twist`** | Intent: what motion the active source wants now (`geometry_msgs/Twist`). |
| **`/cmd_vel`** | Actuation: what the robot actually receives at fixed rate. |
| **`control_mode`** | `dummy` \| `teleop` \| `model` — which source is active. |
| **`action_sequence`** | Ordered list of Epic 103 tokens to step through. |
| **`sequence_step_sec`** | Dwell time between sequence advances. |
| **`action_to_twist()`** | Maps discrete token + limits → `(linear_x, angular_z)`. |

## Guided code reading

Read these in order:

1. `litevla/actions/schema.py` (or `litevla_bridge/action_schema.py` shim)
   - `DEFAULT_ACTION_SEQUENCE`, `action_to_twist`.

2. `litevla_bridge/dummy_action_generator.py`
   - `control_mode` gate, timer stepping, publishers.

3. `launch/dummy_sim.launch.py`
   - Brings dummy + heartbeat + sim together.

4. `scripts/run_dummy_pipeline.py`
   - Offline print of the same sequence (no ROS).

While reading, ask:

- Where does data enter?
- Who owns `/cmd_vel`?
- What happens when `control_mode` is not `dummy`?

## File and artifact index

| File or artifact | What it is | Why it matters | First thing to inspect |
|------------------|------------|----------------|------------------------|
| `dummy_action_generator.py` | ROS timer node | Publishes intent topics | `_on_sequence_step` |
| `action_schema.py` | Import shim to `litevla.actions` | Single vocabulary | `action_to_twist` |
| `launch/dummy_sim.launch.py` | Integrated smoke | Dummy + heartbeat + sim | `control_mode` params |
| `scripts/run_dummy_pipeline.py` | Offline script | No ROS proof of sequence | Printed twists |
| `configs/default.example.yaml` | Config mirror | `runtime.action_sequence` | `runtime` section |

## API contract and data flow

### What "contract" means here

**Contract** = when `control_mode:=dummy`, the node steps through `action_sequence` every `sequence_step_sec`, publishing clamped twists and uppercase action labels on the desired topics. It never publishes `/cmd_vel`.

### Task-local flow

```text
action_sequence (config / param)
    ──> dummy_action_generator (timer per step)
    ──> action_to_twist(DiscreteAction)
    ──> /litevla/desired_twist + /litevla/current_action
    ──> heartbeat_controller
    ──> /cmd_vel
```

### Contract table

| Row label | Meaning |
|-----------|---------|
| **Parameter** | ROS parameter. |
| **Default** | Value when unset. |
| **Config mirror** | YAML key in project config. |

| Parameter | Default | Config mirror |
|-----------|---------|---------------|
| `control_mode` | `dummy` | `runtime.mode` — node idles otherwise |
| `action_sequence` | forward → forward → left → stop | `runtime.action_sequence` |
| `sequence_step_sec` | `2.0` | `runtime.sequence_step_sec` |
| `desired_twist_topic` | `/litevla/desired_twist` | Consumed by VLA-27 |

**Invariant:** Action names are uppercase Epic 103 tokens only (`MOVE_FORWARD`, `TURN_LEFT`, …).

### Naive approach vs chosen approach

| Approach | Why it seems attractive | Why we did or did not choose it |
|----------|-------------------------|---------------------------------|
| Dummy publishes `/cmd_vel` directly | Simpler graph | Bypasses heartbeat safety and timing |
| Publish `desired_twist` only | Extra node required | Same path as teleop and future model |
| Hardcoded twists in dummy node | No Epic 103 dependency | Forks vocabulary from datasets and parser |
| Shared `action_to_twist()` | Import coupling | One nominal velocity table |

## Implementation breakdown

### Shared schema bridge

| Path | Role |
|------|------|
| `litevla/actions/schema.py` | Canonical `DiscreteAction`, `action_to_twist()` |
| `litevla_bridge/action_schema.py` | ROS package import shim |
| `scripts/run_dummy_pipeline.py` | Offline print of the same sequence (no ROS) |

Single vocabulary for dummy ROS, offline scripts, future parser (Epic 103), and dataset labels (Epic 105).

### ROS node (`dummy_action_generator.py`)

```python
if control_mode != "dummy":
    self.get_logger().warn(
        f"control_mode={control_mode!r} — dummy generator idling ..."
    )
    self._active = False
    return
```

**What to notice:** Publishes twist + string action label each step; idles when mode mismatches.

**Why it is written this way:** Respects `control_mode` gates so teleop can take over without duplicate publishers.

**Risks and gotchas:** `runtime_mode` is a deprecated alias for `control_mode`—prefer `control_mode` in new launch files.

## Engineering decisions

**ADR: Publish desired twist, not cmd_vel**

- **Status:** Accepted (VLA-27)
- **Context:** Action sources update slowly; diff-drive expects steady commands.
- **Decision:** Dummy publishes `/litevla/desired_twist`; heartbeat owns `/cmd_vel`.
- **Consequences:** All future sources (teleop, model) follow the same pattern.

## Verification patterns

```bash
pytest tests/test_action_schema.py -q
python scripts/run_dummy_pipeline.py
colcon test --packages-select litevla_bridge
ros2 launch litevla_bridge dummy_sim.launch.py
```

| Contract defended | Where |
|-------------------|-------|
| Token vocabulary | `test_action_schema.py` |
| Sequence → twist offline | `run_dummy_pipeline.py` |
| ROS integration | `dummy_sim.launch.py` |

## Failure modes and debugging path

| Symptom | Likely cause | How to investigate | Fix |
|---------|--------------|--------------------|-----|
| Dummy logs "idling" | `control_mode` not `dummy` | Check launch params | Set `control_mode:=dummy` |
| Robot still | Heartbeat not running or timed out | `ros2 topic echo /litevla/diagnostics` | Launch heartbeat; check timeouts |
| `ValueError` on action | Invalid token in sequence | Inspect `action_sequence` param | Use Epic 103 uppercase tokens |
| Motion once then stop | Single-action sequence | Check sequence length | Add steps or increase dwell |
| Competing motion | Teleop also active | Check `control_mode` on all nodes | One mode at a time |

## Engineering principle taught by this task

This task teaches **intent/actuation separation**: slow, event-driven sources publish desired state; a dedicated controller owns timing, clamps, and the final actuation topic.

## Active learning checks

1. Why does dummy not call `CmdVelPublisher`?
2. What topics does dummy publish, and who subscribes?
3. How does `control_mode` prevent fighting with teleop?
4. Why reuse `action_to_twist()` instead of inline velocities?

## Small modification exercise

Change `action_sequence` to `["MOVE_FORWARD", "TURN_LEFT", "STOP"]` in launch params. Run `dummy_sim.launch.py` and verify `/litevla/current_action` steps through labels while `/cmd_vel` stays steady at heartbeat rate.

## Related

- [action-schema.md](../action-interface-parser-and-safety-layer/action-schema.md) (VLA-29)
- [control-heartbeat.md](control-heartbeat.md) (VLA-27)
