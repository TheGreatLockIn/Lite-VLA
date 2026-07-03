# Velocity command publisher

**Epic:** ROS 2 Simulation and Robot Control Skeleton (102) · **Jira epic:** VLA-3 · **Story:** VLA-25 / 1013 · **Subtasks:** 10039 (publisher), 10040 (twist helpers), 10041 (sim test)

**Human-readable version (browser):** [`velocity-command-publisher.html`](velocity-command-publisher.html)

## Executive summary

`CmdVelPublisher` is the shared **actuation library** for Epic 102: the heartbeat controller (VLA-27) uses it as the sole path to `/cmd_vel`. `clamp_velocity()` enforces MVP limits before messages reach the diff-drive controller, keeping tester and heartbeat output aligned with `resource/ros2_control.yml`.

Action sources (dummy, teleop, future model) publish **intent** on `/litevla/desired_twist`; only the heartbeat + `CmdVelPublisher` pair touches `/cmd_vel` in the nominal architecture.

## Mental model

Think of `CmdVelPublisher` as **the last mile to the motor controller**—but only when called by the heartbeat.

It exists because every node that needs to command motion must share one clamping and publishing implementation, not duplicate `Twist` construction.

The key engineering tension is **convenience vs ownership**: the class can publish `/cmd_vel` directly (tests use this), but production traffic must flow through the heartbeat for timing and safety.

A beginner mistake is calling `CmdVelPublisher` from teleop or dummy nodes, creating competing `/cmd_vel` writers.

A senior engineer watches that **only one runtime owner** publishes `/cmd_vel` in integrated stacks, and that limits match `ros2_control.yml`.

## Backstory: why this exists

Before this module existed, each ROS node could construct and publish `geometry_msgs/Twist` independently, with copy-pasted clamp logic or none at all.

The naive solution would be `node.create_publisher(Twist, "/cmd_vel", 10)` in every command source.

That breaks because limits drift between nodes, multiple publishers race on `/cmd_vel`, and unit tests cannot verify clamp math without spinning ROS.

So this design chooses **`twist_utils.py` (pure functions) + `CmdVelPublisher` (ROS adapter)** used primarily by `heartbeat_controller`, with `cmd_vel_tester` for isolated sim smoke.

This pattern appears in real systems as a **single actuation sink** with shared safety primitives.

## Prerequisites

- `geometry_msgs/Twist` — diff-drive uses `linear.x` and `angular.z`.
- [control-heartbeat.md](control-heartbeat.md) — who calls `CmdVelPublisher` at runtime.
- [webots-sim-environment.md](webots-sim-environment.md) — `ros2_control.yml` velocity limits.

## Concept primer / vocabulary

| Term | Meaning in this project |
|------|-------------------------|
| **`CmdVelPublisher`** | Class wrapping a `/cmd_vel` publisher with clamping. |
| **`clamp_velocity()`** | Symmetric per-axis limiter in `twist_utils.py`. |
| **`make_twist()`** | Builds a `Twist` with only `linear.x` and `angular.z` set. |
| **`/cmd_vel`** | Actuation topic consumed by `diffdrive_controller`. |
| **`/litevla/desired_twist`** | Intent topic; **not** the same as `/cmd_vel`. |
| **`cmd_vel_tester`** | Launchable node cycling test motions (subtask 10041). |

## Guided code reading

Read these in order:

1. `litevla_bridge/twist_utils.py`
   - Pure clamp and `make_twist`; no ROS imports beyond `Twist`.
   - Run `test_twist_utils.py` mentally against each function.

2. `litevla_bridge/cmd_vel_publisher.py`
   - See how `publish_twist` always clamps before publish.

3. `litevla_bridge/heartbeat_controller.py`
   - Confirm heartbeat is the production caller of `CmdVelPublisher`.

4. `litevla_bridge/cmd_vel_tester.py`
   - Isolated sim exercise; direct `/cmd_vel` for bench only.

While reading, ask:

- Who may call `CmdVelPublisher` in teleop/dummy stacks?
- Do limits here match `ros2_control.yml`?

## File and artifact index

| File or artifact | What it is | Why it matters | First thing to inspect |
|------------------|------------|----------------|------------------------|
| `twist_utils.py` | Pure velocity helpers | Testable without ROS runtime | `clamp_velocity` signature |
| `cmd_vel_publisher.py` | `/cmd_vel` adapter | Shared publish + clamp path | `publish_twist` |
| `cmd_vel_tester.py` | Sim motion cycles | Proves `/cmd_vel` reaches Webots | Step table |
| `test/test_twist_utils.py` | Unit tests | Defends clamp contracts | Boundary cases |
| `launch/cmd_vel_test.launch.py` | Sim launch | Operator smoke | Includes Webots |
| `resource/ros2_control.yml` | Sim limits | Source of truth for max speeds | `max_velocity` fields |

## API contract and data flow

### What "contract" means here

**Contract** = any call to `publish_twist(linear_x, angular_z)` results in a `geometry_msgs/Twist` on `/cmd_vel` whose components are clamped to configured maxima. `publish_stop()` always emits zeros.

### Task-local flow

```text
heartbeat_controller (production)
    ──> CmdVelPublisher.publish_twist(linear_x, angular_z)
    ──> clamp_velocity()
    ──> geometry_msgs/Twist
    ──> /cmd_vel
    ──> diffdrive_controller (Webots)

cmd_vel_tester (bench only)
    ──> CmdVelPublisher ──> /cmd_vel
```

### Contract table

| Row label | Meaning |
|-----------|---------|
| **Parameter** | ROS parameter or constructor argument name. |
| **Default** | Value when unset in launch/config. |
| **Notes** | How it relates to sim or config elsewhere. |

| Parameter | Default | Notes |
|-----------|---------|-------|
| `cmd_vel_topic` | `/cmd_vel` | Matches `configs/default.example.yaml` |
| `max_linear_vel` | `0.2` | Matches `resource/ros2_control.yml` |
| `max_angular_vel` | `0.6` | Webots diff-drive limit |

**Invariant:** Published twists never exceed configured maxima; `publish_stop()` always sends zeros.

### Naive approach vs chosen approach

| Approach | Why it seems attractive | Why we did or did not choose it |
|----------|-------------------------|---------------------------------|
| Each node publishes `/cmd_vel` directly | Fewer hops | Competing owners; inconsistent clamps |
| Shared `CmdVelPublisher` via heartbeat only | Extra indirection | One clamp implementation; one actuation owner |
| Config limits only in YAML | Single file | Runtime nodes still need enforced clamps before publish |
| Pure `twist_utils` + thin publisher | Two files | Enables fast unit tests without `rclpy` spin |

## Implementation breakdown

### Twist helpers (`twist_utils.py`)

```python
def clamp_velocity(
    linear_x: float,
    angular_z: float,
    max_linear: float,
    max_angular: float,
) -> tuple[float, float]:
    max_linear = abs(max_linear)
    max_angular = abs(max_angular)
    linear_x = max(-max_linear, min(max_linear, linear_x))
    angular_z = max(-max_angular, min(max_angular, angular_z))
    return linear_x, angular_z
```

**What to notice:** Symmetric limits; only X and Z axes used (diff-drive convention).

**Why it is written this way:** Pure functions — fully covered by `test_twist_utils.py` without ROS runtime.

**Risks and gotchas:** Does not validate NaN/Inf; heartbeat should not pass non-finite values.

### Publisher class (`cmd_vel_publisher.py`)

```python
publisher = CmdVelPublisher(node, cmd_vel_topic="/cmd_vel")
publisher.publish_twist(0.15, 0.0)
publisher.publish_stop()
```

**What to notice:** Accepts a `rclpy.Node` so heartbeat and testers share one implementation; stores `last_twist` for diagnostics.

**Why it is written this way:** Dependency injection of the node keeps the class testable and avoids duplicate publishers.

**Risks and gotchas:** Post–VLA-27 architecture routes production traffic through `heartbeat_controller`; direct `/cmd_vel` publish is for tests and legacy paths only.

### Sim tester (`cmd_vel_tester.py`, subtask 10041)

Cycles forward → left → right → stop with `step_duration_sec` dwell (default 2 s).

| Step | linear.x | angular.z |
|------|----------|-----------|
| forward | 0.15 | 0 |
| turn_left | 0 | 0.4 |
| turn_right | 0 | -0.4 |
| stop | 0 | 0 |

## Engineering decisions

**ADR: Shared publisher, heartbeat-owned `/cmd_vel`**

- **Status:** Accepted (VLA-27)
- **Context:** Multiple sources need motion, but diff-drive expects steady, clamped commands.
- **Decision:** `CmdVelPublisher` is the only `/cmd_vel` implementation; heartbeat is the only production caller.
- **Alternatives rejected:** Per-source publishers (race conditions, limit drift).
- **Consequences:** Test nodes may still use `CmdVelPublisher` directly for isolated benches.

## Verification patterns

```bash
colcon test --packages-select litevla_bridge
./ros_ws/scripts/run_webots_mvp.sh
ros2 launch litevla_bridge cmd_vel_test.launch.py
ros2 topic echo /cmd_vel
```

| Contract defended | Where |
|-------------------|-------|
| Clamp at boundaries | `test_twist_utils.py` |
| `make_twist` only sets X/Z | `test_twist_utils.py` |
| Sim motion visible | `cmd_vel_test.launch.py` |

## Failure modes and debugging path

| Symptom | Likely cause | How to investigate | Fix |
|---------|--------------|--------------------|-----|
| Robot does not move | No `/cmd_vel` or inactive controller | `ros2 topic hz /cmd_vel` | Use heartbeat path; check controllers |
| Motion faster than expected | Limits mismatch | Compare params with `ros2_control.yml` | Align `max_linear_vel` / `max_angular_vel` |
| Jerky motion | Multiple `/cmd_vel` publishers | `ros2 topic info /cmd_vel` | Remove direct publishes from action sources |
| Tester works; teleop does not | Teleop publishes intent only | `ros2 topic echo /litevla/desired_twist` | Ensure heartbeat is running |

## Engineering principle taught by this task

This task teaches **shared side-effect primitives with a single runtime owner**: extract clamp/publish logic for reuse, but route production actuation through one node so safety and timing stay centralized.

## Active learning checks

1. Why does teleop not import `CmdVelPublisher`?
2. What is the difference between `/litevla/desired_twist` and `/cmd_vel`?
3. Which file can you unit test without `rclpy.init()`?
4. What happens if dummy and heartbeat both publish `/cmd_vel`?

## Small modification exercise

Lower `max_linear_vel` to `0.1` in `cmd_vel_test.launch.py` (or params). Run the tester and confirm `ros2 topic echo /cmd_vel` never exceeds 0.1 on `linear.x`. Ensure `test_twist_utils.py` still passes.

## Related

- [camera-frame-subscriber.md](camera-frame-subscriber.md) (VLA-24)
- [control-heartbeat.md](control-heartbeat.md) (VLA-27)
