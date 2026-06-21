# LiteVLA Edge ROS 2 Workspace

This workspace contains the ROS 2 source packages for the LiteVLA edge/control bridge prototype.

The repository should commit source and docs only. Each developer builds locally against their own ROS 2 install.

## ROS 2 Distribution

Use ROS 2 Jazzy on Ubuntu 24.04.

Install ROS 2 Jazzy from the official docs:
https://docs.ros.org/en/jazzy/Installation/Ubuntu-Install-Debs.html

## Layout

```text
ros_ws/
├── README.md
├── scripts/
│   └── build_ros_ws.sh
└── src/
    └── litevla_edge/
```

Commit:

- `src/litevla_edge/`
- `README.md`
- `scripts/`
- the root `.gitignore` ROS workspace rules

Do not commit:

- `build/`
- `install/`
- `log/`
- Python cache files

## Build

After a fresh clone, every developer with ROS 2 should use the same local build flow:

```bash
git clone https://github.com/TheGreatLockIn/Lite-VLA.git
cd Lite-VLA
source /opt/ros/jazzy/setup.bash
cd ros_ws
colcon build
source install/setup.bash
```

From this workspace root:

```bash
source /opt/ros/jazzy/setup.bash
colcon build
source install/setup.bash
```

Or run:

```bash
./scripts/build_ros_ws.sh
```

## Test

```bash
source /opt/ros/jazzy/setup.bash
colcon test
colcon test-result --verbose
```

## Run

After building and sourcing the overlay:

```bash
ros2 run litevla_edge dummy_controller
```

For the dummy camera launch:

```bash
ros2 launch litevla_edge sim_camera_dummy.launch.py
```

For turtlesim:

```bash
ros2 launch litevla_edge turtlesim_dummy.launch.py
```

## Non-ML robot loop smoke test

Use this path to prove the robot control loop before connecting a VLA model:

```bash
source /opt/ros/jazzy/setup.bash
cd ros_ws
colcon build --packages-select litevla_edge
source install/setup.bash
ros2 launch litevla_edge sim_camera_dummy.launch.py
```

The launch starts a simulated camera and the dummy controller:

- `image_tools/cam2image` publishes camera frames on `/image_raw` at about 10 Hz.
- `litevla_dummy_controller` subscribes to `/image_raw` and publishes `geometry_msgs/Twist` on `/cmd_vel`.
- The controller timer is the heartbeat for this non-ML loop. It defaults to `publish_hz:=6.6`, matching the project target for stable closed-loop command publishing.
- The default dummy action is `MOVE_FORWARD`, which maps to `linear.x=0.15` and `angular.z=0.0`.

In another terminal, verify the active topics:

```bash
source /opt/ros/jazzy/setup.bash
source ros_ws/install/setup.bash
ros2 topic hz /image_raw
ros2 topic hz /cmd_vel
ros2 topic echo /cmd_vel --once
```

Manual control is available through ROS parameters while the controller is running:

```bash
ros2 param set /litevla_dummy_controller dummy_action TURN_LEFT
ros2 param set /litevla_dummy_controller dummy_action TURN_RIGHT
ros2 param set /litevla_dummy_controller dummy_action STOP
ros2 param set /litevla_dummy_controller estop true
```

Invalid actions safely fall back to `STOP`, and velocity outputs are clamped by `litevla_edge/action_schema.py`.
