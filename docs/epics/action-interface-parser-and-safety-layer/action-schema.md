# Discrete action schema

**Epic:** Action Interface, Parser, and Safety Layer (103) · **Jira:** VLA-29 / Story 1017

**Human-readable version (browser):** [`action-schema.html`](action-schema.html)

## Executive summary

`litevla.actions.schema` owns the **discrete action contract** for the MVP: five exact uppercase tokens and their nominal velocity meanings. Parser, dataset labeling, prompts, safety gate, and ROS publishers must not invent parallel vocabularies or ad-hoc speed tables.

This module answers one bounded question: **given a valid action token, what `(linear_x, angular_z)` should downstream code request?** It does not parse noisy VLA text ([`discrete-action-parser.md`](discrete-action-parser.md)) and does not publish safe `STOP` fallbacks on failure ([`safety-clamp-and-fallback.md`](safety-clamp-and-fallback.md)). Those boundaries are intentional.

## Mental model

Think of this module as a **Rosetta stone** between what the VLA model is allowed to say and what the robot is allowed to do.

It exists because every layer above and below this file needs a single, stable vocabulary — training labels, prompt templates, parser tests, safety clamps, and `/cmd_vel` publishers must all agree on the same five tokens and what they mean in meters per second and radians per second.

The key engineering tension is **stable training semantics vs. deployment safety limits**: nominal speeds must stay fixed for reproducible datasets, but deployed robots may need tighter ceilings without relabeling data.

A beginner mistake is adding friendly aliases like `FORWARD` or `GO` “just for the model” — that silently breaks dataset QA, parser strictness, and test determinism.

A senior engineer watches for **contract drift**: any new token, renamed enum member, or changed nominal velocity is a breaking change across ML, data, and ROS.

## Backstory: why this exists

Before this module existed, the system had no shared definition of “what is a valid action” or “how fast should `MOVE_FORWARD` go.” Scripts, prompts, and future ROS nodes would each invent their own strings and speed tables.

The naive solution would be to let the VLA output free-form text and parse velocities directly from model prose, or to scatter `if action == "forward": speed = 0.2` checks across the codebase.

That breaks because training data, evaluation metrics, and runtime safety cannot stay aligned when every file owns a slightly different vocabulary. A model fine-tuned on `MOVE_FORWARD` will not match a node that accepts `FORWARD`, and nominal 0.2 m/s forward has no meaning if another module uses 0.15 m/s.

So this design chooses a **small `str, Enum` vocabulary**, a single `ACTION_VELOCITIES` lookup table, and a required `action_to_twist` entry point that applies config clamps before any command reaches the safety gate or ROS.

This pattern appears in real systems as **schema-first robotics APIs** — game engines use action enums, ROS navigation stacks use discrete cmd profiles, and ML pipelines use fixed label sets so train and deploy share one contract.

## Prerequisites

Before reading this module, you should understand:

- **Python enums** — `DiscreteAction` is a `str, Enum` so tokens serialize to JSON and compare as strings.
- **ROS `Twist` basics** — Lite-VLA maps actions to `linear.x` (forward m/s) and `angular.z` (yaw rad/s). See [`../../architecture_summary.md`](../../architecture_summary.md) for how `/cmd_vel` fits the stack.
- **MVP design points** — nominal speeds come from [`../../mvp_definition.md`](../../mvp_definition.md) (0.2 m/s forward, ±0.6 rad/s turns).
- **Epic pipeline order** — parser extracts tokens ([`discrete-action-parser.md`](discrete-action-parser.md)); this module maps valid tokens; safety gate fail-safes invalid input ([`safety-clamp-and-fallback.md`](safety-clamp-and-fallback.md)).

## Concept primer / vocabulary

| Term | Meaning in this project |
|------|-------------------------|
| `DiscreteAction` | Enum of the five allowed MVP action tokens; the type-safe handle for a valid label. |
| `ACTION_NAMES` | Tuple of token strings in enum order — used by parser regex and iteration scripts. |
| `ACTION_VELOCITIES` | Nominal `(linear_x, angular_z)` per action before config clamping; training/demo semantics. |
| `action_to_twist` | Single runtime mapper from token → clamped velocity pair; required `max_*` keyword args. |
| `clamp_velocity` | Axis-local sign-preserving clamp to `[-limit, limit]`; reused by safety gate. |
| `Twist` | ROS geometry message; Lite-VLA publishes `linear.x` and `angular.z` to `/cmd_vel`. |
| `safety.max_linear_vel` | Config ceiling (m/s) passed into `action_to_twist`; may be lower than nominal design points. |
| `safety.max_angular_vel` | Config ceiling (rad/s) for angular velocity clamping. |
| Nominal vs. config limit | Nominal = what the action *means* for labeling; config = what the robot *may receive* at deploy time. |

## Guided code reading

Read these in order:

1. **`litevla/actions/schema.py`**
   - Start with `DiscreteAction` and `ACTION_VELOCITIES` — this is the whole vocabulary contract.
   - Then read `is_valid_action`, `clamp_velocity`, and `action_to_twist`.
   - Ignore imports and module docstring on first pass.

2. **`litevla/actions/__init__.py`**
   - See which symbols are exported as the public API (`ACTION_NAMES`, `action_to_twist`, etc.).

3. **`tests/test_action_schema.py`**
   - Tests document the behavioral contracts better than comments — especially clamping and alias rejection.

4. **`configs/default.example.yaml`** (`safety` section)
   - See how deploy limits are configured separately from nominal table values.

While reading, ask:

- Where does data enter? — As `DiscreteAction` or exact string token at `action_to_twist`.
- Where is it validated? — `DiscreteAction(name)` inside `is_valid_action` / `action_to_twist`; invalid strings raise `ValueError`.
- Where can it fail? — Unknown token strings raise `ValueError` (fail-fast); callers must not let this reach `/cmd_vel` without the safety gate.
- Who owns the final side effect? — Not this module; it returns floats only. ROS publishing is downstream.

## File and artifact index

| File or artifact | What it is | Why it matters | First thing to inspect |
|------------------|------------|----------------|------------------------|
| `litevla/actions/schema.py` | Discrete vocabulary and velocity mapping | Single source of truth for tokens and nominal speeds | `DiscreteAction` enum and `ACTION_VELOCITIES` dict |
| `litevla/actions/__init__.py` | Public re-exports | Application code imports `litevla.actions`, not internal files | `__all__` list |
| `tests/test_action_schema.py` | Unit tests for schema contracts | Executable spec for clamping, aliases, MVP limits | `test_action_to_twist_clamps_to_config_limits` |
| `configs/default.example.yaml` | Example deploy config | Shows `safety.max_*` separate from nominal constants | `safety:` section |
| `scripts/run_dummy_pipeline.py` | Smoke script | End-to-end schema + config integration without ROS | Loop over `ACTION_NAMES` calling `action_to_twist` |
| `docs/mvp_definition.md` | MVP acceptance criteria | Authoritative design-point speeds | Linear/angular limits |

## API contract and data flow

### What “contract” means here

For this module, **contract** means the promise it makes to every caller: if you pass a known `DiscreteAction` (or its exact string value) plus required safety limits, you get back a `(linear_x, angular_z)` pair in SI units, already clamped to those limits. The contract does **not** promise to accept aliases, prose, or partial matches — that is the parser’s job. It does **not** promise fail-safe zero velocity on bad input — that is the safety gate’s job.

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

### Contract table

In the table below, **Surface** means “which part of the API you interact with,” and **Rule** means “what that surface guarantees.”

| Surface | Rule |
|---------|------|
| **Input** | `DiscreteAction` or exact string matching an enum value (e.g. `"MOVE_FORWARD"`) |
| **Config** | `max_linear_vel`, `max_angular_vel` from `safety` section (SI units: m/s, rad/s) |
| **Output** | `(linear_x, angular_z)` floats for `Twist.linear.x` / `Twist.angular.z` |
| **Invariant** | Every enum member has exactly one nominal velocity pair in `ACTION_VELOCITIES` |
| **Validation** | `is_valid_action(name)` — exact token only; no aliases |
| **Error behavior** | Unknown strings in `action_to_twist` raise `ValueError` (fail-fast here; safety gate fail-safes later) |

### Action vocabulary

| Action | Meaning | Nominal `linear_x` (m/s) | Nominal `angular_z` (rad/s) |
|--------|---------|--------------------------|-----------------------------|
| `MOVE_FORWARD` | Drive toward the goal | 0.2 | 0.0 |
| `TURN_LEFT` | Rotate left in place | 0.0 | 0.6 |
| `TURN_RIGHT` | Rotate right in place | 0.0 | −0.6 |
| `SLOW_DOWN` | Reduce forward speed near target | 0.1 | 0.0 |
| `STOP` | Halt immediately | 0.0 | 0.0 |

### Naive approach vs chosen approach

| Approach | Why it seems attractive | Why we did or did not choose it |
|----------|-------------------------|---------------------------------|
| Free-form model velocities in prose | Flexible; model can output any speed | Unparseable, untrainable, unsafe without heavy post-processing |
| Per-file `if/elif` speed tables | Quick to prototype | Drift across ML, ROS, and data tooling |
| Alias tokens (`FORWARD`, `GO`) | Friendlier model outputs | Breaks strict dataset labels and deterministic parser tests |
| **`str, Enum` + single lookup table** | Slightly more ceremony | One vocabulary for train, eval, and deploy; type-checked call sites |
| Nominal table + config clamp | Two layers of limits | Stable labeling semantics with deploy-time safety tightening |
| Fail-fast `ValueError` on bad tokens | Crashes on bad input | Catches bugs in tests; safety gate owns fail-safe at publish boundary |

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

**What to notice:** Design-point constants are named (`DEFAULT_LINEAR_FORWARD`) and referenced in both the enum table and tests. `TURN_RIGHT` uses **negative** angular velocity.

**Why it is written this way:** One source of truth mirrors [`docs/mvp_definition.md`](../../mvp_definition.md) so tests and docs reference the same numbers. `ACTION_NAMES` (derived from the enum) gives scripts a stable iteration order without duplicating the token list.

**Risks and gotchas:** Changing enum order or names is a **breaking contract change** for datasets, prompts, and parser tests. Consumers must not assume unsigned angular magnitudes.

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

**What to notice:** `is_valid_action` never raises — it is a probe for parser pre-checks. `clamp_velocity` is symmetric around zero.

**Why it is written this way:** Non-throwing validation keeps parser logic simple. Sign-preserving clamp is reused by the safety gate for both discrete and future continuous paths.

**Risks and gotchas:** `is_valid_action` requires **exact** case and spelling; whitespace normalization belongs in the parser, not here. `clamp_velocity` does not detect NaN/Inf inputs.

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

**What to notice:** Config limits are **required keyword arguments** — callers cannot accidentally omit safety ceilings.

**Why it is written this way:** Single runtime entry point for discrete-to-velocity conversion; forces every call site to pass deploy limits explicitly.

**Risks and gotchas:** Invalid strings raise `ValueError` — callers must not let that propagate to `/cmd_vel` without the safety gate. Accepting raw strings is a convenience for tests and dummy mode.

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

**What to notice:** Schema symbols are re-exported at package level.

**Why it is written this way:** Application code imports `litevla.actions`, not `litevla.actions.schema`, so internal file layout can evolve without breaking ROS nodes or scripts.

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

**What to notice:** Example config allows 0.5 m/s — higher than MVP operational target (0.2 m/s).

**Why it is written this way:** Dummy pipeline proves schema + config integration without ROS or model weights.

**Risks and gotchas:** Deployment configs must set limits appropriate to the robot; the schema does not enforce MVP caps by itself.

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
| Config clamp when limits < nominal | `test_action_to_twist_clamps_to_config_limits` |
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

## Failure modes and debugging path

| Symptom | Likely cause | How to investigate | Fix |
|---------|--------------|--------------------|-----|
| `ValueError` on `action_to_twist` | Alias or typo in token (`FORWARD`, lowercase) | Check string against `ACTION_NAMES`; run `is_valid_action` | Use exact enum value; route raw model text through parser + safety gate |
| Forward speed lower than expected | Config `max_linear_vel` below nominal 0.2 | Print `safety` config; compare to `ACTION_VELOCITIES` | Raise config limit or accept intentional deploy clamp |
| Turn direction inverted | Assuming positive angular always means left | Inspect `TURN_RIGHT` nominal (−0.6 rad/s) | Use `DiscreteAction` enum, not hand-rolled signs |
| Dataset labels rejected in training | Token not in `ACTION_NAMES` | Grep dataset for action field values | Relabel to exact five tokens |
| Tests pass but robot too fast | Example config allows 0.5 m/s linear | Read `configs/default.example.yaml` vs production `local.yaml` | Set deploy `safety.max_*` to robot-appropriate limits |

## Engineering principle taught by this task

This task teaches **schema-first bounded contracts**: define the smallest shared vocabulary and mapping table once, then let specialized modules (parser, safety, smoothing) own their adjacent concerns. Nominal semantics and deploy limits stay separate so training reproducibility does not fight operational safety.

## Active learning checks

Before modifying this module, answer:

1. Why does `action_to_twist` require `max_linear_vel` and `max_angular_vel` as keyword arguments instead of reading config internally?
2. What happens if you add a sixth action to the enum but forget to update `ACTION_VELOCITIES`?
3. Why does this module raise on invalid tokens while the safety gate returns `STOP` at zero velocity?
4. How would you verify that a config change tightens deploy limits without changing nominal training semantics?

## Small modification exercise

Change `DEFAULT_LINEAR_SLOW` from `0.1` to `0.05` in `litevla/actions/schema.py`, then verify:

1. `pytest tests/test_action_schema.py -q` — update `test_nominal_velocities_match_mvp_design_points` if MVP doc still mandates 0.1 (or revert if exercise is exploratory only).
2. `python scripts/run_dummy_pipeline.py` — confirm `SLOW_DOWN` prints `linear=0.050` (or clamped value if config is lower).
3. Grep the repo for `0.1` slow references in docs/tests to see blast radius of a nominal change.

## Open questions

- Should `action_to_twist` accept only `DiscreteAction` once Story 1019 owns all string coercion?
- How will optional JSON velocities (Story 1018) merge with discrete tokens at the safety gate?

## Related docs

- Parser (noisy VLA text): [`discrete-action-parser.md`](discrete-action-parser.md)
- Safety gate (downstream): [`safety-clamp-and-fallback.md`](safety-clamp-and-fallback.md)
- Epic walkthrough: [`index.html`](index.html)
- MVP acceptance criteria: [`../../mvp_definition.md`](../../mvp_definition.md)
- Architecture overview: [`../../architecture_summary.md`](../../architecture_summary.md)
