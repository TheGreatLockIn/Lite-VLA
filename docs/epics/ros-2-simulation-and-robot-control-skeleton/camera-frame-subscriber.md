# Camera frame subscriber

**Epic:** ROS 2 Simulation and Robot Control Skeleton (102) · **Jira epic:** VLA-3 · **Story:** VLA-24 / 1012 · **Subtasks:** 10036 (subscriber), 10037 (conversion), 10038 (frame save)

**Human-readable version (browser):** [`camera-frame-subscriber.html`](camera-frame-subscriber.html)

## Executive summary

`camera_subscriber` is the **perception ingress** for Epic 102: it subscribes to `sensor_msgs/Image` (default `/image_raw`), converts each message to an RGB `numpy` ndarray, and keeps the latest frame in node state for future VLA inference (Epic 108). Optional rate-limited PNG recording supports dataset debugging without flooding disk.

The heartbeat controller optionally treats camera freshness as a safety input—stale frames can force `STOP` when `require_frame:=true`.

## Mental model

Think of this node as **the robot's eyes at the ROS boundary**.

It exists because ML and dataset pipelines need a stable, decoded RGB array—not raw `sensor_msgs/Image` bytes scattered across nodes.

The key engineering tension is **always-fresh latest frame vs storage cost** when recording PNGs.

A beginner mistake is subscribing to `/image_raw/image_color` directly and missing the Webots remap in `webots_sim.launch.py`.

A senior engineer watches **frame age** in heartbeat diagnostics and uses sensor QoS appropriately for camera streams.

## Backstory: why this exists

Before this module existed, every future inference node would need its own `cv_bridge` conversion, encoding handling, and "latest frame" state.

The naive solution would be to save images inside Webots or read files from disk in each node.

That breaks because runtime inference needs synchronized ROS timestamps, consistent RGB layout, and one place to log first-frame geometry for operators.

So this design chooses **`image_utils.ros_image_to_rgb()` + `CameraSubscriber` node** with optional rate-limited disk capture.

This pattern appears in real systems as a **perception adapter** between sensor middleware and ML code.

## Prerequisites

- `sensor_msgs/Image` and common encodings (`rgb8`, `bgr8`).
- [webots-sim-environment.md](webots-sim-environment.md) — `/image_raw` remap from Webots.
- Basic `numpy` image layout (H×W×3 `uint8`).

## Concept primer / vocabulary

| Term | Meaning in this project |
|------|-------------------------|
| **`/image_raw`** | Canonical camera topic; `sensor_msgs/Image`. |
| **`cv_bridge`** | ROS library converting `Image` messages to OpenCV/numpy arrays. |
| **`latest_frame`** | Most recent decoded RGB ndarray on the node instance. |
| **`latest_stamp`** | ROS timestamp of the latest successful decode. |
| **`qos_profile_sensor_data`** | QoS preset for high-rate sensor streams (best effort). |
| **`record_interval_sec`** | Minimum seconds between PNG writes when recording. |
| **`require_frame`** | Heartbeat parameter: if true, stale camera forces STOP. |

## Guided code reading

Read these in order:

1. `litevla_bridge/image_utils.py`
   - `ros_image_to_rgb` encoding support.
   - Ignore error paths on first pass, then read them.

2. `litevla_bridge/camera_subscriber.py`
   - Subscription QoS, `_on_image` callback, `latest_frame` updates.
   - Optional PNG save gate.

3. `launch/camera_subscriber.launch.py`
   - Parameters mirroring `configs/default.example.yaml`.

4. `litevla_bridge/heartbeat_controller.py` (camera section)
   - How frame age participates in timeout logic.

While reading, ask:

- Where does data enter?
- What happens on decode failure?
- Who consumes `latest_frame` today vs in Epic 108?

## File and artifact index

| File or artifact | What it is | Why it matters | First thing to inspect |
|------------------|------------|----------------|------------------------|
| `image_utils.py` | Image conversion | Single encoding policy | `ros_image_to_rgb` |
| `camera_subscriber.py` | ROS subscriber node | Latest frame state | `_on_image` |
| `test/test_image_utils.py` | Unit tests | rgb8/bgr8 contracts | Shape assertions |
| `launch/camera_subscriber.launch.py` | Launch entry | Parameter defaults | `record_frames` |
| `configs/default.example.yaml` | Config mirror | `ros.image_topic`, save dir | `ros` section |
| `outputs/frames/` | Recorded PNGs | Debug captures | Timestamp in filename |

## API contract and data flow

### What "contract" means here

**Contract** = subscribe on `image_topic`, expose `latest_frame` as H×W×3 `uint8` RGB after successful decode; on failure, log and skip update (previous frame remains). Optional PNG saves respect `record_interval_sec`.

### Task-local flow

```text
/image_raw (sensor_msgs/Image)
    ──> camera_subscriber._on_image
    ──> ros_image_to_rgb()  [cv_bridge]
    ──> latest_frame (H×W×3 uint8), latest_stamp
    ──> optional PNG → outputs/frames/  (record_interval_sec gate)
```

### Contract table

| Row label | Meaning |
|-----------|---------|
| **Parameter** | ROS parameter name. |
| **Default** | Value if unset. |
| **Config mirror** | Matching key in `configs/default.example.yaml`. |

| Parameter | Default | Config mirror |
|-----------|---------|---------------|
| `image_topic` | `/image_raw` | `ros.image_topic` |
| `record_frames` | `false` | `ros.record_frames` |
| `frame_save_dir` | `outputs/frames` | `ros.frame_save_dir` |
| `record_interval_sec` | `1.0` | Max save rate when recording |

**Invariant:** `latest_frame` is always the most recent successfully decoded image; decode failures log and skip update.

### Naive approach vs chosen approach

| Approach | Why it seems attractive | Why we did or did not choose it |
|----------|-------------------------|---------------------------------|
| Convert in every ML node | No shared node | Duplicated encoding bugs |
| Save every frame to disk | Complete logs | Floods disk at camera rate |
| Rate-limited optional PNG | May miss frames | Good debug trade-off |
| Central `CameraSubscriber` | One more node | Single decode path + heartbeat integration |

## Implementation breakdown

### Image conversion (`image_utils.py`)

```python
def ros_image_to_rgb(msg: Image) -> np.ndarray:
    # Supports rgb8 and bgr8 via cv_bridge
```

**What to notice:** Centralized encoding handling.

**Why it is written this way:** Avoids duplicating `cv_bridge` logic in inference nodes later.

**Risks and gotchas:** Webots may publish on `/image_raw/image_color`; `webots_sim.launch.py` remaps to `/image_raw`. Unsupported encodings raise—extend `image_utils` if the sim changes.

### Subscriber node (`camera_subscriber.py`)

**What to notice:** Logs first frame geometry and encoding once (operator confidence). Uses `qos_profile_sensor_data`.

**Why it is written this way:** Exposes `latest_frame` / `latest_stamp` for synchronous reads from future orchestration code.

**Risks and gotchas:** `latest_frame` is not thread-locked for heavy concurrent access—Epic 108 orchestration should read from the node's callback context or add synchronization if needed.

### Heartbeat coupling

`heartbeat_controller` optionally requires fresh frames (`require_frame`, `frame_timeout_sec`). Teleop sets `require_frame:=false` so driving works before camera warmup.

## Engineering decisions

**ADR: Latest-frame holder, not a video pipeline**

- **Status:** Accepted
- **Context:** MVP needs one RGB array for inference and optional debug PNGs, not a full recorder.
- **Decision:** Node state holds latest decode; optional interval-gated PNG save.
- **Alternatives rejected:** Always-on full-rate recording (disk cost); per-node conversion (duplication).
- **Consequences:** Epic 108 must poll or extend with a service if it needs pull-based access.

## Verification patterns

```bash
colcon test --packages-select litevla_bridge   # test_image_utils.py
./ros_ws/scripts/run_webots_mvp.sh             # terminal 1
ros2 launch litevla_bridge camera_subscriber.launch.py record_frames:=true
```

| Test | Contract defended |
|------|-------------------|
| `test_image_utils.py` | rgb8/bgr8 → consistent RGB ndarray shape |
| Live launch | First-frame log; PNG files at ≤ 1 Hz when recording |

## Failure modes and debugging path

| Symptom | Likely cause | How to investigate | Fix |
|---------|--------------|--------------------|-----|
| No first-frame log | Wrong topic or sim not publishing | `ros2 topic hz /image_raw` | Check Webots remap; wait for controllers |
| Decode errors in log | Unexpected encoding | Echo one message's `encoding` field | Extend `image_utils.py` |
| Heartbeat always STOP | `require_frame` + stale camera | `ros2 topic echo /litevla/diagnostics` | Warm up camera; teleop uses `require_frame:=false` |
| Empty `outputs/frames/` | `record_frames:=false` or interval gate | Check launch params | Set `record_frames:=true` |
| Huge disk usage | Interval set too low | Check `record_interval_sec` | Increase interval |

## Engineering principle taught by this task

This task teaches **adapter nodes at sensor boundaries**: convert middleware messages once into a stable in-memory representation downstream code can trust.

## Active learning checks

1. Why does Webots use `/image_raw/image_color` before remap?
2. What QoS profile does the subscriber use and why?
3. How does heartbeat use frame age when `require_frame:=true`?
4. What happens to `latest_frame` when one message fails to decode?

## Small modification exercise

Set `record_interval_sec:=2.0` and `record_frames:=true`. Capture for 10 seconds and count PNG files—should be ≤ 6. Run `test_image_utils.py` to ensure conversion still passes.

## Related

- [webots-sim-environment.md](webots-sim-environment.md) (VLA-23)
- [control-heartbeat.md](control-heartbeat.md) (VLA-27)
- [`../../../../configs/default.example.yaml`](../../../../configs/default.example.yaml)
