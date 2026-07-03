# Simulator selection (MVP)

**Epic:** ROS 2 Simulation and Robot Control Skeleton (102) · **Jira epic:** VLA-3 · **Task:** VLA-115 / Subtask 10033 (parent VLA-23)

**Human-readable version (browser):** [`simulator-selection.html`](simulator-selection.html)

## Executive summary

VLA-115 records the simulator evaluation for Epic 102 and locks the **MVP platform contract**: Webots with `webots_ros2` on ROS 2 Jazzy. The decision prioritizes a laptop-friendly GPU budget (sim + 4-bit VLA inference on one machine) over photorealism. Isaac Sim was evaluated and **rejected** on available hardware; Gazebo remains a documented fallback.

This task does not ship runtime code. It owns the **integration boundary** that every downstream Epic 102 node assumes: a diff-drive robot with an RGB camera, `/cmd_vel` actuation, and `/image_raw` perception on Jazzy.

## Mental model

Think of this task as **choosing the stage, not writing the play**.

It exists because Lite-VLA needs a repeatable robot + camera loop before ML, dataset, and deployment epics can attach. The simulator is infrastructure—the contract (`/image_raw` in, `/cmd_vel` out) matters more than visual fidelity.

The key engineering tension is **realism vs resource budget**: photoreal simulators teach pretty scenes but can starve the GPU that inference needs.

A beginner mistake is picking the simulator with the best demo reel, then discovering the team laptop cannot run sim + model together.

A senior engineer watches for **topic-level portability**: if you cannot swap simulators without rewriting every node, the decision was cosmetic, not architectural.

## Backstory: why this exists

Before this module existed, the system had architecture docs pointing at Webots, but no recorded evaluation against alternatives on team hardware. New contributors could not tell whether Isaac Sim was deferred or rejected, or whether turtlesim was a serious option.

The naive solution would be to default to NVIDIA Isaac Sim because it dominates industry demos and has strong ROS integration.

That breaks because Isaac Sim + VLA inference exceeded available VRAM on team laptops (RSK-07). A simulator you cannot run daily is not an MVP platform—it becomes a blocker for every Epic 102 story.

So this design chooses **Webots R2025a + `ros-jazzy-webots-ros2`** with a custom `litevla_robot` in `mvp_arena.wbt`. Gazebo Harmonic stays documented as a fallback; turtlesim and `cam2image` remain dev-only stubs.

This pattern appears in real systems as **platform ADRs**: record the decision, the rejected options, and the measurable criteria so future hardware upgrades can reopen the choice without relitigating from scratch.

## Prerequisites

- Basic ROS 2 mental model: nodes publish/subscribe on **topics**; messages have typed schemas.
- Familiarity with `geometry_msgs/Twist` (diff-drive velocity commands) and `sensor_msgs/Image` (camera frames).
- Awareness that Epic 102 downstream nodes assume topic names in `configs/default.example.yaml`.

## Concept primer / vocabulary

| Term | Meaning in this project |
|------|-------------------------|
| **Simulator** | Software that renders a robot world and exposes ROS topics for camera and motion. |
| **`webots_ros2`** | ROS 2 bridge package that connects a Webots `.wbt` world to Jazzy topics. |
| **`/cmd_vel`** | Topic carrying `geometry_msgs/Twist` velocity commands to the diff-drive controller. |
| **`/image_raw`** | Topic carrying `sensor_msgs/Image` camera frames for perception and dataset capture. |
| **Diff-drive** | Two-wheeled drive model; MVP uses `linear.x` (forward) and `angular.z` (turn). |
| **RSK-07** | Project risk: GPU/VRAM budget must cover sim + 4-bit inference on one machine. |
| **Platform contract** | The stable topic/interface boundary downstream code may depend on. |

## Guided code reading

This task is primarily a decision record. Read implementation in this order after understanding the verdict:

1. [simulator-selection.md](simulator-selection.md) (this page) — criteria and ADR.
2. [webots-sim-environment.md](webots-sim-environment.md) — how the Webots contract is implemented.
3. `ros_ws/src/litevla_bridge/launch/webots_sim.launch.py` — topic remaps and launcher wiring.
4. `configs/default.example.yaml` — topic names the rest of the stack expects.

While reading, ask:

- Which topics must stay stable if we swap simulators later?
- Where is the two-part Webots install documented?
- What smoke test proves the contract works?

## File and artifact index

| File or artifact | What it is | Why it matters | First thing to inspect |
|------------------|------------|----------------|------------------------|
| `docs/epics/ros-2-simulation-and-robot-control-skeleton/simulator-selection.md` | Decision record | Source of truth for MVP sim choice | Options table and ADR |
| `ros_ws/scripts/install_webots.sh` | Webots app installer | ROS apt package alone does not install `webots` binary | Two-part install note |
| `ros_ws/scripts/run_webots_mvp.sh` | Operator entry point | Canonical smoke path after decision | Launch sequence |
| `worlds/mvp_arena.wbt` | Webots world | Robot spawn, arena, target cube | Robot name `litevla_robot` |
| `configs/default.example.yaml` | Stack config | Topic names assumed by all nodes | `ros.image_topic`, cmd_vel paths |

## API contract and data flow

### What "contract" means here

In this task, **contract** means the **stable ROS interface** Epic 102 nodes may assume regardless of which simulator runs underneath. Callers do not import Webots APIs; they subscribe and publish on named topics. If the contract drifts (wrong topic names, missing camera), every downstream story breaks without a single compile error.

### Task-local flow

```text
Webots world (.wbt)
    ──> webots_ros2_driver (litevla_robot)
            ├── /image_raw/image_color ──remap──> /image_raw
            ├── diffdrive_controller/cmd_vel ──remap──> /cmd_vel
            └── /odom
    ──> downstream Epic 102 nodes (camera, heartbeat, teleop, dummy)
```

### Contract table

| Row label | Meaning |
|-----------|---------|
| **Platform** | Selected simulator stack for MVP. |
| **Camera topic** | ROS topic downstream perception nodes subscribe to. |
| **Actuation topic** | ROS topic the heartbeat ultimately drives (via diff-drive controller). |
| **ROS distro** | Target middleware version for all Epic 102 packages. |
| **GPU posture** | Whether sim + inference can coexist on team hardware. |

| Contract | Value |
|----------|-------|
| **Platform** | Webots R2025a + `ros-jazzy-webots-ros2` |
| **Camera topic** | `/image_raw` (`sensor_msgs/Image`) |
| **Actuation topic** | `/cmd_vel` (`geometry_msgs/Twist`) |
| **ROS distro** | Jazzy |
| **GPU posture** | Low sim load; Isaac rejected for VRAM |

### Naive approach vs chosen approach

| Approach | Why it seems attractive | Why we did or did not choose it |
|----------|-------------------------|---------------------------------|
| **Isaac Sim** | Industry-standard photorealism, strong perception research tooling | Rejected — VRAM exhaustion with concurrent VLA inference on team laptops |
| **Gazebo Harmonic** | Native Jazzy integration, common in ROS tutorials | Deferred — heavier first-time setup for this MVP scope |
| **turtlesim / cam2image** | Trivial to launch, zero 3D assets | Dev-only — no onboard camera in turtlesim; not a full sim loop |
| **Webots** | Moderate fidelity, `webots_ros2` bridge, laptop-friendly | **Selected** — meets camera + diff-drive + Jazzy with acceptable GPU load |

## Implementation breakdown

This story is a **decision artifact**, not a runtime module. Implementation lives in VLA-23 ([webots-sim-environment.md](webots-sim-environment.md)).

### Evaluation criteria

| Criterion | Why it matters |
|-----------|----------------|
| RGB camera → ROS image topic | VLA pipeline starts with `/image_raw` |
| Diff-drive `/cmd_vel` | MVP uses `geometry_msgs/Twist` |
| ROS 2 Jazzy integration | Matches VLA-19 workspace |
| GPU budget | Sim + inference without VRAM exhaustion (RSK-07) |
| Beginner setup | Team reaches first loop quickly |

**What to notice:** Criteria are interface-first (topics, distro), not feature checklists (physics accuracy, mesh quality).

**Why it is written this way:** Downstream epics depend on topic contracts, not on a specific physics engine API.

**Risks and gotchas:** Reopening Isaac requires documenting new hardware assumptions, not just installing Omniverse.

### Options compared

| Simulator | MVP verdict | Camera | Diff-drive | Jazzy | GPU load |
|-----------|-------------|--------|------------|-------|----------|
| **Webots** | **Selected** | Yes | Yes | `webots_ros2` | Low |
| **Isaac Sim** | **Rejected** | Yes | Yes | Isaac ROS | Very high |
| **Gazebo Harmonic** | Defer | Yes | Yes | Native | Moderate |
| **turtlesim** | Dev-only | No | Yes | Native | Minimal |
| **cam2image** | Dev stub | Synthetic | N/A | Native | Minimal |

## Engineering decisions

**ADR: Webots for MVP**

- **Status:** Accepted
- **Context:** Architecture and MVP docs originally targeted Webots; Isaac trial failed on team GPU.
- **Decision:** Webots R2025a + `ros-jazzy-webots-ros2`; custom `litevla_robot` in `mvp_arena.wbt`.
- **Alternatives rejected:** Isaac Sim (VRAM); Gazebo (heavier first-time setup for this scope); turtlesim/cam2image (not full sim).
- **Consequences:** VLA-23 deliverables use `run_webots_mvp.sh`; revisit Isaac only with stronger hardware.

## Verification patterns

| Contract defended | Evidence |
|-------------------|----------|
| Four Jira-listed options documented | Options table above |
| Webots selected; Isaac rejection recorded | ADR with GPU rationale |
| Integration smoke | `./ros_ws/scripts/run_webots_mvp.sh` + `verify_spawn.launch.py` |

```bash
./ros_ws/scripts/find_webots.sh
./ros_ws/scripts/run_webots_mvp.sh
# separate terminal:
ros2 launch litevla_bridge verify_spawn.launch.py
```

## Failure modes and debugging path

| Symptom | Likely cause | How to investigate | Fix |
|---------|--------------|--------------------|-----|
| `Webots not found` | Two-part install incomplete — apt only installed bridge | `./ros_ws/scripts/find_webots.sh` | Run `./ros_ws/scripts/install_webots.sh` |
| Team wants Isaac instead | Hardware may now be sufficient | Re-run GPU budget test with sim + inference | Reopen ADR; do not swap silently |
| Topics differ from docs | Wrong launch file or distro remapping | `ros2 topic list` while sim runs | Compare with `webots_sim.launch.py` remaps |
| `verify_spawn` fails | Controllers not active or sim not ready | Wait 120 s; check spawner logs | Re-run after `stop_teleop_sim.sh` |

## Engineering principle taught by this task

This task teaches **interface-stable platform selection**: choose infrastructure by the ROS contract it exposes and the resources it consumes, not by demo quality. Record rejections with measurable reasons so the team does not relitigate the same trade-off every sprint.

## Active learning checks

Before proposing a simulator change, answer:

1. Which three ROS topics must stay stable for Epic 102 nodes to work unchanged?
2. Why was Isaac Sim rejected on team hardware, not merely deferred?
3. What is the difference between turtlesim as a dev tool and Webots as the MVP platform?
4. What command proves the Webots contract end-to-end without reading C++?

## Small modification exercise

Add one row to the options table for a simulator you know (e.g. MuJoCo + ROS bridge). Document camera support, diff-drive, Jazzy integration, and estimated GPU load. Compare against the Webots ADR criteria—would it pass without changing the `/image_raw` + `/cmd_vel` contract?

## Related

- [webots-sim-environment.md](webots-sim-environment.md) (VLA-23)
- [../../mvp_definition.md](../../mvp_definition.md)
- [../../architecture_summary.md](../../architecture_summary.md)
