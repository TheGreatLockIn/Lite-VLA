# Discrete action schema

**Epic:** Action Interface, Parser, and Safety Layer (103) · **Jira:** VLA-29 / Story 1017

**Human-readable version (browser):** [`action-schema.html`](action-schema.html)

## Executive summary

`litevla.actions` owns the **discrete action contract** for the MVP: five exact uppercase tokens and their nominal velocity meanings. Parser, dataset labeling, prompts, safety gate, and ROS publishers must not invent parallel vocabularies or ad-hoc speed tables.

This module answers one bounded question: **given a valid action token, what `(linear_x, angular_z)` should downstream code request?** It does not parse noisy VLA text (Story 1019) and does not publish safe `STOP` fallbacks on failure (Story 1021). Those boundaries are intentional.

## API contract and data flow

### Task-local flow

```text
DiscreteAction | exact str token
        │
        ├──> ACTION_VELOCITIES lookup (nominal m/s, rad/s)
        │
        ├──> clamp_velocity per axis (config safety limits)
        │
        └──> (linear_x, angular_z)  ──> parser / safety / ROS consumers
```

### Contract

| Surface | Rule |
|---------|------|
| **Input** | `DiscreteAction` or exact string matching an enum value |
| **Config** | `max_linear_vel`, `max_angular_vel` from `safety` section (SI units) |
| **Output** | `(linear_x, angular_z)` floats for `Twist.linear.x` / `Twist.angular.z` |
| **Invariant** | Every enum member has exactly one nominal velocity pair |
| **Validation** | `is_valid_action(name)` — exact token only; no aliases |
| **Error behavior** | Unknown strings in `action_to_twist` raise `ValueError` (fail-fast here; safety gate will fail-safe later) |

### Vocabulary

| Action | Meaning | Nominal `linear_x` (m/s) | Nominal `angular_z` (rad/s) |
|--------|---------|--------------------------|-----------------------------|
| `MOVE_FORWARD` | Drive toward the goal | 0.2 | 0.0 |
| `TURN_LEFT` | Rotate left in place | 0.0 | 0.6 |
| `TURN_RIGHT` | Rotate right in place | 0.0 | −0.6 |
| `SLOW_DOWN` | Reduce forward speed near target | 0.1 | 0.0 |
| `STOP` | Halt immediately | 0.0 | 0.0 |

### Trade-offs

- **`str, Enum` over plain strings** — tokens stay serializable and comparable while giving type-checked call sites. Parser may still emit strings; coercion happens at the mapping boundary.
- **Nominal table + config clamp** — motion meaning (`ACTION_VELOCITIES`) stays stable for labeling and training; deployment limits (`safety.max_*`) can tighten without relabeling data.
- **Strict tokens, no aliases** — rejects `FORWARD`/`GO` so parser tests and dataset QA stay deterministic.
- **Fail-fast mapping vs fail-safe publishing** — `action_to_twist` raises on bad input so tests catch mistakes early; Story 1021 owns converting failures to zero velocity at the ROS boundary.

## Implementation breakdown

### Vocabulary and nominal motion profile

**Snippet** (`litevla/actions/schema.py`):

```python
DEFAULT_LINEAR_FORWARD: Final[float] = 0.2  # m/s
DEFAULT_LINEAR_SLOW: Final[float] = 0.1  # m/s
DEFAULT_ANGULAR_TURN: Final[float] = 0.6  # rad/s

class DiscreteAction(str, Enum):
    MOVE_FORWARD = "MOVE_FORWARD"
    TURN_LEFT = "TURN_LEFT"
    TURN_RIGHT = "TURN_RIGHT"
    SLOW_DOWN = "SLOW_DOWN"
    STOP = "STOP"

ACTION_VELOCITIES: Final[dict[DiscreteAction, tuple[float, float]]] = {
    DiscreteAction.MOVE_FORWARD: (DEFAULT_LINEAR_FORWARD, 0.0),
    DiscreteAction.TURN_LEFT: (0.0, DEFAULT_ANGULAR_TURN),
    DiscreteAction.TURN_RIGHT: (0.0, -DEFAULT_ANGULAR_TURN),
    DiscreteAction.SLOW_DOWN: (DEFAULT_LINEAR_SLOW, 0.0),
    DiscreteAction.STOP: (0.0, 0.0),
}
```

**Design notes:** Design-point constants mirror [`docs/mvp_definition.md`](../../mvp_definition.md) so tests and docs reference one source of truth. `ACTION_NAMES` (derived from the enum) gives scripts a stable iteration order without duplicating the token list.

**Risks and gotchas:** Changing enum order or names is a **breaking contract change** for datasets, prompts, and parser tests. `TURN_RIGHT` uses negative angular velocity — consumers must not assume unsigned magnitudes.

---

### Validation and clamping primitives

**Snippet:**

```python
def is_valid_action(name: str) -> bool:
    try:
        DiscreteAction(name)
    except ValueError:
        return False
    return True

def clamp_velocity(value: float, limit: float) -> float:
    return max(-limit, min(limit, value))
```

**Design notes:** `is_valid_action` is a non-throwing probe for parser pre-checks. `clamp_velocity` is axis-local and sign-preserving — reused by Story 1021's safety gate.

**Risks and gotchas:** `is_valid_action` requires **exact** case and spelling; whitespace-normalization belongs in Story 1019, not here. `clamp_velocity` does not detect NaN/Inf inputs.

---

### Token-to-velocity mapping

**Snippet:**

```python
def action_to_twist(
    action: DiscreteAction | str,
    *,
    max_linear_vel: float,
    max_angular_vel: float,
) -> tuple[float, float]:
    if isinstance(action, str):
        action = DiscreteAction(action)

    linear, angular = ACTION_VELOCITIES[action]
    return (
        clamp_velocity(linear, max_linear_vel),
        clamp_velocity(angular, max_angular_vel),
    )
```

**Design notes:** Single runtime entry point for discrete-to-velocity conversion. Config limits are **required keyword arguments** so callers cannot accidentally bypass safety ceilings.

**Risks and gotchas:** Invalid strings raise `ValueError` — callers must not let that propagate to `/cmd_vel` without Story 1021's fallback. Accepting raw strings is a convenience for tests and dummy mode; parser may narrow the API later.

**Before/after** (why the shared contract matters):

```diff
- for action in ("FORWARD", "STOP"):
-     print(action)
+ for action in ACTION_NAMES:
+     linear, angular = action_to_twist(
+         action,
+         max_linear_vel=safety["max_linear_vel"],
+         max_angular_vel=safety["max_angular_vel"],
+     )
```

---

### Public API surface

**Snippet** (`litevla/actions/__init__.py`):

```python
from litevla.actions.schema import (
    ACTION_NAMES,
    DiscreteAction,
    action_to_twist,
    clamp_velocity,
    is_valid_action,
    # ...
)
```

**Design notes:** Application code imports `litevla.actions`, not `litevla.actions.schema`, so internal file layout can evolve without breaking ROS nodes or scripts.

**Risks and gotchas:** Anything added to `__all__` becomes a semver-sensitive public contract.

---

### Runtime integration (config-driven)

**Config** (`configs/default.example.yaml`):

```yaml
safety:
  max_linear_vel: 0.5
  max_angular_vel: 1.0
```

**Snippet** (`scripts/run_dummy_pipeline.py`):

```python
safety = config["safety"]
for action in ACTION_NAMES:
    linear, angular = action_to_twist(
        action,
        max_linear_vel=safety["max_linear_vel"],
        max_angular_vel=safety["max_angular_vel"],
    )
    print(f"action={action:13s}  linear={linear:.3f} m/s  angular={angular:.3f} rad/s")
```

**Design notes:** Dummy pipeline proves schema + config integration without ROS or model weights. Nominal 0.2 m/s forward may clamp down when config limits are lower than design points.

**Risks and gotchas:** Example config allows 0.5 m/s — higher than MVP operational target (0.2 m/s). Deployment configs must set limits appropriate to the robot; the schema does not enforce MVP caps by itself.

## Engineering decisions

```text
ADR: Five-token discrete vocabulary
Status: Accepted
Context: MVP defers continuous VLM velocity output; team needs a small, label-friendly action set.
Decision: MOVE_FORWARD, TURN_LEFT, TURN_RIGHT, SLOW_DOWN, STOP with nominal 0.2/0.1 m/s forward and ±0.6 rad/s turns.
Alternatives Rejected: FORWARD alias (ambiguous); JSON velocity schema as primary MVP path.
Consequences: Dataset labels and prompts must use exact tokens; parser validates before calling action_to_twist.
```

## Verification patterns

Tests and scripts defend specific behavioral contracts:

| Contract defended | Where |
|-------------------|-------|
| Token names uppercase, unique, stable order | `test_action_names_are_uppercase_and_unique` |
| Every action has a velocity mapping | `test_all_actions_have_velocity_mapping` |
| Nominal values match MVP design points | `test_nominal_velocities_match_mvp_design_points` |
| Mapping at MVP limits (0.2 / 0.6) | `test_action_to_twist_at_mvp_limits` |
| Config clamp when limits &lt; nominal | `test_action_to_twist_clamps_to_config_limits` |
| Aliases rejected (`FORWARD`) | `test_is_valid_action`, `test_invalid_action_string_raises` |
| End-to-end config integration | `scripts/run_dummy_pipeline.py` |

**Snippet** (clamping + fail-fast):

```python
def test_action_to_twist_clamps_to_config_limits() -> None:
    linear, angular = action_to_twist(
        DiscreteAction.MOVE_FORWARD,
        max_linear_vel=0.1,
        max_angular_vel=0.3,
    )
    assert linear == pytest.approx(0.1)
    assert angular == pytest.approx(0.0)

def test_invalid_action_string_raises() -> None:
    with pytest.raises(ValueError):
        action_to_twist("FORWARD", max_linear_vel=0.2, max_angular_vel=0.6)
```

**Run:**

```bash
pytest tests/test_action_schema.py -q
python scripts/run_dummy_pipeline.py
```

## Open questions

- Should `action_to_twist` accept only `DiscreteAction` once Story 1019 owns all string coercion?
- How will optional JSON velocities (Story 1018) merge with discrete tokens at the safety gate?

## Related docs

- Parser (noisy VLA text): [`discrete-action-parser.md`](discrete-action-parser.md)
- Epic walkthrough: [`index.html`](index.html)
- MVP acceptance criteria: [`../../mvp_definition.md`](../../mvp_definition.md)
- Architecture overview: [`../../architecture_summary.md`](../../architecture_summary.md)
