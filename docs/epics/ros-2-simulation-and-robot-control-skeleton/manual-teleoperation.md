# Manual teleoperation mode

**Epic:** ROS 2 Simulation and Robot Control Skeleton (102) · **Jira epic:** VLA-3 · **Story:** VLA-28 / 1016 · **Subtasks:** 10048 (input), 10049 (wire teleop), 10050 (record commands)

**Human-readable version (browser):** [`manual-teleoperation.html`](manual-teleoperation.html)

## Executive summary

`teleop_keyboard` is the human override path for Epic 102: it reads keys from an interactive TTY, maps held keys to bounded `(linear_x, angular_z)` twists, and publishes them on `/litevla/desired_twist` for the heartbeat controller (VLA-27). The heartbeat—not teleop—owns `/cmd_vel`, so keyboard polling can run at 50 Hz while actuation stays at a stable 25 Hz with safety timeouts. `command_recorder` logs discrete action labels for Epic 105 dataset work. **`run_teleop_sim.sh` is the supported entry point** because ROS launch-managed nodes do not receive interactive stdin reliably.

## Mental model

Think of teleop as **the human intent producer**, not the driver of motors.

It exists because operators must steer the robot before a VLA model exists, and dataset work needs human labels.

The key engineering tension is **ROS launch ergonomics vs TTY ownership**—launch backgrounds nodes; keyboards need foreground stdin.

A beginner mistake is running `ros2 launch teleop_sim.launch.py` and wondering why keys do nothing (no TTY).

A senior engineer watches **`control_mode:=teleop`**, uses `run_teleop_sim.sh`, and never publishes `/cmd_vel` from teleop.

## Backstory: why this exists

Before this module existed, operators could only run scripted dummy sequences or raw `cmd_vel` tests—no interactive driving with logging.

The naive solution would be a `teleop_keyboard` node started via `ros2 launch` alongside everything else.

That breaks because launch places nodes in the background without a controlling terminal; `stdin` is not a TTY, and key reads fail silently or error out.

So this design chooses **shell-orchestrated startup** (`run_teleop_sim.sh`): sim and heartbeat in background, `teleop_keyboard` in foreground, with readiness gates for `/clock` and active controllers.

This pattern appears in real systems whenever **interactive CLI tools** must coexist with **daemonized middleware**.

## Prerequisites

- [control-heartbeat.md](control-heartbeat.md) — consumes `/litevla/desired_twist`.
- [webots-sim-environment.md](webots-sim-environment.md) — interactive Webots for GUI teleop.
- Terminal basics: TTY, foreground vs background processes.

## Concept primer / vocabulary

| Term | Meaning in this project |
|------|-------------------------|
| **TTY** | Interactive terminal device; teleop requires `stdin.isatty()`. |
| **`desired_twist`** | Intent topic; heartbeat converts to `/cmd_vel`. |
| **`control_mode`** | Must be `teleop` for this node to run. |
| **Hold semantics** | Keys extend deadlines; release → STOP intent. |
| **`MOVE_BACKWARD`** | Teleop-only label; not in ML `DiscreteAction` enum. |
| **`commands.jsonl`** | Append-only log of action labels with timestamps. |
| **`run_teleop_sim.sh`** | Canonical operator script with TTY check. |

## Guided code reading

Read these in order:

1. `litevla_bridge/teleop_utils.py`
   - `twist_from_keys` — pure key-set → twist + label.
   - Ignore ROS; understand hold and opposing-key cancel.

2. `litevla_bridge/teleop_keyboard.py`
   - TTY guard, `tty.setcbreak`, timer poll loop.

3. `ros_ws/scripts/run_teleop_sim.sh`
   - Readiness gates and foreground teleop invocation.

4. `litevla_bridge/command_recorder.py`
   - Subscribes to `/litevla/current_action`, writes JSONL.

While reading, ask:

- Where does data enter?
- Who owns `/cmd_vel`?
- What fails when stdin is not a TTY?

## File and artifact index

| File or artifact | What it is | Why it matters | First thing to inspect |
|------------------|------------|----------------|------------------------|
| `teleop_utils.py` | Pure key mapping | Testable logic | `twist_from_keys` |
| `teleop_keyboard.py` | ROS TTY node | Publishes intent only | `stdin.isatty()` check |
| `run_teleop_sim.sh` | Operator entry | Foreground teleop | TTY check at top |
| `stop_teleop_sim.sh` | Cleanup | Kills stale sim processes | `pkill` patterns |
| `scripts/lib/sim_common.sh` | Shared wait helpers | Clock/controller gates | `wait_for_sim_clock` |
| `command_recorder.py` | JSONL logger | Dataset labels | Output path |
| `launch/teleop_sim.launch.py` | Launch graph | Non-keyboard integration tests only | Not for interactive keys |

## API contract and data flow

### What "contract" means here

**Contract** = when `control_mode:=teleop` and stdin is a TTY, poll keys at `refresh_hz`, publish clamped twists and action labels on desired topics. Never publish `/cmd_vel`. Quit key sends STOP and exits.

### Task-local flow

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

### Contract table

| Row label | Meaning |
|-----------|---------|
| **Contract** | Named rule in the teleop API. |
| **Rule** | Behavioral requirement. |

| Contract | Rule |
|----------|------|
| **Input** | Single-byte and arrow escape sequences from `stdin` (must be a TTY) |
| **Output twist** | `linear.x`, `angular.z` clamped to `max_linear_vel` / `max_angular_vel` (default 0.2 / 0.6) |
| **Action labels** | Epic 103 tokens plus teleop-only `MOVE_BACKWARD`; combos use `+` (e.g. `MOVE_FORWARD+TURN_LEFT`) |
| **Control gate** | Node idles unless `control_mode:=teleop` |
| **Quit** | `q` publishes STOP and raises `KeyboardInterrupt` |

### Naive approach vs chosen approach

| Approach | Why it seems attractive | Why we did or did not choose it |
|----------|-------------------------|---------------------------------|
| `ros2 launch` for teleop | One command starts all nodes | stdin not attached — keys don't work |
| Shell script foreground teleop | Two-step operator flow | Correct TTY ownership + readiness gates |
| Teleop publishes `/cmd_vel` | Direct control | Bypasses heartbeat safety and timing |
| Game-style key holds | Slightly more code | Better driving feel; diagonal labels for datasets |

## Implementation breakdown

### Key map and hold semantics (`teleop_utils.py`)

Game-style driving: keys extend per-key hold deadlines; opposing keys (forward vs backward, left vs right) cancel each other.

```python
def twist_from_keys(keys, *, max_linear_vel, max_angular_vel) -> tuple[float, float, str]:
    # forward + left → (max_linear, max_angular, "MOVE_FORWARD+TURN_LEFT")
```

**What to notice:** `MOVE_BACKWARD` is teleop-only and outside the ML `DiscreteAction` enum.

**Why it is written this way:** Dataset labels for forward/turn/stop stay aligned with Epic 103; backward is an operator affordance.

**Risks and gotchas:** `key_to_action()` remains for unit tests; runtime uses `twist_from_keys()` on the active key set.

### TTY node (`teleop_keyboard.py`)

```python
if not sys.stdin.isatty():
    self.get_logger().error("stdin is not a TTY — run teleop in an interactive terminal")
```

**What to notice:** `tty.setcbreak` + `select` non-blocking read keeps ROS timers responsive.

**Why it is written this way:** Foreground terminal ownership is a hard requirement.

**Risks and gotchas:** Do not run via `ros2 launch teleop_sim.launch.py` for keyboard input—launch places teleop in the background without a controlling TTY.

### Interactive Webots (`webots_launcher.py`, `webots_sim.launch.py`)

`InteractiveWebotsLauncher` strips `--batch` so the GUI camera follows the robot during teleop (`interactive:=true`).

### Lifecycle scripts

| Script | Role |
|--------|------|
| `run_teleop_sim.sh` | TTY check → Webots interactive → wait `/clock` + controllers → heartbeat + recorder → foreground `teleop_keyboard` |
| `stop_teleop_sim.sh` | `pkill` stale Webots/ROS teleop processes |
| `scripts/lib/sim_common.sh` | Shared wait helpers (`wait_for_sim_clock`, `wait_for_diffdrive_stack`, …) |

**Design note:** `ros_ws/scripts/lib/sim_common.sh` is tracked in git (root `.gitignore` uses `/lib/` only, not `ros_ws/scripts/lib/`). Teleop and episode capture share the same readiness gates.

### Command recorder (`command_recorder.py`)

Subscribes to `/litevla/current_action`, appends JSONL rows with sim timestamps.

| Mode | Script | Output |
|------|--------|--------|
| Casual teleop | `run_teleop_sim.sh` | `outputs/teleop/<ts>/commands.jsonl` |
| Full episode capture | `run_episode_capture.sh` (VLA-42) | `data/raw/episodes/<id>/commands.jsonl` + frames |

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

## Failure modes and debugging path

| Symptom | Likely cause | How to investigate | Fix |
|---------|--------------|--------------------|-----|
| "stdin is not a TTY" | Launched via `ros2 launch` or IDE task | Check how teleop was started | Use `./ros_ws/scripts/run_teleop_sim.sh` in real terminal |
| Keys ignored | `control_mode` not `teleop` | Node logs on startup | Set `control_mode:=teleop` |
| Robot stops immediately | Heartbeat timeout / grace | Diagnostics `action_age_ms` | Teleop script sets shorter timeout + grace |
| No JSONL file | Recorder not started | Check script background steps | Use `run_teleop_sim.sh` |
| Webots frozen / no clock | Stale process | `ros2 topic hz /clock` | `stop_teleop_sim.sh` and relaunch |

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

## Engineering principle taught by this task

This task teaches **separating interactive I/O from actuation**: human input produces intent on a schedule the heartbeat understands; TTY/process ownership is part of the system design, not an implementation detail.

## Active learning checks

1. Why must teleop run in the foreground of a real terminal?
2. Which topic does teleop publish, and which topic moves the robot?
3. Why is `MOVE_BACKWARD` not in the ML action enum?
4. What readiness gates does `run_teleop_sim.sh` wait for before accepting keys?

## Small modification exercise

Change hold duration in `teleop_utils.py` (e.g. 120 ms → 200 ms). Run `test_teleop_utils.py`, then teleop briefly—keys should feel "stickier." Confirm heartbeat still receives desired twists via `ros2 topic echo /litevla/desired_twist`.

## Related

- [control-heartbeat.md](control-heartbeat.md) (VLA-27)
- [dummy-action-generator.md](dummy-action-generator.md) (VLA-26)
- [webots-sim-environment.md](webots-sim-environment.md) (VLA-23)
- [simulation-data-capture.md](../dataset-generation-labeling-and-validation/simulation-data-capture.md) (VLA-42 episode capture)
