# Camera frame subscriber

**Epic:** ROS 2 Simulation and Robot Control Skeleton (102) · **Jira:** VLA-24 / Story 1012 · **Subtasks:** 10036 (subscriber), 10037 (image conversion), 10038 (frame save)

**Human-readable version (browser):** [`camera-frame-subscriber.html`](camera-frame-subscriber.html)

Subscribe to the simulation camera topic, convert frames to RGB numpy arrays, and optionally save debug frames for dataset work.

## Intent

Receive camera frames from Webots (or a physical camera) and keep the latest frame in node state for future VLA inference (Epic 108).

## Artifacts

| Path | Purpose |
|------|---------|
| `litevla_bridge/camera_subscriber.py` | ROS node — subscribes, logs first frame, holds `latest_frame` |
| `litevla_bridge/image_utils.py` | `ros_image_to_rgb()` via `cv_bridge` |
| `launch/camera_subscriber.launch.py` | Launch with topic + recording params |
| `config/bridge_params.yaml` | Default `image_topic`, `record_frames`, `frame_save_dir` |
| `test/test_image_utils.py` | Unit tests for RGB/BGR conversion |

## Parameters

| Param | Default | Maps to `configs/default.example.yaml` |
|-------|---------|----------------------------------------|
| `image_topic` | `/image_raw` | `ros.image_topic` |
| `record_frames` | `false` | `ros.record_frames` |
| `frame_save_dir` | `outputs/frames` | `ros.frame_save_dir` |
| `record_interval_sec` | `1.0` | (save at most 1 Hz when recording) |

## Run

With Webots sim running (`./ros_ws/scripts/run_webots_mvp.sh`):

```bash
source /opt/ros/jazzy/setup.bash
source ros_ws/install/setup.bash

# Option A — launch file
ros2 launch litevla_bridge camera_subscriber.launch.py

# Option B — direct run with recording
ros2 run litevla_bridge camera_subscriber --ros-args \
  -p image_topic:=/image_raw \
  -p record_frames:=true \
  -p frame_save_dir:=outputs/frames
```

**Pass:** Logs first frame `WxH encoding=...`; `latest_frame` updates each callback; PNG files appear under `outputs/frames/` when recording is enabled.

## Data flow

```text
/image_raw (sensor_msgs/Image)
    → camera_subscriber._on_image
    → ros_image_to_rgb() → latest_frame (HxWx3 uint8)
    → optional PNG save (record_interval_sec)
```

## Validation

```bash
colcon test --packages-select litevla_bridge   # test_image_utils.py
ros2 launch litevla_bridge webots_sim.launch.py   # terminal 1
ros2 launch litevla_bridge camera_subscriber.launch.py record_frames:=true  # terminal 2
```

## Related

- [webots-sim-environment.md](webots-sim-environment.md) (VLA-23)
- [`../../../../configs/default.example.yaml`](../../../../configs/default.example.yaml)
