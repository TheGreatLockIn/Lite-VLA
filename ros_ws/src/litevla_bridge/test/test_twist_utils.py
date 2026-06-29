"""Tests for twist_utils (no ROS runtime required)."""

from litevla_bridge.twist_utils import clamp_velocity, make_twist


def test_make_twist_sets_diff_drive_axes() -> None:
    twist = make_twist(0.15, -0.4)
    assert twist.linear.x == 0.15
    assert twist.linear.y == 0.0
    assert twist.angular.z == -0.4


def test_clamp_velocity_symmetric() -> None:
    linear, angular = clamp_velocity(1.0, -2.0, max_linear=0.2, max_angular=0.6)
    assert linear == 0.2
    assert angular == -0.6


def test_clamp_velocity_within_limits_unchanged() -> None:
    linear, angular = clamp_velocity(0.1, 0.3, max_linear=0.2, max_angular=0.6)
    assert linear == 0.1
    assert angular == 0.3
