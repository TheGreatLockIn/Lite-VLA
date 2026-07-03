# Safety clamp and fallback behavior

**Epic:** Action Interface, Parser, and Safety Layer (103) · **Jira:** Story 1021

**Human-readable version (browser):** [`safety-clamp-and-fallback.html`](safety-clamp-and-fallback.html)

## Executive summary

`litevla.actions.safety` is the **fail-safe boundary** between VLA model text and ROS `/cmd_vel` publishing. It composes the discrete parser (Story 1019) and velocity mapper (Story 1017), clamps every command to configured limits, converts parse failures into zero-velocity `STOP`, and logs safety events with the original model output.

Subtasks covered: **10063** (velocity clamp), **10064** (invalid-output STOP), **10065** (safety event logging), **10252** and **10253** (learning).

## Mental model

Think of this module as the **airport security checkpoint** between “what the model said” and “what the wheels are allowed to do.”

It exists because no upstream module — not the VLM, not the parser, not the schema mapper — should be trusted to always produce safe, bounded motion. Something must guarantee that every path to `/cmd_vel` ends in a clamped velocity or zero.

The key engineering tension is **fail-fast in development vs. fail-safe at runtime** — schema raises on bad tokens for test clarity, but ROS nodes must never crash or publish unbounded values when the model hallucinates prose.

A beginner mistake is calling `action_to_twist` directly on raw model output in a ROS node, bypassing parse-failure handling and structured event logging.

A senior engineer watches for **dual clamp paths** — `action_to_twist` already clamps, but `clamp_twist_velocities` exists for future continuous/JSON velocity inputs; know which entry point your code path uses.

## Backstory: why this exists

Before this module existed, parse failures might propagate as exceptions or silent no-ops, and velocity limits lived only in the nominal action table without a single publish-time gate.

The naive solution would be `try/except` around `action_to_twist` in every ROS node, or embedding `STOP` logic inside the parser.

That breaks because exception handling duplicates across nodes, logs are inconsistent, and “parser returned stop” becomes indistinguishable from “model said STOP.” Operational review needs structured events with `original_text`.

So this design chooses **`safe_command_from_text` / `safe_command_from_action`** as the single fail-safe composer: parse → map → clamp → log → always return `SafeCommand`.

This pattern appears in real systems as **safety interlocks** — industrial controllers, avionics command validators, and game netcode servers all convert invalid input to safe default output at the last responsible layer.

## Prerequisites

Before reading this module, you should understand:

- **Parser contract** — [`discrete-action-parser.md`](discrete-action-parser.md): returns `None` on failure.
- **Schema mapping** — [`action-schema.md`](action-schema.md): `action_to_twist` and `clamp_velocity`.
- **ROS publishing** — `/cmd_vel` carries `Twist` messages; this module outputs floats, not ROS types.
- **Config `safety` section** — `max_linear_vel` / `max_angular_vel` in `configs/default.example.yaml`.
- **Optional downstream** — [`command-smoothing.md`](command-smoothing.md) rate-limits after the safety gate.

## Concept primer / vocabulary

| Term | Meaning in this project |
|------|-------------------------|
| `SafeCommand` | Bounded velocity + effective `DiscreteAction` + event trail; ready for smoother or `/cmd_vel`. |
| `SafetyEvent` | Structured record: kind, message, optional `original_text`. |
| `SafetyEventKind` | `ok`, `parse_failure`, or `velocity_clamped`. |
| `safe_command_from_text` | Main ROS entry: raw VLA string → always returns `SafeCommand`. |
| `safe_command_from_action` | Known discrete action → clamped `SafeCommand` with events. |
| `clamp_twist_velocities` | Standalone axis clamp returning `was_clamped` flag. |
| Parse failure fallback | `None` from parser → `(0.0, 0.0)` with `DiscreteAction.STOP`. |
| Fail-report vs. fail-safe | Parser reports failure; safety gate enforces safe motion. |

## Guided code reading

Read these in order:

1. **`litevla/actions/safety.py`** — dataclasses `SafeCommand`, `SafetyEvent`, `SafetyEventKind`.
2. **`clamp_twist_velocities`** — reusable primitive for non-discrete paths.
3. **`safe_command_from_action`** — nominal vs. clamped comparison and event emission.
4. **`safe_command_from_text`** — parse failure branch (the fail-safe heart).
5. **`tests/test_action_safety.py`** — especially invalid-text → STOP and logging tests.

While reading, ask:

- Where does data enter? — Raw VLA `text` or known `DiscreteAction`.
- Where is it validated? — `parse_discrete_action`; `DiscreteAction` coercion in `safe_command_from_action`.
- Where can it fail? — Never raises to caller; parse failure becomes zero-velocity STOP.
- Who owns the final side effect? — Still not this module — it returns `SafeCommand`; ROS node publishes `Twist`.

## File and artifact index

| File or artifact | What it is | Why it matters | First thing to inspect |
|------------------|------------|----------------|------------------------|
| `litevla/actions/safety.py` | Fail-safe gate implementation | Last software layer before motion | `safe_command_from_text` |
| `litevla/actions/parser.py` | Upstream parser | Called for every text input | `parse_discrete_action` |
| `litevla/actions/schema.py` | Velocity mapping + `clamp_velocity` | Used inside `safe_command_from_action` | `action_to_twist` |
| `tests/test_action_safety.py` | Safety contract tests | STOP fallback, clamp events, logging | `test_safe_command_from_text_invalid_outputs_stop` |
| `scripts/run_dummy_pipeline.py` | Integration demo | Shows valid + invalid text paths | Invalid text fallback section |

## API contract and data flow

### What “contract” means here

For this module, **contract** means: **every call returns a `SafeCommand`** with velocities clamped to configured limits. Raw model text that does not parse always becomes zero velocity with `DiscreteAction.STOP` and a `PARSE_FAILURE` event. The module never raises to the caller — this is the fail-safe publish boundary.

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

### Contract table

| Surface | Rule |
|---------|------|
| **Input** | Raw VLA text string, or a known `DiscreteAction` |
| **Output** | `SafeCommand` with clamped `(linear_x, angular_z)`, effective action, and `SafetyEvent` trail |
| **Parse failure** | Publishes `STOP` at `(0.0, 0.0)` — never raises to caller |
| **Velocity limits** | From config `safety.max_linear_vel` / `safety.max_angular_vel` (MVP design points: 0.2 m/s, 0.6 rad/s) |
| **Logging** | WARNING on parse failure and clamp; DEBUG on OK |

### Naive approach vs chosen approach

| Approach | Why it seems attractive | Why we did or did not choose it |
|----------|-------------------------|---------------------------------|
| `STOP` inside parser | One function call always succeeds | Blurs parse failure vs. explicit stop; loses event semantics |
| try/except at every ROS node | Local control | Duplicated policy; inconsistent logs |
| Raise on parse failure | Surfaces bugs immediately | Crashes or stalls ROS nodes on bad model output |
| **Central `safe_command_from_text`** | Extra indirection | Single fail-safe owner; structured events; testable |
| Structured events + logging | More types to maintain | Enables metrics, post-incident review, caplog tests |
| Discrete-only MVP path | Defers JSON velocities | Clear extension point via `clamp_twist_velocities` |

### Trade-offs

- **Discrete-only MVP path** — this module accepts VLA text and maps through `parse_discrete_action`. JSON velocity parsing (Stories 1018/1020) can extend the gate later without changing the fail-safe contract.
- **Structured events + logging** — `SafeCommand.events` supports tests and offline metrics; `logging` supports live ROS nodes.
- **Fail-safe at publish boundary** — parser reports `None`; schema raises on bad tokens; safety gate always returns a bounded command.

### Learning context (RSK-04, RSK-02)

**Velocity clamping:** per-axis `clamp_velocity` maps values into `[-limit, limit]` while preserving sign. Nominal `ACTION_VELOCITIES` may exceed deploy config; `VELOCITY_CLAMPED` events record when that happens.

**Fail-safe fallback:** conversational VLM output (RSK-02) must become zero velocity. `SafetyEventKind.PARSE_FAILURE` carries `original_text` for review. ROS nodes should call `safe_command_from_text`, not `action_to_twist` on unvalidated output.

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

**What to notice:** Returns a `was_clamped` boolean for event emission and metrics.

**Why it is written this way:** Reuses `clamp_velocity` from Story 1017. Exposed as a standalone helper for future continuous/JSON paths.

**Risks and gotchas:** Does not validate NaN/Inf inputs (same as schema). Discrete path uses `action_to_twist` which already clamps — know which path you are on.

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

**What to notice:** Never raises — every code path returns `SafeCommand`. Effective action is `STOP` on parse failure.

**Why it is written this way:** Concentrates fail-safe policy in one module; downstream always gets a bounded command.

**Risks and gotchas:** Multi-token strings where the first token is valid still execute that token (parser behavior). Hardware e-stop integration is deferred to ROS runtime nodes.

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

**What to notice:** OK events are DEBUG; failures and clamps are WARNING with quoted `original_text`.

**Why it is written this way:** `SafeCommand.events` preserves structured history for tests; logging supports live nodes without log capture in unit tests.

**Risks and gotchas:** High-frequency invalid outputs could flood WARNING logs during bad model runs — Story 1027 may add rate-limited counters.

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

**What to notice:** Safety types are first-class public exports.

**Why it is written this way:** ROS nodes import from `litevla.actions` only.

**Risks and gotchas:** Bypassing this module for model text breaks the fail-safe contract.

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

## Failure modes and debugging path

| Symptom | Likely cause | How to investigate | Fix |
|---------|--------------|--------------------|-----|
| Robot stops despite plausible model output | Parse failure → STOP fallback | Check WARNING logs for `original_text` | Fix prompt/token format; see parser doc |
| WARNING flood during eval | High parse-failure rate | Count `PARSE_FAILURE` events in metrics | Improve model/prompt; rate-limit logs (open question) |
| Velocity lower than nominal | Config clamp below design point | Look for `VELOCITY_CLAMPED` event | Adjust `safety.max_*` or accept deploy limit |
| `SafeCommand` OK but no motion | Downstream smoother or ROS node | Trace past safety gate | See [`command-smoothing.md`](command-smoothing.md) |
| Tests expect exception but get STOP | Called safety gate, not schema | Identify call path | Use `action_to_twist` only in tests with valid tokens |

## Engineering principle taught by this task

This task teaches the **fail-safe boundary** pattern: upstream modules may fail-fast or report `None` for clarity in tests, but the last software layer before physical actuation must never leave the robot in an undefined state. Convert unknown input into known-safe output, log what happened, and preserve structured evidence for operators.

## Active learning checks

Before modifying this module, answer:

1. Why does `safe_command_from_text` never raise, while `action_to_twist` can raise `ValueError`?
2. What is the difference between `PARSE_FAILURE` and an explicit model output of `STOP`?
3. Why does `safe_command_from_action` emit `VELOCITY_CLAMPED` when nominal values exceed config?
4. How would you test that invalid model text produces zero velocity without starting ROS?

## Small modification exercise

Lower `safety.max_linear_vel` to `0.1` in a local config copy and call `safe_command_from_action(DiscreteAction.MOVE_FORWARD, max_linear_vel=0.1, max_angular_vel=0.6)`. Verify `command.linear_x == 0.1` and that `command.events[0].kind` is `SafetyEventKind.VELOCITY_CLAMPED`. Run `pytest tests/test_action_safety.py -q`.

## Open questions

- Should JSON velocities (Story 1020) enter through `clamp_twist_velocities` only, or a parallel `safe_command_from_json`?
- Should repeated parse failures trigger a latched e-stop flag in the ROS node?
- Rate-limit safety WARNING logs during baseline evaluation (Story 1027)?

## Related docs

- Vocabulary contract: [`action-schema.md`](action-schema.md)
- Parser (upstream): [`discrete-action-parser.md`](discrete-action-parser.md)
- Command smoothing (downstream): [`command-smoothing.md`](command-smoothing.md)
- Epic walkthrough: [`index.html`](index.html)
