# LiteVLA-Edge Learning Progress

Use this file as your project notebook. Each checkpoint should end with a command
you can run, an observation you can explain, and a small artifact in the repo.

## Current Goal

Build understanding from the bottom up:

1. ROS 2 runtime and workspace basics.
2. Topics, messages, and launch files.
3. Camera frames on `/image_raw`.
4. Safe action parsing into `/cmd_vel`.
5. Logging image/instruction/action examples for a dataset.
6. Baseline VLM inference.
7. Fine-tuning, quantization, and deployment.

## Progress Checklist

| Status | Step | What You Should Understand | Proof |
| --- | --- | --- | --- |
| Done | Install ROS 2 Jazzy | What `/opt/ros/jazzy/setup.bash` does and why `ROS_DISTRO=jazzy` matters | `ros2 --help`, `printenv ROS_DISTRO` |
| Done | Create ROS 2 package | How `package.xml`, `setup.py`, and entry points define a Python ROS package | `colcon build --packages-select litevla_edge` |
| Done | Publish velocity commands | How `geometry_msgs/Twist` controls linear and angular velocity | `ros2 topic echo /cmd_vel` |
| Done | Add discrete action schema | Why model output should be constrained before controlling a robot | `colcon test --packages-select litevla_edge` |
| Done | Add safety fallback | Why invalid model text maps to `STOP` | `pytest` parser tests pass |
| Done | Add simulated camera source | How a node publishes `sensor_msgs/Image` on `/image_raw` | `ros2 topic hz /image_raw` |
| Next | Inspect ROS graph | How nodes and topics connect at runtime | `ros2 node list`, `ros2 topic list`, `rqt_graph` if installed |
| Next | Read image metadata | What height, width, encoding, timestamp, and frame ID mean | `ros2 topic echo /image_raw --once` |
| Next | Add frame/action logger | How runtime data becomes a training dataset | `data/sessions/.../labels.jsonl` and saved frames |
| Later | Add baseline VLM service | How image + instruction becomes an action label | Local script returns a valid action |
| Later | Integrate VLM with ROS | How to replace dummy action with model output | `/cmd_vel` changes from model predictions |

## Session 1: ROS 2 Runtime Basics

### Commands

```bash
source /opt/ros/jazzy/setup.bash
ros2 --help
printenv ROS_DISTRO
```

### Questions To Answer

- What does sourcing `/opt/ros/jazzy/setup.bash` change in your shell?
- Why does `ros2` fail before the environment is sourced?
- What is the difference between an installed ROS package and a workspace package?

### Notes

- ROS 2 Jazzy is installed under `/opt/ros/jazzy`.
- This prototype workspace is at `/home/rach.dev/ros2_lyrical/litevla_edge_ws`.

## Session 2: Build And Source The Workspace

### Commands

```bash
cd /home/rach.dev/ros2_lyrical/litevla_edge_ws
source /opt/ros/jazzy/setup.bash
colcon build --packages-select litevla_edge --symlink-install
source install/setup.bash
ros2 pkg prefix litevla_edge
```

### Questions To Answer

- What does `colcon build` create?
- Why do you source both `/opt/ros/jazzy/setup.bash` and `install/setup.bash`?
- What does `--symlink-install` make easier during development?

### Notes

- `/opt/ros/jazzy` is the base ROS installation.
- `install/setup.bash` overlays your local package on top of the base installation.

## Session 3: Topics And Messages

### Commands

```bash
cd /home/rach.dev/ros2_lyrical/litevla_edge_ws
source /opt/ros/jazzy/setup.bash
source install/setup.bash
ros2 run litevla_edge dummy_controller --ros-args -p dummy_action:=TURN_LEFT
```

In another terminal:

```bash
source /opt/ros/jazzy/setup.bash
ros2 topic list
ros2 topic info /cmd_vel
ros2 topic echo /cmd_vel
ros2 interface show geometry_msgs/msg/Twist
```

### Questions To Answer

- What node publishes `/cmd_vel`?
- What message type does `/cmd_vel` use?
- Which fields of `Twist` are used by a differential-drive style robot?

### Notes

- `linear.x` controls forward/backward speed.
- `angular.z` controls yaw rotation.
- The LiteVLA controller intentionally ignores unsafe free-form model text.

## Session 4: Simulated Camera Frames

### Commands

```bash
cd /home/rach.dev/ros2_lyrical/litevla_edge_ws
source /opt/ros/jazzy/setup.bash
source install/setup.bash
ros2 launch litevla_edge sim_camera_dummy.launch.py
```

In another terminal:

```bash
source /opt/ros/jazzy/setup.bash
ros2 topic hz /image_raw
ros2 topic info /image_raw
ros2 topic echo /image_raw --once
ros2 interface show sensor_msgs/msg/Image
```

### Questions To Answer

- What message type is published on `/image_raw`?
- What do `height`, `width`, `encoding`, and `step` mean?
- Why is the image timestamp important for robotics?

### Notes

- The current launch uses `image_tools/cam2image` with `burger_mode:=true`.
- A real USB camera can replace this as long as it publishes `sensor_msgs/Image`.

## Session 5: Action Parser And Safety

### Commands

```bash
cd /home/rach.dev/ros2_lyrical/litevla_edge_ws
source /opt/ros/jazzy/setup.bash
source install/setup.bash
colcon test --packages-select litevla_edge --event-handlers console_direct+
```

Try changing runtime actions:

```bash
ros2 param set /litevla_dummy_controller dummy_action MOVE_FORWARD
ros2 param set /litevla_dummy_controller dummy_action TURN_LEFT
ros2 param set /litevla_dummy_controller dummy_action nonsense
ros2 param set /litevla_dummy_controller estop true
```

### Questions To Answer

- Why should invalid model output become `STOP`?
- Where are max velocity limits enforced?
- Why start with discrete actions before continuous JSON commands?

### Notes

- Parser code: `litevla_edge/action_schema.py`
- Controller code: `litevla_edge/dummy_controller.py`
- Tests: `test/test_action_schema.py`

## Next Implementation Checkpoint

Add a frame/action logger:

- Subscribe to `/image_raw`.
- Save every Nth frame to `data/sessions/<timestamp>/frames`.
- Write `labels.jsonl` rows with:

```json
{"image_path": "frames/frame_000001.png", "instruction": "Move toward the red cube", "action": "MOVE_FORWARD", "linear_x": 0.15, "angular_z": 0.0, "latency_ms": 0.2}
```

This is the bridge from ROS experimentation to the dataset you need for VLM
fine-tuning.
