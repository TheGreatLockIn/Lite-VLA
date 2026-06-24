"""Tests for drive_pose_utils."""

from __future__ import annotations

from litevla_bridge.drive_pose_utils import Pose2D, at_pose, cmd_vel_toward_pose, DriveLimits


def test_at_pose_when_close() -> None:
    limits = DriveLimits()
    current = Pose2D(1.0, 0.0, 0.0)
    target = Pose2D(1.03, 0.0, 0.0)
    assert at_pose(current, target, limits)


def test_cmd_vel_turns_before_long_forward() -> None:
    limits = DriveLimits()
    current = Pose2D(0.0, 0.0, 0.0)
    target = Pose2D(1.0, 1.0, 0.0)
    twist, reached = cmd_vel_toward_pose(current, target, limits)
    assert not reached
    assert abs(twist.angular.z) > abs(twist.linear.x)
