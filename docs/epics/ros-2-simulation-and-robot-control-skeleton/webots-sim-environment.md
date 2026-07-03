# Webots simulation environment

**Epic:** ROS 2 Simulation and Robot Control Skeleton (102) · **Jira epic:** VLA-3 · **Story:** VLA-23 / 1011 · **Subtasks:** 10034 (world), 10035 / VLA-117 (spawn)

**Human-readable version (browser):** [`webots-sim-environment.html`](webots-sim-environment.html)

## Executive summary

This story delivers the **simulation contract** for Epic 102: a Webots world with a diff-drive `litevla_robot`, onboard camera, and ROS 2 topics `/image_raw` and `/cmd_vel`. `webots_sim.launch.py` wires `webots_ros2_driver`, `ros2_control` spawners, and topic remaps so downstream nodes (camera subscriber, heartbeat, teleop) can assume stable topic names matching `configs/default.example.yaml`.

Without this story, Epic 102 has no shared stage—every node would need ad-hoc topic names and simulator-specific setup.

## Mental model

Think of this module as **the robot's virtual body and wiring closet**.

It exists because Lite-VLA needs one command to spawn a camera-equipped diff-drive robot whose ROS topics match the rest of the codebase.

The key engineering tension is **Webots' two-part install** (ROS bridge vs desktop app) versus the operator expectation that `apt install` is enough.

A beginner mistake is installing only `ros-jazzy-webots-ros2`, then wondering why `webots` is not on PATH.

A senior engineer watches for **topic remaps on Jazzy** (`TwistStamped` path) and ensures shutdown coupling so zombie Webots processes do not block the next launch.

## Backstory: why this exists

Before this module existed, the team had a simulator decision ([simulator-selection.md](simulator-selection.md)) but no reproducible world, URDF, or launch file tying Webots to Jazzy topic names.

The naive solution would be to open Webots manually, click Play, and hand-wire topics in the GUI each session.

That breaks because CI, scripts, and teammates cannot reproduce the setup; topic names drift (`/image_raw/image_color` vs `/image_raw`); and controller spawners race the sim startup.

So this design chooses **versioned assets + `webots_sim.launch.py` + operator scripts** (`run_webots_mvp.sh`, `run_teleop_sim.sh`) with explicit remaps and spawn verification (VLA-117).

This pattern appears in real systems as **infrastructure-as-code for sim**: worlds and launch files are reviewed like application code.

## Prerequisites

- [simulator-selection.md](simulator-selection.md) — why Webots was chosen.
- ROS 2 launch files and `use_sim_time`.
- `ros2_control` basics: controller manager, diff-drive controller, joint state broadcaster.

## Concept primer / vocabulary

| Term | Meaning in this project |
|------|-------------------------|
| **`.wbt` world** | Webots scene file; default `mvp_arena.wbt` with arena and target cube. |
| **`litevla_robot`** | Named Webots robot instance; must match `WebotsController(robot_name=...)`. |
| **`webots_ros2_driver`** | Package bridging Webots devices to ROS 2 topics and `ros2_control`. |
| **`ros2_control.yml`** | Controller config: diff-drive limits (0.2 m/s, 0.6 rad/s). |
| **`use_sim_time:=true`** | Nodes use `/clock` from simulation, not wall clock. |
| **Interactive vs batch launcher** | GUI mode (`interactive:=true`) for teleop; batch for headless smoke. |
| **Spawn verifier** | Node that confirms `/image_raw` frames and `/cmd_vel` motion (VLA-117). |

## Guided code reading

Read these in order:

1. `worlds/mvp_arena.wbt`
   - Find robot name `litevla_robot` and camera device.
   - Ignore decorative arena geometry on first pass.

2. `resource/litevla_robot.urdf`
   - Inspect diff-drive and camera `ros2_control` interfaces.
   - Note wheel collision geometry (tip-over mitigation).

3. `resource/ros2_control.yml`
   - Velocity limits must align with MVP safety defaults.

4. `launch/webots_sim.launch.py`
   - Jazzy `cmd_vel` remap and `/image_raw/image_color` → `/image_raw`.
   - `InteractiveWebotsLauncher` vs `WebotsLauncher`.

5. `ros_ws/scripts/run_webots_mvp.sh`
   - Operator entry point and environment setup.

While reading, ask:

- Where does `/cmd_vel` enter the diff-drive controller?
- Who publishes `/clock`?
- What happens when Webots exits?

## File and artifact index

| File or artifact | What it is | Why it matters | First thing to inspect |
|------------------|------------|----------------|------------------------|
| `worlds/mvp_arena.wbt` | Webots arena world | Robot spawn, target cube | `litevla_robot` DEF name |
| `resource/litevla_robot.urdf` | Robot description | Camera + diff-drive interfaces | `ros2_control` tags |
| `resource/ros2_control.yml` | Controller parameters | Velocity limits, controller types | `diffdrive_controller` limits |
| `config/webots_sim.yaml` | Bridge metadata | Topic naming for driver nodes | Image topic keys |
| `launch/webots_sim.launch.py` | Sim launch graph | Remaps, spawners, shutdown | Jazzy `cmd_vel` remap branch |
| `litevla_bridge/spawn_verifier.py` | Smoke test node | Proves contract after spawn | Frame + motion checks |
| `ros_ws/scripts/install_webots.sh` | Webots app install | Part 2 of two-part install | Version pin |
| `ros_ws/scripts/find_webots.sh` | PATH diagnostic | Verifies `webots` binary exists | Exit code |

## API contract and data flow

### What "contract" means here

The **contract** is what Epic 102 downstream nodes may assume while the sim runs: topic names, message types, velocity limits, and sim time. Nodes do not talk to Webots directly—they trust remapped ROS topics.

### Task-local flow

```text
mvp_arena.wbt
    ──> WebotsLauncher (batch) or InteractiveWebotsLauncher (GUI teleop)
    ──> webots_ros2_driver (litevla_robot)
            ├── /image_raw/image_color ──remap──> /image_raw
            ├── diffdrive_controller/cmd_vel ──remap──> /cmd_vel
            └── /odom
    ──> controller_manager spawner: joint_state_broadcaster, diffdrive_controller
```

### Contract table

| Row label | Meaning |
|-----------|---------|
| **World default** | Launch argument for `.wbt` file path. |
| **Velocity limits** | Max linear/angular speeds in `ros2_control.yml`. |
| **Sim time** | Whether nodes use simulation clock. |
| **Spawn verify** | Automated checks that camera and motion work. |

| Contract | Value |
|----------|-------|
| **World default** | `mvp_arena.wbt` |
| **Velocity limits** | 0.2 m/s linear, 0.6 rad/s angular (`ros2_control.yml`) |
| **Sim time** | `use_sim_time:=true` |
| **Spawn verify** | `spawn_verifier` — expects frames on `/image_raw`, motion on `/cmd_vel` (VLA-117) |

### Naive approach vs chosen approach

| Approach | Why it seems attractive | Why we did or did not choose it |
|----------|-------------------------|---------------------------------|
| Manual Webots GUI wiring | Fast for one developer once | Not reproducible; topic names drift |
| Single `apt install` assumption | Simple onboarding story | `ros-jazzy-webots-ros2` does **not** install `webots` binary |
| Launch + scripts + verifier | More files to maintain | Reproducible contract; CI can test config without GUI |
| Publish raw Webots topic names | No remapping | Breaks `configs/default.example.yaml` and all downstream nodes |

## Implementation breakdown

### Two-part install (critical)

| Step | Component | Install |
|------|-----------|---------|
| 1 | ROS bridge | `sudo apt install ros-jazzy-webots-ros2` |
| 2 | Webots app | `./ros_ws/scripts/install_webots.sh` |

**What to notice:** `ros-jazzy-webots-ros2` alone does **not** install the `webots` binary.

**Why it is written this way:** Ubuntu packages the ROS bridge; Cyberbotics distributes the simulator separately.

**Risks and gotchas:** `./ros_ws/scripts/find_webots.sh` is the first diagnostic when launch fails with "Webots not found".

### World and robot assets

| Path | Responsibility |
|------|----------------|
| `worlds/mvp_arena.wbt` | Arena, red cube target, robot spawn |
| `resource/litevla_robot.urdf` | Camera + diff-drive `ros2_control` interfaces |
| `resource/ros2_control.yml` | Controller types and velocity limits |
| `config/webots_sim.yaml` | Topic metadata for bridge nodes |

Wheel-only collision geometry avoids tip-over during teleop sharp turns (VLA-28 follow-up).

### Launch (`webots_sim.launch.py`)

**Snippet** (Jazzy remapping):

```python
use_twist_stamped = os.environ.get("ROS_DISTRO", "") in {"jazzy", "kilted", "rolling"}
if use_twist_stamped:
    cmd_vel_remapping = ("/diffdrive_controller/cmd_vel", "/cmd_vel")
# ...
remappings=[
    cmd_vel_remapping,
    ("/diffdrive_controller/odom", "/odom"),
    ("/image_raw/image_color", "/image_raw"),
],
```

**What to notice:** Jazzy uses a different `cmd_vel` topic suffix than older distros.

**Why it is written this way:** `webots_ros2` follows `ros2_control` naming per distro; Lite-VLA exposes a stable `/cmd_vel` alias.

**Risks and gotchas:** Upgrading ROS distro requires re-checking this branch.

- **Interactive mode:** `interactive:=true` selects `InteractiveWebotsLauncher` (drops `--batch`).
- **Shutdown coupling:** Webots exit triggers ROS shutdown via `OnProcessExit`.

### Operator scripts

```bash
./ros_ws/scripts/run_webots_mvp.sh          # sim only
./ros_ws/scripts/run_teleop_sim.sh          # sim + teleop (interactive:=true)
./ros_ws/scripts/run_episode_capture.sh     # sim + teleop + frames/commands for VLA-42
./ros_ws/scripts/stop_teleop_sim.sh         # clean shutdown (teleop + capture)
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

| Check | Pass criteria | Contract defended |
|-------|---------------|-------------------|
| `test_webots_config.py` | Launch args, world path, remaps present | Launch graph matches Jazzy expectations |
| `verify_spawn.launch.py` | `/image_raw` frames; robot moves on test `/cmd_vel` | Camera + actuation path alive |
| `ros2 topic list` | `/clock`, `/cmd_vel`, `/image_raw` while sim running | Topic contract for downstream nodes |

## Failure modes and debugging path

| Symptom | Likely cause | How to investigate | Fix |
|---------|--------------|--------------------|-----|
| `Webots not found` | Missing part 2 install | `./ros_ws/scripts/find_webots.sh` | `./ros_ws/scripts/install_webots.sh` |
| No `/image_raw` | Controllers not spawned; sim not running | `ros2 topic hz /image_raw` | Wait for spawners; keep Webots window open |
| No `/cmd_vel` effect | Wrong remap or inactive diff-drive | `ros2 control list_controllers` | Re-run after `stop_teleop_sim.sh`; allow up to 120 s |
| Robot tips on sharp turn | Collision mesh on body | Inspect URDF collision | Wheel-only collision (known follow-up) |
| Stale processes block relaunch | Prior Webots not killed | `ps aux \| grep webots` | `./ros_ws/scripts/stop_teleop_sim.sh` |

## Engineering principle taught by this task

This task teaches **reproducible simulation infrastructure**: treat worlds, URDF, launch remaps, and install scripts as part of the API surface, not operator folklore.

## Active learning checks

1. What are the two install steps for Webots on this project?
2. Why does Jazzy need a different `cmd_vel` remap than Humble?
3. Which file proves `/image_raw` and motion without manual GUI testing?
4. What topic does `webots_ros2` publish before remapping, and why?

## Small modification exercise

Change the default world launch argument to a copy of `mvp_arena.wbt` with one obstacle moved. Update `test_webots_config.py` if paths are asserted. Run `colcon test --packages-select litevla_bridge` and `verify_spawn.launch.py` to confirm the contract still holds.

## Related

- [simulator-selection.md](simulator-selection.md) (VLA-115)
- [`../../../../ros_ws/README.md`](../../../../ros_ws/README.md)
