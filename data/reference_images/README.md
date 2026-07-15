# Reference camera frames (Purshottam / VLA preprocessing)

640×480 **BGR PNG** front-camera views from the Lite-VLA Webots robot.

| File | Expected action | How it is produced |
|------|-----------------|-------------------|
| `red_cone_centered.png` | MOVE_FORWARD | Robot drives ahead; cube centered ~1.5–2 m |
| `red_cone_left.png` | TURN_LEFT | Robot drives to offset pose; cube on left of frame |
| `red_cone_right.png` | TURN_RIGHT | Robot drives to offset pose; cube on right of frame |
| `stop_barrier_close.png` | STOP | Robot drives close to fixed cube |

The **red cube stays fixed** in `mvp_arena.wbt` (`translation 2 0 0.1`). Only the **robot moves** via `/cmd_vel` and `/odom`.

## Dataset labels (VLA-43)

Action labels for the builder live in [`manifest.json`](manifest.json). Run:

```bash
python scripts/build_starter_dataset.py
```

after capturing the four PNGs above.

**Note (2026-07-02):** If Webots headless capture times out, `red_cone_left.png` / `red_cone_right.png` may be copied from `block_positions/`; `stop_barrier_close.png` may be a centered-crop placeholder until `./ros_ws/scripts/capture_block_reference_images.sh close` succeeds.

## Recommended: capture by driving (simulation motion)

```bash
./ros_ws/scripts/capture_reference_frames_by_driving.sh
```

Or manually:

```bash
source /opt/ros/jazzy/setup.bash
source ros_ws/install/setup.bash
ros2 launch litevla_bridge reference_capture.launch.py
```

Requires Webots (`./ros_ws/scripts/install_webots.sh`).

## Alternative: static headless poses (no ROS drive)

If you only need quick PNGs without running the full ROS loop:

```bash
./ros_ws/scripts/capture_block_reference_images.sh all
```

## Tuning

Drive targets live in `litevla_bridge/reference_frame_capture.py` (`DEFAULT_SCENARIOS`). Adjust `x`, `y`, `yaw` if framing needs tweaking after a test run.
