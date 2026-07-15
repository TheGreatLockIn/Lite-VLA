"""Keyboard key → twist mapping for game-style teleop (VLA-28)."""

from __future__ import annotations

from litevla_bridge.action_schema import DiscreteAction

# Teleop-only label for reverse (not part of ML action vocabulary).
MOVE_BACKWARD = "MOVE_BACKWARD"

_FORWARD_KEYS = frozenset({"w", "W", "\x1b[A"})
_BACKWARD_KEYS = frozenset({"s", "S", "\x1b[B"})
_LEFT_KEYS = frozenset({"a", "A", "\x1b[D"})
_RIGHT_KEYS = frozenset({"d", "D", "\x1b[C"})
_STOP_KEYS = frozenset({"x", "X", " ", "\x03"})
_DRIVE_KEYS = _FORWARD_KEYS | _BACKWARD_KEYS | _LEFT_KEYS | _RIGHT_KEYS

TELEOP_HELP = """
Lite-VLA keyboard teleop (game-style)
  w / ↑     drive forward
  s / ↓     drive backward
  a / ←     turn left
  d / →     turn right
  x / space brake
  q         quit
"""


def key_to_action(key: str) -> str | None:
    """Legacy single-key lookup (tests / compatibility)."""
    if key in {"q", "Q"}:
        return None
    if key in _STOP_KEYS:
        return DiscreteAction.STOP.value
    if key in _FORWARD_KEYS:
        return DiscreteAction.MOVE_FORWARD.value
    if key in _BACKWARD_KEYS:
        return MOVE_BACKWARD
    if key in _LEFT_KEYS:
        return DiscreteAction.TURN_LEFT.value
    if key in _RIGHT_KEYS:
        return DiscreteAction.TURN_RIGHT.value
    return None


def twist_from_keys(
    keys: set[str],
    *,
    max_linear_vel: float,
    max_angular_vel: float,
) -> tuple[float, float, str]:
    """Map currently active keys to (linear_x, angular_z, action_label)."""
    forward = bool(keys & _FORWARD_KEYS)
    backward = bool(keys & _BACKWARD_KEYS)
    left = bool(keys & _LEFT_KEYS)
    right = bool(keys & _RIGHT_KEYS)

    if keys & _STOP_KEYS:
        return 0.0, 0.0, DiscreteAction.STOP.value

    linear = 0.0
    if forward and not backward:
        linear = max_linear_vel
    elif backward and not forward:
        linear = -max_linear_vel

    angular = 0.0
    if left and not right:
        angular = max_angular_vel
    elif right and not left:
        angular = -max_angular_vel

    if linear == 0.0 and angular == 0.0:
        return 0.0, 0.0, DiscreteAction.STOP.value

    parts: list[str] = []
    if linear > 0:
        parts.append(DiscreteAction.MOVE_FORWARD.value)
    elif linear < 0:
        parts.append(MOVE_BACKWARD)
    if angular > 0:
        parts.append(DiscreteAction.TURN_LEFT.value)
    elif angular < 0:
        parts.append(DiscreteAction.TURN_RIGHT.value)

    return linear, angular, "+".join(parts)


def apply_key_hold(
    key: str,
    holds: dict[str, float],
    *,
    now: float,
    hold_sec: float,
) -> dict[str, float] | None:
    """Extend per-key hold deadlines. Returns None to quit teleop."""
    if key in {"q", "Q"}:
        return None
    if key in _STOP_KEYS:
        return {}
    if key not in _DRIVE_KEYS:
        return holds

    if key in _FORWARD_KEYS:
        holds = {k: v for k, v in holds.items() if k not in _BACKWARD_KEYS}
    elif key in _BACKWARD_KEYS:
        holds = {k: v for k, v in holds.items() if k not in _FORWARD_KEYS}
    if key in _LEFT_KEYS:
        holds = {k: v for k, v in holds.items() if k not in _RIGHT_KEYS}
    elif key in _RIGHT_KEYS:
        holds = {k: v for k, v in holds.items() if k not in _LEFT_KEYS}

    holds[key] = now + hold_sec
    return holds


def active_keys(holds: dict[str, float], *, now: float) -> set[str]:
    """Return keys whose hold deadline has not expired."""
    return {key for key, until in holds.items() if until >= now}
