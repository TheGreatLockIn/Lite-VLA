"""Tests for action_schema import bridge (no ROS runtime)."""

from litevla_bridge.action_schema import (
    DEFAULT_ACTION_SEQUENCE,
    action_to_twist,
    parse_action,
)


def test_default_sequence_uses_valid_tokens() -> None:
    for action in DEFAULT_ACTION_SEQUENCE:
        assert parse_action(action) == action


def test_action_to_twist_stop() -> None:
    linear, angular = action_to_twist("STOP", max_linear_vel=0.2, max_angular_vel=0.6)
    assert linear == 0.0
    assert angular == 0.0
