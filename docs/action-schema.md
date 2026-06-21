# Discrete action schema

**Human-readable version (browser):** [`action-schema.html`](html/action-schema.html)

This document defines the **discrete action vocabulary** for the Lite-VLA MVP. The VLA model outputs one of these uppercase tokens; downstream code maps each token to bounded `linear_x` and `angular_z` values for ROS `/cmd_vel`.

## Design goals

- **Beginner-friendly**: Fixed tokens are easier to label, parse, and evaluate than continuous velocities.
- **Safe by default**: Nominal speeds match MVP limits (0.2 m/s linear, 0.6 rad/s angular); config safety ceilings further clamp output.
- **Shared contract**: Parser, dummy controller, dataset labels, and prompts all use the same names from `litevla.actions`.

## Allowed actions

| Action | Meaning | Nominal `linear_x` (m/s) | Nominal `angular_z` (rad/s) |
|--------|---------|--------------------------|-----------------------------|
| `MOVE_FORWARD` | Drive toward the goal | 0.2 | 0.0 |
| `TURN_LEFT` | Rotate left in place | 0.0 | 0.6 |
| `TURN_RIGHT` | Rotate right in place | 0.0 | −0.6 |
| `SLOW_DOWN` | Reduce forward speed near target | 0.1 | 0.0 |
| `STOP` | Halt immediately | 0.0 | 0.0 |

Action names are **uppercase**, **underscore-separated**, and **unambiguous**. Do not use aliases such as `FORWARD` or `GO`.

## Code API

Shared constants and helpers live in `litevla/actions/schema.py`:

| Symbol | Purpose |
|--------|---------|
| `DiscreteAction` | `str` enum of the five allowed tokens |
| `ACTION_NAMES` | Tuple of token strings (stable iteration order) |
| `ACTION_VELOCITIES` | Nominal `(linear_x, angular_z)` per action |
| `is_valid_action(name)` | Returns whether a string is a known token |
| `action_to_twist(action, max_linear_vel=..., max_angular_vel=...)` | Maps token → clamped velocities |

Example:

```python
from litevla.actions import DiscreteAction, action_to_twist

linear, angular = action_to_twist(
    DiscreteAction.MOVE_FORWARD,
    max_linear_vel=0.2,
    max_angular_vel=0.6,
)
# (0.2, 0.0)
```

## Control flow

```
VLA text output (e.g. "MOVE_FORWARD")
        │
        ▼
  [Parser — Story 1019]  ← validates / normalizes token
        │
        ▼
  action_to_twist()      ← this schema
        │
        ▼
  [Safety clamp — Story 1021]
        │
        ▼
  ROS /cmd_vel Twist
```

## Configuration

Safety ceilings come from config (`safety.max_linear_vel`, `safety.max_angular_vel` in `configs/default.example.yaml`). Nominal mapping values are design points; `action_to_twist` clamps to the configured limits.

## Related docs

- MVP demo task and acceptance criteria: [`mvp_definition.md`](mvp_definition.md)
- Architecture action-parser role: [`architecture_summary.md`](architecture_summary.md)

## Validation

```bash
pytest tests/test_action_schema.py -q
python scripts/run_dummy_pipeline.py
```

The dummy pipeline prints all five mapped actions using the shared schema.
