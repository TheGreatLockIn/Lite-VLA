"""Tests for teleop_utils (no ROS runtime)."""

from litevla_bridge.action_schema import DiscreteAction
from litevla_bridge.teleop_utils import (
    MOVE_BACKWARD,
    active_keys,
    apply_key_hold,
    key_to_action,
    twist_from_keys,
)


def test_forward_keys() -> None:
    assert key_to_action("w") == DiscreteAction.MOVE_FORWARD.value
    assert key_to_action("\x1b[A") == DiscreteAction.MOVE_FORWARD.value


def test_backward_keys() -> None:
    assert key_to_action("s") == MOVE_BACKWARD
    assert key_to_action("\x1b[B") == MOVE_BACKWARD


def test_stop_keys() -> None:
    assert key_to_action(" ") == DiscreteAction.STOP.value
    assert key_to_action("x") == DiscreteAction.STOP.value


def test_quit_returns_none() -> None:
    assert key_to_action("q") is None


def test_twist_forward() -> None:
    linear, angular, action = twist_from_keys({"w"}, max_linear_vel=0.2, max_angular_vel=0.6)
    assert linear == 0.2
    assert angular == 0.0
    assert action == DiscreteAction.MOVE_FORWARD.value


def test_twist_backward() -> None:
    linear, angular, action = twist_from_keys({"s"}, max_linear_vel=0.2, max_angular_vel=0.6)
    assert linear == -0.2
    assert angular == 0.0
    assert action == MOVE_BACKWARD


def test_twist_forward_left_combo() -> None:
    linear, angular, action = twist_from_keys(
        {"w", "a"},
        max_linear_vel=0.2,
        max_angular_vel=0.6,
    )
    assert linear == 0.2
    assert angular == 0.6
    assert "MOVE_FORWARD" in action
    assert "TURN_LEFT" in action


def test_key_hold_expires() -> None:
    holds = apply_key_hold("w", {}, now=1.0, hold_sec=0.1)
    assert holds is not None
    assert active_keys(holds, now=1.05) == {"w"}
    assert active_keys(holds, now=1.2) == set()


def test_opposing_keys_cancel() -> None:
    holds = apply_key_hold("w", {}, now=1.0, hold_sec=0.2)
    assert holds is not None
    holds = apply_key_hold("s", holds, now=1.1, hold_sec=0.2)
    assert holds is not None
    assert "w" not in holds
    linear, _, _ = twist_from_keys(active_keys(holds, now=1.1), max_linear_vel=0.2, max_angular_vel=0.6)
    assert linear == -0.2
