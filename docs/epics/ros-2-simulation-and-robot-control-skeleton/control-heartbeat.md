# Low-level control heartbeat

**Epic:** ROS 2 Simulation and Robot Control Skeleton (102) · **Jira epic:** VLA-3 · **Story:** VLA-27 / 1015 · **Subtasks:** 10045 (timer), 10046 (timeouts), 10047 (diagnostics)

**Human-readable version (browser):** [`control-heartbeat.html`](control-heartbeat.html)

## Executive summary

`heartbeat_controller` is the **safety and timing layer** between slow action sources and the diff-drive controller. It republishes the latest desired twist on `/cmd_vel` at a fixed rate, enforces action and camera freshness timeouts, clamps velocities, and emits JSON diagnostics. Every Epic 102 command source (dummy, teleop, future model) converges here before actuation.

## API contract and data flow

```text
/litevla/desired_twist  ──┐
/litevla/current_action ──┼──> heartbeat_controller (timer @ heartbeat_hz)
/image_raw (optional)   ──┘         │
                                      ├──> clamp + timeout gate
                                      ├──> /cmd_vel
                                      └──> /litevla/diagnostics (JSON)
```

| Parameter | Default | Notes |
|-----------|---------|-------|
| `heartbeat_hz` | `10.0` | Teleop stack uses `25.0` for lower latency |
| `action_timeout_sec` | `0.5` | Teleop uses `0.2` |
| `frame_timeout_sec` | `2.0` | Stale camera → STOP |
| `require_frame` | `true` | `false` for teleop / cmd-only benches |
| `control_mode` | `dummy` | `dummy` \| `teleop` \| `model` |
| `teleop_startup_grace_sec` | `0.0` | `20.0` in teleop script — avoids immediate STOP before keys |

**Invariant:** On timeout or mode mismatch, published twist is zero (`STOP`).

## Implementation breakdown

### Pure helpers (`heartbeat_utils.py`)

```python
def is_timed_out(age_sec, timeout_sec) -> bool: ...
def select_velocities(desired, *, timed_out, ...) -> tuple[float, float]: ...
def build_diagnostics(...) -> dict: ...
```

Unit-tested without ROS — documents timeout math explicitly.

### Controller node (`heartbeat_controller.py`)

- Uses `CmdVelPublisher` (VLA-25) for all `/cmd_vel` output.
- Subscribes desired twist, action label, and optionally camera with sensor QoS.
- `control_mode` gate: ignores sources not matching active mode.

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

## Related

- [dummy-action-generator.md](dummy-action-generator.md) (VLA-26)
- [manual-teleoperation.md](manual-teleoperation.md) (VLA-28)
