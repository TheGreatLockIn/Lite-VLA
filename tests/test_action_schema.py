"""Tests for litevla.actions schema (no ROS runtime)."""

import pytest

from litevla.actions import (
    ACTION_NAMES,
    DiscreteAction,
    action_to_twist,
    is_valid_action,
    parse_action,
)


def test_action_names_cover_all_enum_values() -> None:
    assert set(ACTION_NAMES) == {item.value for item in DiscreteAction}


def test_action_to_twist_forward() -> None:
    linear, angular = action_to_twist(DiscreteAction.MOVE_FORWARD, max_linear_vel=0.2, max_angular_vel=0.6)
    assert linear == 0.2
    assert angular == 0.0


def test_action_to_twist_clamps() -> None:
    linear, angular = action_to_twist("TURN_LEFT", max_linear_vel=0.1, max_angular_vel=0.3)
    assert linear == 0.0
    assert angular == 0.3


def test_parse_action_rejects_unknown() -> None:
    with pytest.raises(ValueError, match="Unknown action"):
        parse_action("FORWARD")


def test_is_valid_action() -> None:
    assert is_valid_action("STOP")
    assert not is_valid_action("GO")
