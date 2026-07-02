# Velocity command publisher

**Epic:** ROS 2 Simulation and Robot Control Skeleton (102) · **Jira epic:** VLA-3 · **Story:** VLA-25 / 1013 · **Subtasks:** 10039 (publisher), 10040 (twist helpers), 10041 (sim test)

**Human-readable version (browser):** [`velocity-command-publisher.html`](velocity-command-publisher.html)

## Executive summary

`CmdVelPublisher` is the shared **actuation sink** for Epic 102: any node that needs to move the robot should call this library rather than publishing `geometry_msgs/Twist` directly. `clamp_velocity()` enforces MVP limits before messages reach `/cmd_vel`, keeping dummy, heartbeat, tester, and future model paths aligned with `ros2_control.yml`.

## API contract and data flow

```text
caller (tester / heartbeat / legacy direct use)
    ──> CmdVelPublisher.publish_twist(linear_x, angular_z)
    ──> clamp_velocity()
    ──> geometry_msgs/Twist
    ──> /cmd_vel
    ──> diffdrive_controller (Webots)
```

| Parameter | Default | Notes |
|-----------|---------|-------|
| `cmd_vel_topic` | `/cmd_vel` | Matches `configs/default.example.yaml` |
| `max_linear_vel` | `0.2` | Matches `resource/ros2_control.yml` |
| `max_angular_vel` | `0.6` | Webots diff-drive limit |

**Invariant:** Published twists never exceed configured maxima; `publish_stop()` always sends zeros.

## Implementation breakdown

### Twist helpers (`twist_utils.py`)

```python
def clamp_velocity(linear_x, angular_z, *, max_linear_vel, max_angular_vel):
    ...
def make_twist(linear_x, angular_z) -> Twist:
    ...
```

Pure functions — fully covered by `test_twist_utils.py` without ROS runtime.

### Publisher class (`cmd_vel_publisher.py`)

```python
publisher = CmdVelPublisher(node, cmd_vel_topic="/cmd_vel")
publisher.publish_twist(0.15, 0.0)
publisher.publish_stop()
```

- **Design note:** Accepts a `rclpy.Node` so heartbeat and testers share one implementation.
- **Gotcha:** Post–VLA-27 architecture routes most traffic through `heartbeat_controller`; direct `/cmd_vel` publish is for tests and legacy paths.

### Sim tester (`cmd_vel_tester.py`, subtask 10041)

Cycles forward → left → right → stop with `step_duration_sec` dwell (default 2 s).

| Step | linear.x | angular.z |
|------|----------|-----------|
| forward | 0.15 | 0 |
| turn_left | 0 | 0.4 |
| turn_right | 0 | -0.4 |
| stop | 0 | 0 |

## Verification patterns

```bash
colcon test --packages-select litevla_bridge
./ros_ws/scripts/run_webots_mvp.sh
ros2 launch litevla_bridge cmd_vel_test.launch.py
ros2 topic echo /cmd_vel
```

## Related

- [camera-frame-subscriber.md](camera-frame-subscriber.md) (VLA-24)
- [control-heartbeat.md](control-heartbeat.md) (VLA-27)
