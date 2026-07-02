# Command smoothing

**Epic:** Action Interface, Parser, and Safety Layer (103) · **Jira:** Story 1022

**Human-readable version (browser):** [`command-smoothing.html`](command-smoothing.html)

## Executive summary

`litevla.actions.smoothing` is the **rate-limiting layer** between the safety gate (Story 1021) and ROS `/cmd_vel` publishing. It reduces jerky velocity changes when VLA inference updates at ~5 Hz while the low-level heartbeat runs at 10–100 Hz (RSK-05). The MVP uses a **per-axis slew-rate limiter** with an immediate **STOP bypass** so emergency and parse-failure stops are never delayed.

Subtasks covered: **10066** (strategy), **10067** (rate limiter), **10068** (STOP bypass), **10254** and **10255** (learning).

## API contract and data flow

### Task-local flow

```text
SafeCommand (from safety gate 1021)
        │
        ├──> action is STOP? ──> snap to (0.0, 0.0), reset state
        │
        └──> CommandSmoother.step(dt) ──> rate-limited SafeCommand ──> /cmd_vel
```

### Contract

| Surface | Rule |
|---------|------|
| **Input** | `SafeCommand` with clamped target velocities and discrete action |
| **Output** | `SafeCommand` with smoothed `(linear_x, angular_z)`; action/events preserved |
| **STOP bypass** | `DiscreteAction.STOP` (including parse-failure STOP) skips smoothing |
| **Rate limits** | Config `smoothing.max_linear_rate` / `smoothing.max_angular_rate` (units: per second) |
| **Disabled** | When `smoothing.enabled: false`, target passes through unchanged |

### Trade-offs

- **Rate limiter vs. moving average** — discrete MVP targets jump between fixed velocities; averaging would blend incompatible commands. A slew limiter retargets cleanly when inference flips actions mid-ramp.
- **After safety gate** — smoothing limits *rate of change*; safety still owns absolute bounds. Smoothed values cannot exceed the target the gate already approved.
- **dt-based stepping** — works at any heartbeat rate; tune rates in m/s² and rad/s² rather than per-tick magic numbers.

## Learning notes

### Subtask 10254 — Control-rate decoupling and slew limiting

**Why smooth?** VLA inference at ~5 Hz produces step changes in velocity. The diff-drive controller and Webots sim expect continuous commands. Without smoothing, each new token snaps wheel speeds instantly.

**Key concepts:**

- **Slew rate** — maximum change in velocity per second. `max_delta = rate * dt` per control tick.
- **Setpoint tracking** — each inference step sets a new target; the smoother approaches it incrementally.
- **Decoupled loops** — high-rate heartbeat (10–100 Hz) interpolates low-rate model outputs (~5 Hz).

Default rates (`0.5` m/s² linear, `1.5` rad/s² angular) reach MVP nominal speeds (0.2 m/s, 0.6 rad/s) from rest in ~400 ms.

### Subtask 10255 — STOP bypass and fail-safe timing

**Why bypass STOP?** A ramp-down on emergency stop adds lag before the robot halts. Parse failures already map to `STOP` at the safety gate — smoothing must not re-introduce motion.

**Key concepts:**

- **Immediate zero** — `STOP` resets smoother state and returns `(0.0, 0.0)` on the same tick.
- **Action label vs. velocity** — bypass checks the discrete action, not whether velocities happen to be zero (e.g. `SLOW_DOWN` is not a bypass).
- **Timeout STOP** — ROS heartbeat also resets the smoother on action/camera timeout before publishing zero.

## Implementation breakdown

### Strategy (Subtask 10066)

**Decision:** per-axis slew-rate limiter toward the latest safe target.

**Alternatives rejected:**

| Approach | Why not |
|----------|---------|
| Moving average / EMA | Blends incompatible discrete commands; STOP becomes asymptotic |
| Fixed-duration lerp | Restarts on every inference step; still needs STOP special case |

### Rate limiter (Subtask 10067)

**Snippet** (`litevla/actions/smoothing.py`):

```python
def step_toward(current: float, target: float, max_delta: float) -> float:
    delta = target - current
    if abs(delta) <= max_delta:
        return target
    return current + math.copysign(max_delta, delta)
```

**Design notes:** pure helper for unit tests; independent linear and angular axes.

**Risks:** `dt <= 0` falls through to passthrough; NaN inputs are not sanitized (same as schema/safety).

### STOP bypass (Subtask 10068)

```python
if is_stop_bypass(target.action):
    self.reset()
    return target
```

**Design notes:** bypass uses action enum, not velocity magnitude. Covers explicit `STOP` and parse-failure `STOP` from `safe_command_from_text`.

### Integration

- **`scripts/run_dummy_pipeline.py`** — prints a smoothing ramp demo using config `smoothing` and `runtime.heartbeat_hz`.
- **`ros_ws/.../heartbeat_controller.py`** — owns a `CommandSmoother`; applies it each timer tick before `CmdVelPublisher`.
- **Config** — `smoothing` section in `configs/default.example.yaml` and `litevla/config/schema.json`.

## Engineering decisions

**ADR: Per-axis slew-rate limiter**

- **Status:** Accepted (Story 1022)
- **Context:** RSK-05 — jerk between ~5 Hz VLA outputs and 10–100 Hz actuation.
- **Decision:** Stateful `CommandSmoother` with configurable per-second rates and STOP bypass.
- **Alternatives rejected:** moving average (wrong for discrete jumps), fixed lerp (restart complexity).
- **Consequences:** tune `max_*_rate` and `heartbeat_hz` together in sim; Story 1053 wires model path through the same smoother.

## Verification patterns

```bash
pytest tests/test_action_smoothing.py -q
python scripts/run_dummy_pipeline.py
```

Contracts defended:

- max delta per tick respects `rate * dt`
- ramp reaches nominal target after sufficient steps
- `STOP` and parse-failure STOP are immediate (no residual velocity)
- disabled smoothing passes targets through
- mid-ramp retargeting follows new setpoint

## Open questions

- Raise default `heartbeat_hz` to 25–50 Hz when smoothing is enabled in sim launches?
- Expose smoother diagnostics (current vs. target) on `/litevla/diagnostics`?
- Continuous JSON velocity path (Story 1020) — same smoother applies to numeric targets.
