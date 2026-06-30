# Safety clamp and fallback behavior

**Epic:** Action Interface, Parser, and Safety Layer (103) · **Jira:** Story 1021

**Human-readable version (browser):** [`safety-clamp-and-fallback.html`](safety-clamp-and-fallback.html)

## Executive summary

`litevla.actions.safety` is the **fail-safe boundary** between VLA model text and ROS `/cmd_vel` publishing. It composes the discrete parser (Story 1019) and velocity mapper (Story 1017), clamps every command to configured limits, converts parse failures into zero-velocity `STOP`, and logs safety events with the original model output.

Subtasks covered: **10063** (velocity clamp), **10064** (invalid-output STOP), **10065** (safety event logging), **10252** and **10253** (learning).

## API contract and data flow

### Task-local flow

```text
VLA raw text
        │
        ├──> parse_discrete_action (1019) ──> DiscreteAction | None
        │
        ├──> None? ──> STOP (0.0, 0.0) + PARSE_FAILURE event
        │
        └──> action_to_twist (1017) ──> clamp check ──> SafeCommand
                                                    │
                                                    └──> /cmd_vel (1022 smoother optional)
```

### Contract

| Surface | Rule |
|---------|------|
| **Input** | Raw VLA text string, or a known `DiscreteAction` |
| **Output** | `SafeCommand` with clamped `(linear_x, angular_z)`, effective action, and `SafetyEvent` trail |
| **Parse failure** | Publishes `STOP` at `(0.0, 0.0)` — never raises to caller |
| **Velocity limits** | From config `safety.max_linear_vel` / `safety.max_angular_vel` (MVP design points: 0.2 m/s, 0.6 rad/s) |
| **Logging** | WARNING on parse failure and clamp; DEBUG on OK |

### Trade-offs

- **Discrete-only MVP path** — this module accepts VLA text and maps through `parse_discrete_action`. JSON velocity parsing (Stories 1018/1020) can extend the gate later without changing the fail-safe contract.
- **Structured events + logging** — `SafeCommand.events` supports tests and offline metrics; `logging` supports live ROS nodes.
- **Fail-safe at publish boundary** — parser reports `None`; schema raises on bad tokens; safety gate always returns a bounded command.

## Learning notes

### Subtask 10252 — Velocity clamping and operational limits

**Why clamp?** A VLA model might eventually emit continuous velocities or nominal discrete speeds could exceed deployment limits. Clamping guarantees the robot never receives a command above configured ceilings, even if upstream logic has a bug.

**Key concepts:**

- **Per-axis clamping** — linear and angular velocity are independent axes. `clamp_velocity(value, limit)` maps any value into `[-limit, limit]` while preserving sign.
- **Nominal vs. config limits** — `ACTION_VELOCITIES` defines training/demo semantics (e.g. `MOVE_FORWARD` → 0.2 m/s). Config `safety.max_*` can tighten limits at deploy time without retraining.
- **Detection vs. prevention** — `clamp_twist_velocities` returns a `was_clamped` flag; `safe_command_from_action` emits a `VELOCITY_CLAMPED` event when nominal values exceed config.

**MVP limits (RSK-04):** linear ≤ 0.2 m/s, angular ≤ 0.6 rad/s at full design point.

### Subtask 10253 — Fail-safe fallback and safety event logging

**Why fallback STOP?** VLMs can produce conversational text instead of action tokens (RSK-02). The safety gate is the last line of defense before physical motion — any unrecognized input must become zero velocity.

**Key concepts:**

- **Fail-report vs. fail-safe** — parser returns `None` (report); safety gate publishes `STOP` (safe act). This split keeps parser logic simple and concentrates policy in one module.
- **Safety events** — `SafetyEventKind` records `ok`, `parse_failure`, or `velocity_clamped`. Each event carries a human-readable message and optional `original_text` for post-incident review.
- **Logging levels** — failures and clamps log at WARNING with the original model string; successful commands log at DEBUG to avoid flooding production logs.

**ROS integration pattern:** ROS nodes should call `safe_command_from_text`, read `command.linear_x` / `command.angular_z`, and publish a `Twist`. They must not call `action_to_twist` directly on unvalidated model output.

## Implementation breakdown

### Velocity clamp (Subtask 10063)

**Snippet** (`litevla/actions/safety.py`):

```python
def clamp_twist_velocities(
    linear_x: float,
    angular_z: float,
    *,
    max_linear_vel: float,
    max_angular_vel: float,
) -> tuple[float, float, bool]:
    clamped_linear = clamp_velocity(linear_x, max_linear_vel)
    clamped_angular = clamp_velocity(angular_z, max_angular_vel)
    was_clamped = clamped_linear != linear_x or clamped_angular != angular_z
    return clamped_linear, clamped_angular, was_clamped
```

**Design notes:** Reuses `clamp_velocity` from Story 1017. Exposed as a standalone helper for future continuous/JSON paths and direct velocity clamping without discrete mapping.

**Risks and gotchas:** Does not validate NaN/Inf inputs (same as schema). Discrete path uses `action_to_twist` which already clamps — `clamp_twist_velocities` is the explicit reusable primitive.

---

### Invalid-output STOP (Subtask 10064)

**Snippet:**

```python
def safe_command_from_text(text: str, *, max_linear_vel: float, max_angular_vel: float, ...) -> SafeCommand:
    parsed = parse_discrete_action(text)
    if parsed is None:
        return SafeCommand(
            linear_x=0.0,
            angular_z=0.0,
            action=DiscreteAction.STOP,
            original_text=text,
            events=(SafetyEvent(kind=SafetyEventKind.PARSE_FAILURE, ...),),
        )
    return safe_command_from_action(parsed, ...)
```

**Design notes:** Never raises — every code path returns a `SafeCommand`. Effective action is always `DiscreteAction.STOP` on parse failure so downstream metrics can count fallback rate.

**Risks and gotchas:** Multi-token strings where the first token is valid still execute that token (parser behavior). Emergency-stop hardware integration is deferred to ROS runtime nodes.

---

### Safety event logging (Subtask 10065)

**Snippet:**

```python
def _log_event(event: SafetyEvent, *, logger: logging.Logger) -> None:
    if event.kind is SafetyEventKind.OK:
        logger.debug(event.message)
        return
    detail = event.message
    if event.original_text is not None:
        detail = f"{detail} (original_text={event.original_text!r})"
    logger.warning(detail)
```

**Design notes:** Callers may pass a module-specific logger (e.g. ROS node logger). `SafeCommand.events` preserves structured history for tests and experiment metrics without requiring log capture.

**Risks and gotchas:** High-frequency invalid outputs could flood WARNING logs during bad model runs — Story 1027 baseline eval may add rate-limited counters.

---

### Public API surface

**Snippet** (`litevla/actions/__init__.py`):

```python
from litevla.actions.safety import (
    SafeCommand,
    SafetyEvent,
    SafetyEventKind,
    clamp_twist_velocities,
    safe_command_from_action,
    safe_command_from_text,
)
```

**Integration:** `scripts/run_dummy_pipeline.py` uses `safe_command_from_action` for known tokens and demonstrates invalid-text fallback via `safe_command_from_text`.

## Engineering decisions

```text
ADR: Central safety gate for discrete MVP
Status: Accepted
Context: Parser (1019) reports failure; schema (1017) fail-fast on bad tokens; ROS needs fail-safe publishing (RSK-02, RSK-04).
Decision: safe_command_from_text / safe_command_from_action in litevla.actions.safety own clamp + STOP + logging.
Alternatives Rejected: STOP inside parser (blurs boundaries); try/except around action_to_twist at every call site.
Consequences: ROS and inference nodes should route all model text through the safety gate before /cmd_vel.
```

## Verification patterns

| Contract defended | Where |
|-------------------|-------|
| Axis clamp within/outside limits | `test_clamp_twist_velocities_*` |
| Valid text → correct action and velocity | `test_safe_command_from_text_valid_outputs` |
| Invalid text → STOP at zero velocity | `test_safe_command_from_text_invalid_outputs_stop` |
| Config limits clamp nominal speeds | `test_safe_command_from_action_clamps_to_config_limits` |
| Parse failure logged with original text | `test_safe_command_from_text_logs_parse_failure` |
| Clamp event logged | `test_safe_command_from_action_logs_clamp_event` |

**Run:**

```bash
pytest tests/test_action_safety.py -q
python scripts/run_dummy_pipeline.py
```

## Open questions

- Should JSON velocities (Story 1020) enter through `clamp_twist_velocities` only, or a parallel `safe_command_from_json`?
- Should repeated parse failures trigger a latched e-stop flag in the ROS node?
- Rate-limit safety WARNING logs during baseline evaluation (Story 1027)?

## Related docs

- Vocabulary contract: [`action-schema.md`](action-schema.md)
- Parser (upstream): [`discrete-action-parser.md`](discrete-action-parser.md)
- Epic walkthrough: [`index.html`](index.html)
