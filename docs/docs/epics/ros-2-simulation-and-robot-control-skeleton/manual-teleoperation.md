# Manual teleoperation mode

**Epic:** ROS 2 Simulation and Robot Control Skeleton (102) · **Jira:** VLA-28 / Story 1016 · **Subtasks:** 10048 (input method), 10049 (wire teleop), 10050 (record commands)

**Human-readable version (browser):** [`manual-teleoperation.html`](manual-teleoperation.html)

Keyboard driving for testing and dataset capture, integrated with the heartbeat safety layer.

## Intent

Let a human override dummy/model commands via keyboard; log commands with timestamps for Epic 105 datasets.

## Artifacts

| Path | Purpose |
|------|---------|
| `litevla_bridge/teleop_keyboard.py` | Keyboard → desired twist + action |
| `litevla_bridge/teleop_utils.py` | Key map (`w`/`a`/`d`/`s`/`x`/arrows) |
| `litevla_bridge/command_recorder.py` | JSONL log under `outputs/teleop/<timestamp>/` |
| `launch/teleop_sim.launch.py` | Webots + heartbeat + teleop + recorder |
| `launch/full_stack.launch.py` | Epic 102 integration demo (`control_mode` switch) |

## Key map

| Key | Action |
|-----|--------|
| `w` / `↑` | `MOVE_FORWARD` |
| `a` / `←` | `TURN_LEFT` |
| `d` / `→` | `TURN_RIGHT` |
| `s` | `SLOW_DOWN` |
| `x` / `space` | `STOP` (estop) |
| `q` | Quit |

## Control modes

| `control_mode` | Behavior |
|----------------|----------|
| `dummy` | Dummy generator active; teleop idle |
| `teleop` | Teleop active; dummy idle |
| `model` | Reserved (Epic 108) |

## Run

```bash
source ros_ws/install/setup.bash

# Teleop in Webots (interactive terminal required)
./ros_ws/scripts/run_teleop_sim.sh

# Full stack demo (dummy mode + camera)
ros2 launch litevla_bridge full_stack.launch.py control_mode:=dummy
```

`run_teleop_sim.sh` starts Webots, heartbeat, and command recording in the
background, then runs `teleop_keyboard` in the foreground so `w`/`a`/`d` are read
from the active terminal. Do not use `ros2 launch ... teleop_sim.launch.py` for
keyboard driving because launch-managed nodes do not receive interactive stdin.

**Teleop only** (sim already running):

```bash
ros2 run litevla_bridge teleop_keyboard --ros-args -p control_mode:=teleop
ros2 run litevla_bridge command_recorder
```

## Command log format

`outputs/teleop/<timestamp>/commands.jsonl`:

```json
{"stamp": "...", "source": "teleop", "action": "TURN_LEFT", "linear_x": 0.0, "angular_z": 0.6}
```

## Validation

```bash
colcon test --packages-select litevla_bridge
ros2 launch litevla_bridge teleop_sim.launch.py
ls outputs/teleop/*/commands.jsonl
```

## Related

- [control-heartbeat.md](control-heartbeat.md) (VLA-27)
- [dummy-action-generator.md](dummy-action-generator.md) (VLA-26)
