# Manual teleoperation mode

**Epic:** ROS 2 Simulation and Robot Control Skeleton (102) · **Jira epic:** VLA-3 · **Story:** VLA-28 / 1016 · **Subtasks:** 10048 (input), 10049 (wire teleop), 10050 (record commands)

**Human-readable version (browser):** [`manual-teleoperation.html`](manual-teleoperation.html)

## Executive summary

`teleop_keyboard` is the human override path for Epic 102: it reads keys from an interactive TTY, maps held keys to bounded `(linear_x, angular_z)` twists, and publishes them on `/litevla/desired_twist` for the heartbeat controller (VLA-27). The heartbeat—not teleop—owns `/cmd_vel`, so keyboard polling can run at 50 Hz while actuation stays at a stable 25 Hz with safety timeouts. `command_recorder` logs discrete action labels for Epic 105 dataset work. **`run_teleop_sim.sh` is the supported entry point** because ROS launch-managed nodes do not receive interactive stdin reliably.

## API contract and data flow

```text
TTY keys ──> teleop_keyboard (50 Hz poll, 120 ms hold)
         ──> /litevla/desired_twist (Twist)
         ──> /litevla/current_action (String label)
              │
              ▼
         heartbeat_controller (25 Hz, action_timeout 200 ms)
              │
              ├──> /cmd_vel ──> diffdrive_controller ──> Webots
              └──> /litevla/diagnostics

command_recorder <── /litevla/current_action ──> outputs/teleop/<ts>/commands.jsonl
```

| Contract | Rule |
|----------|------|
| Input | Single-byte and arrow escape sequences from `stdin` (must be a TTY) |
| Output twist | `linear.x`, `angular.z` clamped to `max_linear_vel` / `max_angular_vel` (default 0.2 / 0.6) |
| Action labels | Epic 103 tokens plus teleop-only `MOVE_BACKWARD`; combos use `+` (e.g. `MOVE_FORWARD+TURN_LEFT`) |
| Control gate | Node idles unless `control_mode:=teleop` |
| Quit | `q` publishes STOP and raises `KeyboardInterrupt` |

**Trade-off:** Shell-orchestrated startup (`run_teleop_sim.sh`) trades “one `ros2 launch`” ergonomics for correct stdin ownership and readiness gates (`/clock`, active controllers) before keys are accepted.

## Implementation breakdown

### Key map and hold semantics (`teleop_utils.py`)

Game-style driving: keys extend per-key hold deadlines; opposing keys (forward vs backward, left vs right) cancel each other.

```python
def twist_from_keys(keys, *, max_linear_vel, max_angular_vel) -> tuple[float, float, str]:
    # forward + left → (max_linear, max_angular, "MOVE_FORWARD+TURN_LEFT")
```

- **Design note:** `MOVE_BACKWARD` is teleop-only and intentionally outside the ML `DiscreteAction` enum so dataset labels stay aligned with Epic 103 vocabulary for forward/turn/stop.
- **Gotcha:** `key_to_action()` remains for unit tests; runtime uses `twist_from_keys()` on the active key set.

### TTY node (`teleop_keyboard.py`)

```python
if not sys.stdin.isatty():
    self.get_logger().error("stdin is not a TTY — run teleop in an interactive terminal")
```

- **Design note:** `tty.setcbreak` + `select` non-blocking read keeps ROS timers responsive.
- **Gotcha:** Do not run via `ros2 launch teleop_sim.launch.py` for keyboard input—launch places teleop in the background without a controlling TTY.

### Interactive Webots (`webots_launcher.py`, `webots_sim.launch.py`)

`InteractiveWebotsLauncher` strips `--batch` so the GUI camera follows the robot during teleop (`interactive:=true`).

### Lifecycle scripts

| Script | Role |
|--------|------|
| `run_teleop_sim.sh` | TTY check → Webots interactive → wait `/clock` + controllers → heartbeat + recorder → foreground `teleop_keyboard` |
| `stop_teleop_sim.sh` | `pkill` stale Webots/ROS teleop processes |
| `scripts/lib/sim_common.sh` | Shared wait helpers (`wait_for_sim_clock`, `wait_for_diffdrive_stack`, …) |

**Design note:** `ros_ws/scripts/lib/sim_common.sh` is tracked in git (root `.gitignore` uses `/lib/` only, not `ros_ws/scripts/lib/`). Teleop and episode capture share the same readiness gates (`wait_for_sim_clock`, `wait_for_diffdrive_stack`, `cleanup_stale_sim_processes`).

### Command recorder (`command_recorder.py`)

Subscribes to `/litevla/current_action`, appends JSONL rows with sim timestamps.

| Mode | Script | Output |
|------|--------|--------|
| Casual teleop | `run_teleop_sim.sh` | `outputs/teleop/<ts>/commands.jsonl` |
| Full episode capture | `run_episode_capture.sh` (VLA-42) | `data/raw/episodes/<id>/commands.jsonl` + frames |

See [simulation-data-capture.md](../dataset-generation-labeling-and-validation/simulation-data-capture.md) for the dataset capture entry point.

## Engineering decisions

**ADR: Shell script owns teleop stdin**

- **Status:** Accepted
- **Context:** `ros2 launch` backgrounds nodes; keyboard teleop requires foreground stdin.
- **Decision:** `run_teleop_sim.sh` launches sim/heartbeat/recorder in background, `teleop_keyboard` in foreground.
- **Alternatives rejected:** Launch-only teleop (stdin broken); separate terminal wrapper without readiness gates (fragile controller startup).
- **Consequences:** Document the script as canonical; keep `teleop_sim.launch.py` for non-keyboard integration tests only.

**ADR: Game-style holds vs discrete tap-to-step**

- **Status:** Accepted
- **Decision:** 50 Hz poll, 120 ms hold after last key event; release → STOP.
- **Consequences:** Better driving feel; recorder sees compound labels for diagonal motion.

## Verification patterns

```bash
source /opt/ros/jazzy/setup.bash
source ros_ws/install/setup.bash
colcon test --packages-select litevla_bridge   # test_teleop_utils.py

# Interactive terminal (GNOME Terminal / Konsole — not Cursor task output)
./ros_ws/scripts/run_teleop_sim.sh
./ros_ws/scripts/stop_teleop_sim.sh
ls outputs/teleop/*/commands.jsonl
```

| Test / command | Contract defended |
|----------------|-----------------|
| `test_teleop_utils.py` | Key combos, hold expiry, opposing-key cancellation |
| `run_teleop_sim.sh` | TTY guard, `/clock`, active `joint_state_broadcaster` + `diffdrive_controller` |
| JSONL output | Recorder receives action labels with timestamps |

## Key map

| Key | Behavior |
|-----|----------|
| `w` / `↑` | Forward |
| `s` / `↓` | Backward (`MOVE_BACKWARD`) |
| `a` / `←` | Turn left |
| `d` / `→` | Turn right |
| `x` / `space` | Brake (STOP) |
| `q` | Quit |

## Control modes

| `control_mode` | Behavior |
|----------------|----------|
| `dummy` | Dummy generator active; teleop idle |
| `teleop` | Teleop active; dummy idle |
| `model` | Reserved (Epic 108) |

## Related

- [control-heartbeat.md](control-heartbeat.md) (VLA-27)
- [dummy-action-generator.md](dummy-action-generator.md) (VLA-26)
- [webots-sim-environment.md](webots-sim-environment.md) (VLA-23)
- [simulation-data-capture.md](../dataset-generation-labeling-and-validation/simulation-data-capture.md) (VLA-42 episode capture)
