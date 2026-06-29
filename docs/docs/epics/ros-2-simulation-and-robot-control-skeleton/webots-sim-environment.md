# Webots simulation environment

**Epic:** ROS 2 Simulation and Robot Control Skeleton (102) · **Jira:** VLA-23 / Story 1011 · **Subtasks:** 10034 (world), 10035 / VLA-117 (spawn)

**Human-readable version (browser):** [`webots-sim-environment.html`](webots-sim-environment.html)

GPU-friendly MVP simulation using **Webots** + **`webots_ros2`** (replaces Isaac Sim path).

## Intent

Launch a bounded arena with a red cube, diff-drive `litevla_robot` with onboard camera, and ROS 2 `/image_raw` + `/cmd_vel` for `litevla_bridge`.

## Two-part install (important)

Webots integration requires **two separate installs**. Installing only the ROS package is a common mistake.

| Step | Component | Install | Provides |
|------|-----------|---------|----------|
| 1 | **ROS 2 bridge** | `sudo apt install ros-jazzy-webots-ros2` | `webots_ros2_driver`, launch helpers, ROS ↔ Webots glue |
| 2 | **Webots simulator app** | `./ros_ws/scripts/install_webots.sh` | The `webots` binary, physics engine, GUI |

If `run_webots_mvp.sh` prints **"Webots not found in PATH"** but `ros-jazzy-webots-ros2` is already installed, you are missing **step 2**.

### Step 1 — ROS bridge

```bash
sudo apt install ros-jazzy-webots-ros2
```

### Step 2 — Webots application

From the repository root:

```bash
./ros_ws/scripts/install_webots.sh
```

This downloads [Webots R2025a](https://github.com/cyberbotics/webots/releases/tag/R2025a) (`webots_2025a_amd64.deb`) and installs it with `sudo`.

**Manual alternative:**

```bash
wget https://github.com/cyberbotics/webots/releases/download/R2025a/webots_2025a_amd64.deb
sudo apt install ./webots_2025a_amd64.deb
```

### Verify both are present

```bash
./ros_ws/scripts/find_webots.sh
# WEBOTS_BIN=/usr/local/webots/webots/bin/webots
# WEBOTS_HOME=/usr/local/webots

source /opt/ros/jazzy/setup.bash
ros2 pkg list | grep webots_ros2
```

## Artifacts

| Path | Purpose |
|------|---------|
| `worlds/mvp_arena.wbt` | Arena, red cube, `litevla_robot` + camera |
| `resource/litevla_robot.urdf` | Camera + diff-drive `ros2_control` |
| `resource/ros2_control.yml` | Velocity limits (0.2 m/s, 0.6 rad/s) |
| `config/webots_sim.yaml` | Topic names and world metadata |
| `launch/webots_sim.launch.py` | Webots + driver + controllers |
| `scripts/run_webots_mvp.sh` | One-command launch |
| `scripts/install_webots.sh` | Download and install Webots `.deb` |
| `scripts/find_webots.sh` | Locate `webots` binary and set `WEBOTS_HOME` |
| `spawn_verifier` + `verify_spawn.launch.py` | VLA-117 |

## Run

```bash
source /opt/ros/jazzy/setup.bash
./ros_ws/scripts/build_ros_ws.sh
source ros_ws/install/setup.bash
./ros_ws/scripts/run_webots_mvp.sh
```

## Verify spawn (VLA-117)

Terminal 2 (while Webots is running):

```bash
source /opt/ros/jazzy/setup.bash
source ros_ws/install/setup.bash
ros2 launch litevla_bridge verify_spawn.launch.py
```

**Pass:** `/image_raw` frames logged; test `/cmd_vel` published; robot moves in Webots.

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| `Webots not found in PATH` | Simulator app not installed | `./ros_ws/scripts/install_webots.sh` |
| `ros-jazzy-webots-ros2` installed but script still fails | Same as above — apt package ≠ Webots app | Run step 2 above |
| No `/image_raw` topics | Driver not started or Webots closed | Re-run `run_webots_mvp.sh`; wait for controller spawners |
| `/image_raw` missing but `/image_raw/image_color` exists | webots_ros2 naming | Launch remaps `image_color` → `/image_raw` in `webots_sim.launch.py` |
| `ros2_control.yml` parse error | Controller `type:` must be under `controller_manager.ros__parameters` | See fixed `resource/ros2_control.yml` |
| `WEBOTS_HOME` warning | Wrong path when `webots` is in `/usr/local/bin` | Run `./ros_ws/scripts/find_webots.sh` (should show `/usr/local/webots`) |
| `WEBOTS_HOME` errors | Binary not on default path | `eval "$(./ros_ws/scripts/find_webots.sh --export)"` |

## ADR: Webots over Isaac Sim

| Field | Value |
|-------|--------|
| **Status** | Accepted |
| **Context** | Isaac Sim exceeded available GPU/VRAM with inference workload. |
| **Decision** | Webots + `webots_ros2`; custom `litevla_robot` in `mvp_arena.wbt`. |
| **Consequences** | Aligns with original MVP/architecture docs; lower visual fidelity than Isaac. |

## Validation

```bash
colcon test --packages-select litevla_bridge   # test_webots_config.py (no Webots required)
./ros_ws/scripts/find_webots.sh                # confirms simulator app
./ros_ws/scripts/run_webots_mvp.sh             # full sim (requires both installs)
ros2 launch litevla_bridge verify_spawn.launch.py
```

## Related

- [simulator-selection.md](simulator-selection.md) (VLA-115)
- [`../../../../ros_ws/README.md`](../../../../ros_ws/README.md)
- [`../../../../ros_ws/src/litevla_bridge/worlds/README.md`](../../../../ros_ws/src/litevla_bridge/worlds/README.md)
