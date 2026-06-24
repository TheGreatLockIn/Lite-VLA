"""Discrete action vocabulary for Lite-VLA MVP (Epic 103 / VLA-29)."""

from __future__ import annotations

from enum import Enum
from typing import Final


class DiscreteAction(str, Enum):
    MOVE_FORWARD = "MOVE_FORWARD"
    TURN_LEFT = "TURN_LEFT"
    TURN_RIGHT = "TURN_RIGHT"
    SLOW_DOWN = "SLOW_DOWN"
    STOP = "STOP"


ACTION_NAMES: Final[tuple[str, ...]] = tuple(action.value for action in DiscreteAction)

ACTION_VELOCITIES: Final[dict[str, tuple[float, float]]] = {
    DiscreteAction.MOVE_FORWARD.value: (0.2, 0.0),
    DiscreteAction.TURN_LEFT.value: (0.0, 0.6),
    DiscreteAction.TURN_RIGHT.value: (0.0, -0.6),
    DiscreteAction.SLOW_DOWN.value: (0.1, 0.0),
    DiscreteAction.STOP.value: (0.0, 0.0),
}

DEFAULT_ACTION_SEQUENCE: Final[tuple[str, ...]] = (
    DiscreteAction.MOVE_FORWARD.value,
    DiscreteAction.MOVE_FORWARD.value,
    DiscreteAction.TURN_LEFT.value,
    DiscreteAction.STOP.value,
)


def is_valid_action(name: str) -> bool:
    return name in ACTION_VELOCITIES


def parse_action(name: str) -> str:
    """Normalize and validate an action token."""
    token = name.strip().upper()
    if not is_valid_action(token):
        valid = ", ".join(ACTION_NAMES)
        raise ValueError(f"Unknown action {name!r}. Expected one of: {valid}")
    return token


def action_to_twist(
    action: str | DiscreteAction,
    *,
    max_linear_vel: float = 0.5,
    max_angular_vel: float = 1.0,
) -> tuple[float, float]:
    """Map a discrete action to clamped (linear_x, angular_z)."""
    token = action.value if isinstance(action, DiscreteAction) else parse_action(action)
    linear, angular = ACTION_VELOCITIES[token]
    max_linear = abs(max_linear_vel)
    max_angular = abs(max_angular_vel)
    linear = max(-max_linear, min(max_linear, linear))
    angular = max(-max_angular, min(max_angular, angular))
    return linear, angular
