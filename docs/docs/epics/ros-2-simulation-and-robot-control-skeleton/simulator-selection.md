# Simulator selection (MVP)

**Epic:** ROS 2 Simulation and Robot Control Skeleton (102) · **Jira epic:** VLA-3 · **Task:** VLA-115 / Subtask 10033 (parent VLA-23)

**Human-readable version (browser):** [`simulator-selection.html`](simulator-selection.html)

## Executive summary

VLA-115 records the simulator evaluation for Epic 102 and locks the **MVP platform contract**: Webots with `webots_ros2` on ROS 2 Jazzy. The decision prioritizes a laptop-friendly GPU budget (sim + 4-bit VLA inference on one machine) over photorealism. Isaac Sim was evaluated and **rejected** on available hardware; Gazebo remains a documented fallback.

## Evaluation criteria

| Criterion | Why it matters |
|-----------|----------------|
| RGB camera → ROS image topic | VLA pipeline starts with `/image_raw` |
| Diff-drive `/cmd_vel` | MVP uses `geometry_msgs/Twist` |
| ROS 2 Jazzy integration | Matches VLA-19 workspace |
| GPU budget | Sim + inference without VRAM exhaustion (RSK-07) |
| Beginner setup | Team reaches first loop quickly |

## Options compared

| Simulator | MVP verdict | Camera | Diff-drive | Jazzy | GPU load |
|-----------|-------------|--------|------------|-------|----------|
| **Webots** | **Selected** | Yes | Yes | `webots_ros2` | Low |
| **Isaac Sim** | **Rejected** | Yes | Yes | Isaac ROS | Very high |
| **Gazebo Harmonic** | Defer | Yes | Yes | Native | Moderate |
| **turtlesim** | Dev-only | No | Yes | Native | Minimal |
| **cam2image** | Dev stub | Synthetic | N/A | Native | Minimal |

## API contract (post-decision)

```text
Webots world (.wbt) ──> webots_ros2_driver ──> /image_raw + /cmd_vel
```

Downstream Epic 102 nodes assume this interface regardless of future simulator migrations.

## Engineering decisions

**ADR: Webots for MVP**

- **Status:** Accepted
- **Context:** Architecture and MVP docs originally targeted Webots; Isaac trial failed on team GPU.
- **Decision:** Webots R2025a + `ros-jazzy-webots-ros2`; custom `litevla_robot` in `mvp_arena.wbt`.
- **Alternatives rejected:** Isaac Sim (VRAM); Gazebo (heavier first-time setup for this scope); turtlesim/cam2image (not full sim).
- **Consequences:** VLA-23 deliverables use `run_webots_mvp.sh`; revisit Isaac only with stronger hardware.

## VLA-23 deliverables (implementation of this decision)

1. `sudo apt install ros-jazzy-webots-ros2` + `./ros_ws/scripts/install_webots.sh`
2. `worlds/mvp_arena.wbt`, `launch/webots_sim.launch.py`, `scripts/run_webots_mvp.sh`
3. `spawn_verifier` + `verify_spawn.launch.py` (VLA-117)

See [webots-sim-environment.md](webots-sim-environment.md).

## Verification patterns

- [x] Four Jira-listed options documented with tradeoffs
- [x] Webots selected; Isaac rejection recorded with GPU rationale
- [x] Integration smoke: `./ros_ws/scripts/run_webots_mvp.sh` + `verify_spawn.launch.py`

## Related

- [webots-sim-environment.md](webots-sim-environment.md) (VLA-23)
- [../../mvp_definition.md](../../mvp_definition.md)
- [../../architecture_summary.md](../../architecture_summary.md)
