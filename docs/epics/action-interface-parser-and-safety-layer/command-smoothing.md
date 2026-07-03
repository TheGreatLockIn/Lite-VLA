# Command smoothing

**Epic:** Action Interface, Parser, and Safety Layer (103) · **Jira:** Story 1022

**Human-readable version (browser):** [`command-smoothing.html`](command-smoothing.html)

## Executive summary

`litevla.actions.smoothing` is the **rate-limiting layer** between the safety gate (Story 1021) and ROS `/cmd_vel` publishing. It reduces jerky velocity changes when VLA inference updates at ~5 Hz while the low-level heartbeat runs at 10–100 Hz (RSK-05). The MVP uses a **per-axis slew-rate limiter** with an immediate **STOP bypass** so emergency and parse-failure stops are never delayed.

Subtasks covered: **10066** (strategy), **10067** (rate limiter), **10068** (STOP bypass), **10254** and **10255** (learning).

## Mental model

Think of this module as a **shock absorber** between discrete model decisions and continuous wheel commands.

It exists because the VLA updates intent slowly (~5 Hz) while the robot control loop runs fast (10–100 Hz). Without interpolation, each new token would snap wheel speeds instantly, causing jerk that simulators, real drivetrains, and operators experience as unstable motion.

The key engineering tension is **smooth motion vs. immediate stop** — ramping is desirable for `MOVE_FORWARD` → `TURN_LEFT` transitions, but catastrophic for `STOP` and parse-failure fallbacks.

A beginner mistake is placing smoothing **before** the safety gate, which could rate-limit an unsafe raw velocity before clamping, or delaying zero-velocity stops.

A senior engineer watches for **`dt` and `heartbeat_hz` coupling** — slew limits are per-second; wrong `dt` makes ramps too fast or too slow.

## Backstory: why this exists

Before this module existed, safe commands from the gate went directly to `/cmd_vel` at heartbeat rate, repeating the same target until the next inference step — but each new inference step still caused a step change in target velocity.

The naive solution would be a moving average or exponential smoothing over recent commands.

That breaks because discrete MVP actions jump between incompatible setpoints (`MOVE_FORWARD` vs. `STOP`). Averaging blends incompatible intents and makes `STOP` asymptotic instead of immediate.

So this design chooses a **stateful per-axis slew-rate limiter** toward the latest safe target, with an explicit **STOP bypass** that resets state and passes zero immediately.

This pattern appears in real systems as **slew rate limiting** in motor controllers, audio parameter smoothing, and animation retargeting — always with an emergency bypass.

## Prerequisites

Before reading this module, you should understand:

- **`SafeCommand`** — output of [`safety-clamp-and-fallback.md`](safety-clamp-and-fallback.md); smoothing input type.
- **`DiscreteAction.STOP`** — bypass trigger, including parse-failure stops from safety gate.
- **Control loop timing** — `runtime.heartbeat_hz` in config; `dt = 1 / hz` per tick.
- **RSK-05** — jerk between inference rate and actuation rate (see epic walkthrough).

## Concept primer / vocabulary

| Term | Meaning in this project |
|------|-------------------------|
| `CommandSmoother` | Stateful per-axis rate limiter; holds current `linear_x` / `angular_z`. |
| `SmoothingConfig` | `enabled`, `max_linear_rate`, `max_angular_rate` (per second). |
| `step_toward` | Pure helper: move current toward target by at most `max_delta`. |
| Slew rate | Max velocity change per second; `max_delta = rate * dt` per tick. |
| STOP bypass | `DiscreteAction.STOP` skips smoothing; resets state to zero immediately. |
| Setpoint tracking | Each inference updates target; smoother approaches incrementally. |
| `step_velocities` | ROS convenience wrapper when node tracks twist + action separately. |

## Guided code reading

Read these in order:

1. **`litevla/actions/smoothing.py`** — `step_toward` and `is_stop_bypass` (pure logic).
2. **`SmoothingConfig` / `smoothing_config_from_mapping`** — config wiring.
3. **`CommandSmoother.step`** — STOP branch, disabled branch, rate-limited branch.
4. **`tests/test_action_smoothing.py`** — ramp, bypass, retargeting, disabled mode.

While reading, ask:

- Where does data enter? — `SafeCommand` target each heartbeat tick.
- Where is it validated? — Assumes upstream safety gate already clamped; no re-clamp here.
- Where can it fail? — NaN/`dt <= 0` edge cases passthrough; not sanitized.
- Who owns the final side effect? — ROS heartbeat publishes smoothed values to `/cmd_vel`.

## File and artifact index

| File or artifact | What it is | Why it matters | First thing to inspect |
|------------------|------------|----------------|------------------------|
| `litevla/actions/smoothing.py` | Rate limiter implementation | Jerk reduction between gate and ROS | `CommandSmoother.step` |
| `litevla/actions/safety.py` | Upstream `SafeCommand` producer | Smoother never re-parses model text | `SafeCommand` dataclass |
| `tests/test_action_smoothing.py` | Smoothing contracts | STOP bypass, ramp math, retargeting | `test_stop_bypass_is_immediate` |
| `configs/default.example.yaml` | `smoothing` section | Default rates and `enabled` flag | `max_linear_rate`, `max_angular_rate` |
| `ros_ws/.../heartbeat_controller.py` | Runtime integration | Owns `CommandSmoother` instance | Timer tick + `step` call |
| `scripts/run_dummy_pipeline.py` | Ramp demo | Visualize smoothing without ROS | Smoothing demo section |

## API contract and data flow

### What “contract” means here

For this module, **contract** means: given a **safe** target `SafeCommand` and elapsed `dt`, return a `SafeCommand` whose velocities move toward the target at most `max_*_rate * dt` per axis per tick — except when the target action is `STOP`, in which case output is immediate zero with no ramp. Smoothed values never exceed the safe target the gate already approved.

### Task-local flow

```text
SafeCommand (from safety gate 1021)
        │
        ├──> action is STOP? ──> snap to (0.0, 0.0), reset state
        │
        └──> CommandSmoother.step(dt) ──> rate-limited SafeCommand ──> /cmd_vel
```

### Contract table

| Surface | Rule |
|---------|------|
| **Input** | `SafeCommand` with clamped target velocities and discrete action |
| **Output** | `SafeCommand` with smoothed `(linear_x, angular_z)`; action/events preserved |
| **STOP bypass** | `DiscreteAction.STOP` (including parse-failure STOP) skips smoothing |
| **Rate limits** | Config `smoothing.max_linear_rate` / `smoothing.max_angular_rate` (units: per second) |
| **Disabled** | When `smoothing.enabled: false`, target passes through unchanged |

### Naive approach vs chosen approach

| Approach | Why it seems attractive | Why we did or did not choose it |
|----------|-------------------------|---------------------------------|
| Moving average / EMA | Simple one-liner smooth | Blends incompatible discrete commands; STOP becomes gradual |
| Fixed-duration lerp | Predictable ramp time | Restarts every inference step; still needs STOP special case |
| Smooth before safety gate | Earlier filtering | Could delay or distort clamping; unsafe targets get interpolated |
| **Per-axis slew limiter** | Slightly more state | Clean retargeting; independent linear/angular; testable `step_toward` |
| STOP bypass on action enum | Special case | Guarantees fail-safe timing; works for parse-failure STOP |
| After safety gate | Extra latency stage | Rate limits change only; absolute bounds already enforced upstream |

### Trade-offs

- **Rate limiter vs. moving average** — discrete MVP targets jump between fixed velocities; averaging would blend incompatible commands. A slew limiter retargets cleanly when inference flips actions mid-ramp.
- **After safety gate** — smoothing limits *rate of change*; safety still owns absolute bounds. Smoothed values cannot exceed the target the gate already approved.
- **dt-based stepping** — works at any heartbeat rate; tune rates in m/s² and rad/s² rather than per-tick magic numbers.

### Learning context (RSK-05)

Default rates (`0.5` m/s² linear, `1.5` rad/s² angular) reach MVP nominal speeds (0.2 m/s, 0.6 rad/s) from rest in ~400 ms. STOP bypass ensures parse-failure and explicit stops publish zero on the same tick — smoothing must not re-introduce motion after the safety gate says stop.

## Implementation breakdown

### Strategy (Subtask 10066)

**Decision:** per-axis slew-rate limiter toward the latest safe target.

**What to notice:** Rejected moving average and fixed lerp explicitly in ADR.

**Why it is written this way:** Discrete command jumps need setpoint tracking, not blending.

**Risks and gotchas:** Tuning must account for `heartbeat_hz` and inference rate together.

---

### Rate limiter (Subtask 10067)

**Snippet** (`litevla/actions/smoothing.py`):

```python
def step_toward(current: float, target: float, max_delta: float) -> float:
    delta = target - current
    if abs(delta) <= max_delta:
        return target
    return current + math.copysign(max_delta, delta)
```

**What to notice:** Pure function; `max_delta <= 0` returns target immediately.

**Why it is written this way:** Testable independent of stateful smoother; separate linear and angular axes.

**Risks and gotchas:** `dt <= 0` in `CommandSmoother.step` passthroughs to target; NaN inputs not sanitized (same as schema/safety).

---

### STOP bypass (Subtask 10068)

```python
if is_stop_bypass(target.action):
    self.reset()
    return target
```

**What to notice:** Bypass checks **action enum**, not velocity magnitude — `SLOW_DOWN` at low speed is not a bypass.

**Why it is written this way:** Parse-failure STOP from `safe_command_from_text` must not ramp down.

**Risks and gotchas:** ROS heartbeat should also reset smoother on action/camera timeout before publishing zero.

---

### Integration

- **`scripts/run_dummy_pipeline.py`** — prints a smoothing ramp demo using config `smoothing` and `runtime.heartbeat_hz`.
- **`ros_ws/.../heartbeat_controller.py`** — owns a `CommandSmoother`; applies it each timer tick before `CmdVelPublisher`.
- **Config** — `smoothing` section in `configs/default.example.yaml` and `litevla/config/schema.json`.

**What to notice:** Smoother sits **after** safety gate in the pipeline.

**Why it is written this way:** Absolute limits are already enforced; smoothing only shapes how fast you approach the safe target.

**Risks and gotchas:** Story 1053 must wire model path through the same smoother for consistent behavior.

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

## Failure modes and debugging path

| Symptom | Likely cause | How to investigate | Fix |
|---------|--------------|--------------------|-----|
| Robot sluggish to start moving | Slew rates too low for `dt` | Print `max_*_rate`, `heartbeat_hz`, compute `rate * dt` | Raise rates or heartbeat |
| Jerky motion despite smoothing | Smoothing disabled or bypassed | Check `smoothing.enabled` in config | Enable smoothing |
| Delayed stop | STOP not reaching smoother as `DiscreteAction.STOP` | Trace `SafeCommand.action` from safety gate | Fix upstream; verify `is_stop_bypass` |
| Overshoot never reaches target | `dt` too small or rate too low | Run `test_rate_limiter_reaches_target_after_enough_steps` | Tune rates / hz together |
| Sim OK, hardware jerky | Heartbeat vs. inference mismatch | Compare sim `heartbeat_hz` to deployment | Align config across environments |

## Engineering principle taught by this task

This task teaches **rate decoupling**: producers and consumers often run at different frequencies. Insert a stateful adapter that respects the fast loop’s `dt`, preserves emergency bypass semantics, and never weakens upstream safety bounds — only the *trajectory* toward those bounds.

## Active learning checks

Before modifying this module, answer:

1. Why is smoothing placed after the safety gate, not before?
2. Why does STOP bypass check `target.action` instead of whether velocities are near zero?
3. What happens to smoother state when a new inference target arrives mid-ramp?
4. How would you test that parse-failure STOP produces zero velocity on the first tick after smoothing?

## Small modification exercise

Set `smoothing.max_linear_rate` to `0.25` in config (half the default) and run `python scripts/run_dummy_pipeline.py`. Observe the printed ramp takes roughly twice as long to reach 0.2 m/s. Confirm with `pytest tests/test_action_smoothing.py -q` that STOP bypass tests still pass unchanged.

## Open questions

- Raise default `heartbeat_hz` to 25–50 Hz when smoothing is enabled in sim launches?
- Expose smoother diagnostics (current vs. target) on `/litevla/diagnostics`?
- Continuous JSON velocity path (Story 1020) — same smoother applies to numeric targets.

## Related docs

- Safety gate (upstream): [`safety-clamp-and-fallback.md`](safety-clamp-and-fallback.md)
- Action schema: [`action-schema.md`](action-schema.md)
- Epic walkthrough: [`index.html`](index.html)
