# Lite-VLA ROS 2 workspace

This directory is the **ROS 2 colcon workspace** for the Lite-VLA robot control loop: camera subscription, velocity publishing, dummy actions, heartbeat, and teleoperation nodes live in `src/litevla_bridge/`.

Source and documentation are committed to git. Each developer builds locally against their own ROS 2 install (`build/`, `install/`, and `log/` are gitignored).

## Prerequisites

| Requirement | Notes |
|-------------|--------|
| **Ubuntu 24.04** | Matches ROS 2 Jazzy target |
| **ROS 2 Jazzy** | [Install guide](https://docs.ros.org/en/jazzy/Installation/Ubuntu-Install-Debs.html) |
| **colcon** | `sudo apt install python3-colcon-common-extensions` |
| **webots_ros2** | `sudo apt install ros-jazzy-webots-ros2` — ROS bridge **only** |
| **Webots app** | `./ros_ws/scripts/install_webots.sh` — simulator binary (separate from apt line above) |

### Webots: two installs required

```bash
# 1) ROS bridge
sudo apt install ros-jazzy-webots-ros2

# 2) Simulator application (if run_webots_mvp.sh says "Webots not found")
./ros_ws/scripts/install_webots.sh

# Check
./ros_ws/scripts/find_webots.sh
```

Python dependencies for ML and config are installed separately from the repo root (`./scripts/setup_python_env.sh`). ROS packages are **not** listed in pip `requirements.txt`.

## Layout

```text
ros_ws/
├── README.md
├── scripts/
│   ├── build_ros_ws.sh
│   ├── install_webots.sh   # download + install Webots .deb
│   ├── find_webots.sh      # locate webots binary / WEBOTS_HOME
│   └── run_webots_mvp.sh   # launch MVP simulation
└── src/
    └── litevla_bridge/
        ├── worlds/mvp_arena.wbt
        ├── resource/
        ├── config/webots_sim.yaml
        ├── launch/
        └── litevla_bridge/
```

## Webots MVP (VLA-23)

GPU-friendly simulation (selected over Isaac Sim). Full runbook: [VLA-23 task doc](../docs/epics/ros-2-simulation-and-robot-control-skeleton/webots-sim-environment.md).

```bash
source /opt/ros/jazzy/setup.bash
./scripts/build_ros_ws.sh
source install/setup.bash
./scripts/run_webots_mvp.sh
```

Verify spawn (VLA-117) in another terminal:

```bash
source install/setup.bash
ros2 launch litevla_bridge verify_spawn.launch.py
```

Camera subscriber (VLA-24):

```bash
ros2 launch litevla_bridge camera_subscriber.launch.py
```

Velocity test (VLA-25) with Webots running:

```bash
ros2 launch litevla_bridge cmd_vel_test.launch.py
```

Dummy action sequence (VLA-26 + VLA-27 heartbeat):

```bash
ros2 launch litevla_bridge dummy_sim.launch.py
ros2 topic hz /cmd_vel
```

Keyboard teleop (VLA-28) — interactive terminal required:

```bash
./ros_ws/scripts/run_teleop_sim.sh
./ros_ws/scripts/stop_teleop_sim.sh   # before restart
```

Do not use `ros2 launch ... teleop_sim.launch.py` for keyboard driving — launch-managed nodes do not receive interactive stdin. See [manual-teleoperation.md](../docs/epics/ros-2-simulation-and-robot-control-skeleton/manual-teleoperation.md).

Full stack integration demo:

```bash
ros2 launch litevla_bridge full_stack.launch.py control_mode:=dummy
```

## Build

From the repository root:

```bash
source /opt/ros/jazzy/setup.bash
./ros_ws/scripts/build_ros_ws.sh
source ros_ws/install/setup.bash
```

## Test

```bash
source /opt/ros/jazzy/setup.bash
source install/setup.bash
colcon test --packages-select litevla_bridge
colcon test-result --verbose
```

**Full stack integration** (unit tests + Webots sim + VLA-19–25 smoke):

```bash
./scripts/run_epic102_integration_test.sh
```

Requires Webots app installed (`./scripts/install_webots.sh`).

## Run (workspace smoke check)

```bash
ros2 run litevla_bridge workspace_ping
```

## Troubleshooting

| Issue | Fix |
|-------|-----|
| `Webots not found in PATH` | Run `./scripts/install_webots.sh` (apt `webots_ros2` ≠ Webots app) |
| `Workspace not built` | Run `./scripts/build_ros_ws.sh` |
| No `/image_raw` | Ensure Webots window is open; wait for diff-drive controller spawners |

## Environment sourcing (every new shell)

```bash
source /opt/ros/jazzy/setup.bash
source /path/to/Lite-VLA/ros_ws/install/setup.bash
```

## Related docs

- Task doc (VLA-19): [`../docs/epics/repository-development-environment-and-tooling/ros-2-workspace-setup.md`](../docs/epics/repository-development-environment-and-tooling/ros-2-workspace-setup.md)
- Simulator selection (VLA-115): [`../docs/epics/ros-2-simulation-and-robot-control-skeleton/simulator-selection.md`](../docs/epics/ros-2-simulation-and-robot-control-skeleton/simulator-selection.md)
- Webots environment (VLA-23): [`../docs/epics/ros-2-simulation-and-robot-control-skeleton/webots-sim-environment.md`](../docs/epics/ros-2-simulation-and-robot-control-skeleton/webots-sim-environment.md)
- Camera subscriber (VLA-24): [`../docs/epics/ros-2-simulation-and-robot-control-skeleton/camera-frame-subscriber.md`](../docs/epics/ros-2-simulation-and-robot-control-skeleton/camera-frame-subscriber.md)
- Velocity publisher (VLA-25): [`../docs/epics/ros-2-simulation-and-robot-control-skeleton/velocity-command-publisher.md`](../docs/epics/ros-2-simulation-and-robot-control-skeleton/velocity-command-publisher.md)
- Dummy action generator (VLA-26): [`../docs/epics/ros-2-simulation-and-robot-control-skeleton/dummy-action-generator.md`](../docs/epics/ros-2-simulation-and-robot-control-skeleton/dummy-action-generator.md)
- Control heartbeat (VLA-27): [`../docs/epics/ros-2-simulation-and-robot-control-skeleton/control-heartbeat.md`](../docs/epics/ros-2-simulation-and-robot-control-skeleton/control-heartbeat.md)
- Manual teleop (VLA-28): [`../docs/epics/ros-2-simulation-and-robot-control-skeleton/manual-teleoperation.md`](../docs/epics/ros-2-simulation-and-robot-control-skeleton/manual-teleoperation.md)
