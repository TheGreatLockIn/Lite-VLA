# Simulator selection (MVP)

**Epic:** ROS 2 Simulation and Robot Control Skeleton (102) · **Jira:** VLA-115 / Subtask 10033 (parent story VLA-23 / 1011)

**Human-readable version (browser):** [`simulator-selection.html`](simulator-selection.html)

This document records the simulator evaluation for Lite-VLA and the **accepted MVP choice**.

**Revision:** **Webots** is selected for MVP. Isaac Sim was tried but **rejected on team hardware** due to GPU/VRAM limits (RSK-07). This aligns with `mvp_definition.md` and `architecture_summary.md`.

## Evaluation criteria

| Criterion | Why it matters |
|-----------|----------------|
| RGB camera → ROS image topic | VLA pipeline starts with `/image_raw` |
| Diff-drive `/cmd_vel` | MVP uses `geometry_msgs/Twist` |
| ROS 2 Jazzy integration | Matches VLA-19 workspace |
| MVP scenario | Flat arena, wheeled robot, red cube target |
| **GPU budget** | Sim + VLA inference on one laptop without VRAM crashes |
| Beginner-friendly setup | Team can reach first loop quickly |

## Options compared

### Summary matrix

| Simulator | MVP verdict | Camera | Diff-drive | Jazzy ROS 2 | GPU load | Notes |
|-----------|-----------|--------|------------|-------------|----------|-------|
| **Webots** | **Selected** | Yes | Yes | `webots_ros2` | **Low** | Matches architecture docs; laptop-friendly |
| **NVIDIA Isaac Sim** | **Reject** | Yes | Yes | Isaac ROS bridge | **Very high** | Failed on team GPU; revisit only with stronger hardware |
| **Gazebo (Harmonic)** | Defer | Yes | Yes | Native | Moderate | Valid fallback if Webots blocks team |
| **turtlesim** | Dev-only | No | Yes (2D) | Native | Minimal | cmd_vel tests only |
| **cam2image** | Dev stub | Synthetic | N/A | Native | Minimal | Not a simulator |

### Webots (selected)

**Pros**

- Low GPU use — runs comfortably alongside 4-bit VLA inference (RSK-07 mitigation).
- Original MVP and architecture target (`webots_ros2`, Pioneer/E-puck class robots).
- Official ROS 2 Jazzy packages (`ros-jazzy-webots-ros2`).
- Simple world format (`.wbt`); good for student teams.

**Cons**

- Less photorealistic than Isaac Sim (acceptable for discrete-action MVP).
- Must pin Webots + `webots_ros2` versions.

**Integration (VLA-23)**

```text
mvp_arena.wbt → webots_ros2_driver → /image_raw, /cmd_vel
```

**Install note:** `sudo apt install ros-jazzy-webots-ros2` is only the ROS bridge. You must also install the Webots simulator app (`./ros_ws/scripts/install_webots.sh`). See [webots-sim-environment.md](webots-sim-environment.md).

### NVIDIA Isaac Sim (rejected — GPU)

**Pros:** Photoreal RGB; NVIDIA ecosystem.

**Cons (decisive for this team):**

- GPU/VRAM insufficient on available hardware.
- Heavy Omniverse install and onboarding.
- Sim + VLA concurrently caused unacceptable load.

**Status:** Rejected for MVP; documented in VLA-115 ADR revision.

### Gazebo (deferred)

Heavier first-time setup than Webots for this scope. Revisit if `webots_ros2` blocks progress.

### turtlesim / cam2image (dev aids only)

No replacement for full sim; use for isolated cmd_vel or fake camera tests.

## Decision

| Field | Value |
|-------|--------|
| **Status** | Accepted |
| **MVP simulator** | **Webots** with **`webots_ros2`** on ROS 2 **Jazzy** |
| **Robot** | Custom `litevla_robot` diff-drive + onboard camera in `mvp_arena.wbt` |
| **World** | `worlds/mvp_arena.wbt` — arena + red cube |
| **ROS topics** | `/image_raw`, `/cmd_vel` |
| **Rejected** | Isaac Sim (GPU/VRAM) |

## VLA-23 deliverables

See [webots-sim-environment.md](webots-sim-environment.md):

1. `sudo apt install ros-jazzy-webots-ros2` + `./ros_ws/scripts/install_webots.sh`
2. `worlds/mvp_arena.wbt`, `launch/webots_sim.launch.py`, `scripts/run_webots_mvp.sh`
3. `spawn_verifier` for VLA-117

## Validation (VLA-115)

- [x] All four Jira-listed options evaluated with tradeoffs.
- [x] **Webots** selected; Isaac rejection documented with GPU rationale.

## Related

- [webots-sim-environment.md](webots-sim-environment.md) (VLA-23)
- [../../mvp_definition.md](../../mvp_definition.md)
- [../../architecture_summary.md](../../architecture_summary.md)
