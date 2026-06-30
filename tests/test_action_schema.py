"""Tests for the discrete action schema."""

from __future__ import annotations

import pytest
from litevla.actions import (
    ACTION_NAMES,
    ACTION_VELOCITIES,
    ALL_ACTIONS,
    DEFAULT_ANGULAR_TURN,
    DEFAULT_LINEAR_FORWARD,
    DEFAULT_LINEAR_SLOW,
    DiscreteAction,
    action_to_twist,
    is_valid_action,
)


def test_action_names_are_uppercase_and_unique() -> None:
    assert len(ACTION_NAMES) == len(set(ACTION_NAMES))
    assert all(name == name.upper() for name in ACTION_NAMES)
    assert ACTION_NAMES == (
        "MOVE_FORWARD",
        "TURN_LEFT",
        "TURN_RIGHT",
        "SLOW_DOWN",
        "STOP",
    )


def test_all_actions_have_velocity_mapping() -> None:
    for action in ALL_ACTIONS:
        assert action in ACTION_VELOCITIES
        linear, angular = ACTION_VELOCITIES[action]
        assert isinstance(linear, float)
        assert isinstance(angular, float)


def test_nominal_velocities_match_mvp_design_points() -> None:
    assert ACTION_VELOCITIES[DiscreteAction.MOVE_FORWARD] == (DEFAULT_LINEAR_FORWARD, 0.0)
    assert ACTION_VELOCITIES[DiscreteAction.SLOW_DOWN] == (DEFAULT_LINEAR_SLOW, 0.0)
    assert ACTION_VELOCITIES[DiscreteAction.TURN_LEFT] == (0.0, DEFAULT_ANGULAR_TURN)
    assert ACTION_VELOCITIES[DiscreteAction.TURN_RIGHT] == (0.0, -DEFAULT_ANGULAR_TURN)
    assert ACTION_VELOCITIES[DiscreteAction.STOP] == (0.0, 0.0)


@pytest.mark.parametrize(
    ("action", "expected"),
    [
        (DiscreteAction.MOVE_FORWARD, (0.2, 0.0)),
        (DiscreteAction.TURN_LEFT, (0.0, 0.6)),
        (DiscreteAction.TURN_RIGHT, (0.0, -0.6)),
        (DiscreteAction.SLOW_DOWN, (0.1, 0.0)),
        (DiscreteAction.STOP, (0.0, 0.0)),
    ],
)
def test_action_to_twist_at_mvp_limits(
    action: DiscreteAction,
    expected: tuple[float, float],
) -> None:
    assert action_to_twist(action, max_linear_vel=0.2, max_angular_vel=0.6) == expected


def test_action_to_twist_accepts_string_tokens() -> None:
    assert action_to_twist("STOP", max_linear_vel=0.5, max_angular_vel=1.0) == (0.0, 0.0)


def test_action_to_twist_clamps_to_config_limits() -> None:
    linear, angular = action_to_twist(
        DiscreteAction.MOVE_FORWARD,
        max_linear_vel=0.1,
        max_angular_vel=0.3,
    )
    assert linear == pytest.approx(0.1)
    assert angular == pytest.approx(0.0)


def test_is_valid_action() -> None:
    assert is_valid_action("MOVE_FORWARD") is True
    assert is_valid_action("FORWARD") is False
    assert is_valid_action("") is False


def test_invalid_action_string_raises() -> None:
    with pytest.raises(ValueError):
        action_to_twist("FORWARD", max_linear_vel=0.2, max_angular_vel=0.6)
