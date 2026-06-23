# Low-level control heartbeat

**Epic:** ROS 2 Simulation and Robot Control Skeleton (102) · **Jira:** VLA-27 / Story 1015 · **Subtasks:** 10045 (timer), 10046 (timeouts), 10047 (diagnostics)

**Human-readable version (browser):** [`control-heartbeat.html`](control-heartbeat.html)

Publish `/cmd_vel` at a fixed rate from the latest desired command, with safety timeouts and diagnostics.

## Intent

Decouple slow action sources (dummy actions, future VLA model) from the steady command rate the diff-drive controller expects.

## Architecture

```text
dummy_action_generator → /litevla/desired_twist + /litevla/current_action
camera (/image_raw)    → heartbeat (frame freshness)
heartbeat_controller   → /cmd_vel + /litevla/diagnostics
```

## Artifacts

| Path | Purpose |
|------|---------|
| `litevla_bridge/heartbeat_controller.py` | Fixed-rate publisher + timeouts |
| `litevla_bridge/heartbeat_utils.py` | Pure timeout/diagnostics helpers |
| `launch/heartbeat.launch.py` | Standalone heartbeat node |
| `launch/dummy_sim.launch.py` | Webots + heartbeat + dummy (updated) |
| `test/test_heartbeat_utils.py` | Unit tests |

## Parameters

| Param | Default | Notes |
|-------|---------|-------|
| `heartbeat_hz` | `10.0` | Publish frequency (`runtime.heartbeat_hz`) |
| `cmd_vel_topic` | `/cmd_vel` | Output velocity commands topic |
| `desired_twist_topic` | `/litevla/desired_twist` | Input desired velocity commands topic |
| `current_action_topic` | `/litevla/current_action` | Input action name topic |
| `image_topic` | `/image_raw` | Input camera frames topic |
| `action_timeout_sec` | `0.5` | No fresh action command → STOP |
| `frame_timeout_sec` | `2.0` | No camera frame → STOP |
| `require_frame` | `true` | Set `false` for cmd-only bench tests |
| `max_linear_vel` | `0.2` | Maximum linear velocity limit |
| `max_angular_vel` | `0.6` | Maximum angular velocity limit |
| `control_mode` | `dummy` | Control mode (`dummy`, `teleop`, or `model`) |
| `diagnostics_topic` | `/litevla/diagnostics` | JSON string diagnostic telemetry topic |

## Diagnostics JSON

```json
{
  "heartbeat_hz": 10.0,
  "last_cmd": "MOVE_FORWARD",
  "last_publish_stamp": "123.456789000",
  "action_age_ms": 12.3,
  "frame_age_ms": 45.0,
  "timed_out": false,
  "control_mode": "dummy"
}
```

## Run

```bash
source ros_ws/install/setup.bash
ros2 launch litevla_bridge dummy_sim.launch.py
ros2 topic echo /litevla/diagnostics --once
ros2 topic hz /cmd_vel
```

## Validation

```bash
colcon test --packages-select litevla_bridge
ros2 topic hz /cmd_vel                    # ~10 Hz
# Stop camera or dummy → timed_out true → cmd_vel zero
```

## Related

- [dummy-action-generator.md](dummy-action-generator.md) (VLA-26)
- [velocity-command-publisher.md](velocity-command-publisher.md) (VLA-25)
