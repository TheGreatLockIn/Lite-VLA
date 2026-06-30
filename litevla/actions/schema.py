"""Discrete action schema: allowed tokens and nominal velocity mapping.

The VLA model outputs one of these uppercase action tokens. Downstream modules
(parser, safety layer, ROS publisher) convert tokens into bounded Twist values.
"""

from __future__ import annotations

from enum import Enum
from typing import Final

# MVP design-point limits (see docs/mvp_definition.md). Config may allow lower
# ceilings via safety.max_linear_vel / safety.max_angular_vel.
DEFAULT_LINEAR_FORWARD: Final[float] = 0.2  # m/s
DEFAULT_LINEAR_SLOW: Final[float] = 0.1  # m/s
DEFAULT_ANGULAR_TURN: Final[float] = 0.6  # rad/s


class DiscreteAction(str, Enum):
    """Allowed discrete actions for the Lite-VLA MVP demo."""

    MOVE_FORWARD = "MOVE_FORWARD"
    TURN_LEFT = "TURN_LEFT"
    TURN_RIGHT = "TURN_RIGHT"
    SLOW_DOWN = "SLOW_DOWN"
    STOP = "STOP"


ALL_ACTIONS: Final[tuple[DiscreteAction, ...]] = tuple(DiscreteAction)
ACTION_NAMES: Final[tuple[str, ...]] = tuple(action.value for action in ALL_ACTIONS)

# Nominal (linear_x, angular_z) before config safety clamping.
ACTION_VELOCITIES: Final[dict[DiscreteAction, tuple[float, float]]] = {
    DiscreteAction.MOVE_FORWARD: (DEFAULT_LINEAR_FORWARD, 0.0),
    DiscreteAction.TURN_LEFT: (0.0, DEFAULT_ANGULAR_TURN),
    DiscreteAction.TURN_RIGHT: (0.0, -DEFAULT_ANGULAR_TURN),
    DiscreteAction.SLOW_DOWN: (DEFAULT_LINEAR_SLOW, 0.0),
    DiscreteAction.STOP: (0.0, 0.0),
}


def is_valid_action(name: str) -> bool:
    """Return True when *name* matches a known discrete action token."""
    try:
        DiscreteAction(name)
    except ValueError:
        return False
    return True


def clamp_velocity(value: float, limit: float) -> float:
    """Clamp *value* to [-limit, limit]."""
    return max(-limit, min(limit, value))


def action_to_twist(
    action: DiscreteAction | str,
    *,
    max_linear_vel: float,
    max_angular_vel: float,
) -> tuple[float, float]:
    """Map a discrete action to clamped (linear_x, angular_z) velocities."""
    if isinstance(action, str):
        action = DiscreteAction(action)

    linear, angular = ACTION_VELOCITIES[action]
    return (
        clamp_velocity(linear, max_linear_vel),
        clamp_velocity(angular, max_angular_vel),
    )
