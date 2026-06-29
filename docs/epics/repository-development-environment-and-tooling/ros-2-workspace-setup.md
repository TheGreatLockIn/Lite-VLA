# ROS 2 workspace setup

**Epic:** Repository, Development Environment, and Tooling (101) · **Jira:** VLA-19 / Story 1007

**Human-readable version (browser):** [`ros-2-workspace-setup.html`](ros-2-workspace-setup.html)

This document describes the repeatable ROS 2 colcon workspace added for Lite-VLA (Jira **VLA-19**).

## Intent

Make ROS workspace creation repeatable for all teammates: consistent layout, one control-bridge package name, documented `source` commands, and a `colcon build` path that succeeds on a machine with ROS 2 Jazzy installed.

## Subtasks covered

| ID | Title | Deliverable |
|----|-------|-------------|
| 10021 | Create ROS workspace skeleton | `ros_ws/src/` layout, `ros_ws/README.md` |
| 10022 | Create control bridge package | `ros_ws/src/litevla_bridge/` ament_python package |
| 10023 | Document ROS environment sourcing | Build/sourcing commands in `ros_ws/README.md` and root `README.md` |

## Repository layout

```text
ros_ws/
├── README.md
├── scripts/build_ros_ws.sh
└── src/litevla_bridge/
    ├── package.xml
    ├── setup.py
    ├── config/bridge_params.yaml
    ├── litevla_bridge/
    │   ├── __init__.py
    │   └── workspace_ping.py
    └── test/
```

`build/`, `install/`, and `log/` are gitignored (see root `.gitignore`).

## Package: `litevla_bridge`

Single ROS 2 package for the robot control bridge (camera subscriber, cmd_vel publisher, dummy actions, heartbeat, teleop — added in later stories).

**Declared dependencies** (`package.xml`): `rclpy`, `std_msgs`, `geometry_msgs`, `sensor_msgs`, `cv_bridge` (for upcoming camera work).

**Smoke executable:** `workspace_ping` — logs once to confirm the overlay is sourced.

## Build and source

```bash
source /opt/ros/jazzy/setup.bash
./ros_ws/scripts/build_ros_ws.sh
source ros_ws/install/setup.bash
```

## Validation

```bash
source /opt/ros/jazzy/setup.bash
cd ros_ws && ./scripts/build_ros_ws.sh && source install/setup.bash
colcon test --packages-select litevla_bridge
colcon test-result --verbose
ros2 run litevla_bridge workspace_ping
```

`colcon test` runs `test/test_package.py` (package version smoke). Python style for this repo is checked at the root with Ruff (`./scripts/run_ci_checks.sh`), not duplicate ament flake8 linters in the ROS package.

## ADR: ROS 2 distribution and package name

| Field | Decision |
|-------|----------|
| **Status** | Accepted |
| **Context** | Team needs one ROS distro and one bridge package for camera → cmd_vel work. |
| **Decision** | ROS 2 **Jazzy** on Ubuntu 24.04; package name **`litevla_bridge`**. |
| **Alternatives rejected** | Multiple packages per node (premature); Humble (docs target Jazzy). |
| **Consequences** | Install docs assume Jazzy paths; Epic 102 nodes land inside `litevla_bridge`. |

## Related

- Workspace README: [`../../../../ros_ws/README.md`](../../../../ros_ws/README.md)
- Example runtime config: [`../../../../configs/default.example.yaml`](../../../../configs/default.example.yaml)
- Epic walkthrough: [`index.html`](index.html)
