# Lite-VLA Webots MVP world (VLA-23)

World file for the red-cube navigation arena. See the full runbook: [webots-sim-environment.md](../../../../docs/epics/ros-2-simulation-and-robot-control-skeleton/webots-sim-environment.md).

## Prerequisites (two installs)

```bash
sudo apt install ros-jazzy-webots-ros2          # ROS bridge
./ros_ws/scripts/install_webots.sh              # Webots simulator app
./ros_ws/scripts/find_webots.sh               # verify
```

## Files

| File | Purpose |
|------|---------|
| `mvp_arena.wbt` | Arena, red cube, `litevla_robot` with camera |
| `../resource/litevla_robot.urdf` | ROS 2 driver config |
| `../launch/webots_sim.launch.py` | Launches this world |

## Run

```bash
source /opt/ros/jazzy/setup.bash
source ros_ws/install/setup.bash
./ros_ws/scripts/run_webots_mvp.sh
```
