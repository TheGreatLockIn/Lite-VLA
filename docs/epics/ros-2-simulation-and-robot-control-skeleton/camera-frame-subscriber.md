# Camera frame subscriber

**Epic:** ROS 2 Simulation and Robot Control Skeleton (102) · **Jira epic:** VLA-3 · **Story:** VLA-24 / 1012 · **Subtasks:** 10036 (subscriber), 10037 (conversion), 10038 (frame save)

**Human-readable version (browser):** [`camera-frame-subscriber.html`](camera-frame-subscriber.html)

## Executive summary

`camera_subscriber` is the **perception ingress** for Epic 102: it subscribes to `sensor_msgs/Image` (default `/image_raw`), converts each message to an RGB `numpy` ndarray, and keeps the latest frame in node state for future VLA inference (Epic 108). Optional rate-limited PNG recording supports dataset debugging without flooding disk.

## API contract and data flow

```text
/image_raw (sensor_msgs/Image)
    ──> camera_subscriber._on_image
    ──> ros_image_to_rgb()  [cv_bridge]
    ──> latest_frame (H×W×3 uint8), latest_stamp
    ──> optional PNG → outputs/frames/  (record_interval_sec gate)
```

| Parameter | Default | Config mirror |
|-----------|---------|---------------|
| `image_topic` | `/image_raw` | `ros.image_topic` |
| `record_frames` | `false` | `ros.record_frames` |
| `frame_save_dir` | `outputs/frames` | `ros.frame_save_dir` |
| `record_interval_sec` | `1.0` | Max save rate when recording |

**Invariant:** `latest_frame` is always the most recent successfully decoded image; decode failures log and skip update.

## Implementation breakdown

### Image conversion (`image_utils.py`)

```python
def ros_image_to_rgb(msg: Image) -> np.ndarray:
    # Supports rgb8 and bgr8 via cv_bridge
```

- **Design note:** Centralizing conversion avoids duplicating `cv_bridge` encoding logic in inference nodes later.
- **Gotcha:** Webots may publish on `/image_raw/image_color`; `webots_sim.launch.py` remaps to `/image_raw`.

### Subscriber node (`camera_subscriber.py`)

- Logs first frame geometry and encoding once (operator confidence).
- Exposes `latest_frame` / `latest_stamp` for synchronous reads from future orchestration code.

### Heartbeat coupling

`heartbeat_controller` optionally requires fresh frames (`require_frame`, `frame_timeout_sec`). Teleop sets `require_frame:=false` so driving works before camera warmup.

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

## Related

- [webots-sim-environment.md](webots-sim-environment.md) (VLA-23)
- [`../../../../configs/default.example.yaml`](../../../../configs/default.example.yaml)
