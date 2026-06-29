# Velocity command publisher

**Epic:** ROS 2 Simulation and Robot Control Skeleton (102) · **Jira:** VLA-25 / Story 1013 · **Subtasks:** 10039 (publisher), 10040 (twist helpers), 10041 (sim test)

**Human-readable version (browser):** [`velocity-command-publisher.html`](velocity-command-publisher.html)

Publish diff-drive movement commands on `/cmd_vel` with safety clamping — the actuation output side of the robot loop.

## Intent

Provide a reusable publisher that dummy actions, heartbeat, and teleop nodes can call. Clamp velocities before publishing so commands stay within simulator limits.

## Artifacts

| Path | Purpose |
|------|---------|
| `litevla_bridge/cmd_vel_publisher.py` | `CmdVelPublisher` class + optional standalone node |
| `litevla_bridge/twist_utils.py` | `make_twist()`, `clamp_velocity()` |
| `litevla_bridge/cmd_vel_tester.py` | Cycles forward / left / right / stop in sim |
| `launch/cmd_vel_test.launch.py` | Launch movement test sequence |
| `test/test_twist_utils.py` | Unit tests (no ROS runtime) |

## Parameters

| Param | Default | Notes |
|-------|---------|-------|
| `cmd_vel_topic` | `/cmd_vel` | Matches `configs/default.example.yaml` |
| `max_linear_vel` | `0.2` | Aligns with `resource/ros2_control.yml` |
| `max_angular_vel` | `0.6` | Aligns with Webots diff-drive limits |
| `step_duration_sec` | `2.0` | Tester dwell time per command |

## Usage (library)

```python
from litevla_bridge.cmd_vel_publisher import CmdVelPublisher

publisher = CmdVelPublisher(node, cmd_vel_topic="/cmd_vel")
publisher.publish_twist(0.15, 0.0)   # forward
publisher.publish_stop()
```

## Run (sim test)

```bash
source /opt/ros/jazzy/setup.bash
source ros_ws/install/setup.bash

# Terminal 1
./ros_ws/scripts/run_webots_mvp.sh

# Terminal 2
ros2 launch litevla_bridge cmd_vel_test.launch.py
```

**Pass:** Robot moves forward, turns left, turns right, stops in Webots; logs show each step.

## Test matrix (subtask 10041)

| Step | linear.x | angular.z | Expected |
|------|----------|-----------|----------|
| forward | 0.15 | 0 | Robot advances |
| turn_left | 0 | 0.4 | Rotates left |
| turn_right | 0 | -0.4 | Rotates right |
| stop | 0 | 0 | Halts |

## Validation

```bash
colcon test --packages-select litevla_bridge   # test_twist_utils.py
ros2 topic echo /cmd_vel                       # while tester runs
```

## Related

- [camera-frame-subscriber.md](camera-frame-subscriber.md) (VLA-24)
- [webots-sim-environment.md](webots-sim-environment.md) (VLA-23)
