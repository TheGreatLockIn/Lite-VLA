# Simulation data capture tool

**Epic:** Dataset Generation, Labeling, and Validation (105) · **Jira epic:** VLA-6 · **Story:** VLA-42 / 1030 · **Subtasks:** 10090 (frame recorder), 10091 (command labels), 10092 (episode metadata)

**Human-readable version (browser):** [`simulation-data-capture.html`](simulation-data-capture.html)

## Executive summary

VLA-42 owns **Layer A raw capture** during Webots keyboard teleop: each session writes a self-contained directory under `data/raw/episodes/<episode_id>/` with `episode.json`, sim-stamped `commands.jsonl`, and `frames/*.png`. VLA-43 joins frames to commands and emits VLA-41 training JSONL. Capture reuses Epic 102 teleop nodes; the entry point is `run_episode_capture.sh` (interactive TTY required).

## API contract and data flow

```text
run_episode_capture.sh ──> init_raw_episode() ──> episode.json + frames/
        │
        ├──> webots_sim.launch.py (interactive)
        ├──> heartbeat_controller (teleop mode)
        ├──> camera_subscriber (record_frames @ ~5 Hz)
        ├──> command_recorder (episode_dir set)
        └──> teleop_keyboard (foreground)

/litevla/current_action ──> command_recorder ──> commands.jsonl
/image_raw ──> camera_subscriber ──> frames/{sec}_{nanosec}.png
```

| Contract | Rule |
|----------|------|
| Episode init | `episode.json` written **before** ROS nodes start |
| Frame naming | `{sim_sec}_{sim_nanosec:09d}.png` from image header stamp |
| Command log | Append on **action transition**; includes `sim_stamp_sec/nanosec` |
| Sim clock | All recorders use `use_sim_time:=true` |
| Entry point | `./ros_ws/scripts/run_episode_capture.sh` — not plain `run_teleop_sim.sh` |

**Trade-off:** Separate capture script keeps casual teleop (`outputs/teleop/`) lightweight; full episodes are opt-in.

## Implementation breakdown

### Episode layout (`litevla/data/episode.py`)

```python
def init_raw_episode(*, instruction, source="teleop", world="mvp_arena.wbt", record_frames_hz=5.0) -> Path:
    # Creates data/raw/episodes/<id>/episode.json and frames/
```

- **`EpisodeMetadata`** validated against `data/schema/episode.schema.json` before write.
- **Design note:** Episode helpers live in `litevla/` (not ROS) so tests and VLA-43 builder run without a sim.

### Command rows (`litevla_bridge/capture_utils.py`, `command_recorder.py`)

```python
def build_command_record(*, stamp, sim_stamp_sec, sim_stamp_nanosec, source, action, linear_x, angular_z):
    ...
```

- **`episode_dir` param:** When set, writes `commands.jsonl` directly in the episode folder (no timestamp subdir under `outputs/teleop/`).
- **Gotcha:** Recording triggers on `/litevla/current_action` changes, not every twist tick — many frames may share one label until the next action transition.

### Frame recorder (`camera_subscriber.py`)

Existing node; capture script sets:

```bash
-p record_frames:=true
-p frame_save_dir:="${EPISODE_DIR}/frames"
-p record_interval_sec:=0.2   # 5 Hz default
```

- **Design note:** Rate limit uses wall-clock monotonic time; filename uses **sim stamp** from the image message — join key for VLA-43.

### Orchestration (`run_episode_capture.sh`)

1. TTY check (same constraint as teleop).
2. `init_raw_episode()` via Python with instruction from CLI/env.
3. Launch Webots + wait for `/clock` and controllers.
4. Start heartbeat, `camera_subscriber`, `command_recorder`, foreground teleop.
5. Stop with `./ros_ws/scripts/stop_teleop_sim.sh` (also kills `camera_subscriber`).

## Engineering decisions

**ADR: Sim-time alignment (10090)**  
Status: Accepted  
Decision: Reuse `camera_subscriber` filename convention; command rows add matching sim stamp fields.  
Consequences: VLA-43 forward-fills without a separate index file.

**ADR: Episode metadata before ROS (10092)**  
Status: Accepted  
Decision: Shell/Python writes `episode.json` first; recorders only append runtime artifacts.  
Consequences: Crashed sim still leaves session intent on disk.

## Verification patterns

```bash
pytest tests/test_episode_capture.py -q
pytest ros_ws/src/litevla_bridge/test/test_capture_utils.py -q

# Manual smoke (interactive terminal + Webots)
./ros_ws/scripts/run_episode_capture.sh --instruction "Move toward the red cube."
./ros_ws/scripts/stop_teleop_sim.sh
ls data/raw/episodes/<latest>/
```

Defends: episode schema validation, sim stamp in command records, frame filename parser.

## Related

- [manual-teleoperation.md](../ros-2-simulation-and-robot-control-skeleton/manual-teleoperation.md) (Epic 102 teleop stack)
- [synthetic-starter-dataset.md](synthetic-starter-dataset.md) (VLA-43 consumes raw episodes)
- [`data/schema/episode.schema.json`](../../../../data/schema/episode.schema.json)

## Open questions

- **Dummy/scripted capture:** `episode.json` `source` enum includes `dummy` and `scripted`; wiring a dummy-driven capture session reuses the same layout (future work).
