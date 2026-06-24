"""Tests for teleop_utils (no ROS runtime)."""

from litevla_bridge.action_schema import DiscreteAction
from litevla_bridge.teleop_utils import key_to_action


def test_forward_keys() -> None:
    assert key_to_action("w") == DiscreteAction.MOVE_FORWARD.value
    assert key_to_action("\x1b[A") == DiscreteAction.MOVE_FORWARD.value


def test_stop_keys() -> None:
    assert key_to_action(" ") == DiscreteAction.STOP.value
    assert key_to_action("x") == DiscreteAction.STOP.value


def test_quit_returns_none() -> None:
    assert key_to_action("q") is None
