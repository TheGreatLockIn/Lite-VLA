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
