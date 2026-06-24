# Webots simulation environment

**Epic:** ROS 2 Simulation and Robot Control Skeleton (102) · **Jira epic:** VLA-3 · **Story:** VLA-23 / 1011 · **Subtasks:** 10034 (world), 10035 / VLA-117 (spawn)

**Human-readable version (browser):** [`webots-sim-environment.html`](webots-sim-environment.html)

## Executive summary

This story delivers the **simulation contract** for Epic 102: a Webots world with a diff-drive `litevla_robot`, onboard camera, and ROS 2 topics `/image_raw` and `/cmd_vel`. `webots_sim.launch.py` wires `webots_ros2_driver`, `ros2_control` spawners, and topic remaps so downstream nodes (camera subscriber, heartbeat, teleop) can assume stable topic names matching `configs/default.example.yaml`.

## API contract and data flow

```text
mvp_arena.wbt
    ──> WebotsLauncher (batch) or InteractiveWebotsLauncher (GUI teleop)
    ──> webots_ros2_driver (litevla_robot)
            ├── /image_raw/image_color ──remap──> /image_raw
            ├── diffdrive_controller/cmd_vel ──remap──> /cmd_vel
            └── /odom
    ──> controller_manager spawner: joint_state_broadcaster, diffdrive_controller
```

| Contract | Value |
|----------|-------|
| World default | `mvp_arena.wbt` |
| Velocity limits | 0.2 m/s linear, 0.6 rad/s angular (`ros2_control.yml`) |
| Sim time | `use_sim_time:=true` |
| Spawn verify | `spawn_verifier` — expects frames on `/image_raw`, motion on `/cmd_vel` (VLA-117) |

## Two-part install (critical)

| Step | Component | Install |
|------|-----------|---------|
| 1 | ROS bridge | `sudo apt install ros-jazzy-webots-ros2` |
| 2 | Webots app | `./ros_ws/scripts/install_webots.sh` |

`ros-jazzy-webots-ros2` alone does **not** install the `webots` binary. Verify with `./ros_ws/scripts/find_webots.sh`.

## Implementation breakdown

### World and robot assets

| Path | Responsibility |
|------|----------------|
| `worlds/mvp_arena.wbt` | Arena, red cube target, robot spawn |
| `resource/litevla_robot.urdf` | Camera + diff-drive `ros2_control` interfaces |
| `resource/ros2_control.yml` | Controller types and velocity limits |
| `config/webots_sim.yaml` | Topic metadata for bridge nodes |

Wheel-only collision geometry avoids tip-over during teleop sharp turns (VLA-28 follow-up).

### Launch (`webots_sim.launch.py`)

- **Jazzy remapping:** `diffdrive_controller/cmd_vel` → `/cmd_vel` (TwistStamped path).
- **Interactive mode:** `interactive:=true` selects `InteractiveWebotsLauncher` (drops `--batch`).
- **Shutdown coupling:** Webots exit triggers ROS shutdown via `OnProcessExit`.

### Operator scripts

```bash
./ros_ws/scripts/run_webots_mvp.sh          # sim only
./ros_ws/scripts/run_teleop_sim.sh          # sim + teleop (interactive:=true)
./ros_ws/scripts/stop_teleop_sim.sh         # clean shutdown
```

## Engineering decisions

**ADR: Webots over Isaac Sim**

- **Status:** Accepted (see [simulator-selection.md](simulator-selection.md) VLA-115)
- **Context:** Isaac Sim exceeded team GPU/VRAM with concurrent VLA inference.
- **Decision:** Webots + `webots_ros2` on Jazzy; custom `litevla_robot`.
- **Consequences:** Lower visual fidelity; laptop-friendly loop for Epic 104–108.

## Verification patterns

```bash
colcon test --packages-select litevla_bridge   # test_webots_config.py — no Webots required
./ros_ws/scripts/find_webots.sh
./ros_ws/scripts/run_webots_mvp.sh
ros2 launch litevla_bridge verify_spawn.launch.py   # VLA-117
```

| Check | Pass criteria |
|-------|---------------|
| `test_webots_config.py` | Launch args, world path, remaps present |
| `verify_spawn.launch.py` | `/image_raw` frames; robot moves on test `/cmd_vel` |
| `ros2 topic list` | `/clock`, `/cmd_vel`, `/image_raw` while sim running |

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `Webots not found` | `./ros_ws/scripts/install_webots.sh` |
| No `/image_raw` | Wait for controller spawners; keep Webots window open |
| Controllers inactive | Re-run after `stop_teleop_sim.sh`; allow up to 120 s |

## Related

- [simulator-selection.md](simulator-selection.md) (VLA-115)
- [`../../../../ros_ws/README.md`](../../../../ros_ws/README.md)
