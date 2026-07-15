"""Simple diff-drive go-to-pose helpers using odometry (reference capture)."""

from __future__ import annotations

import math
from dataclasses import dataclass

from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry

from litevla_bridge.twist_utils import clamp_velocity, make_twist


def yaw_from_odom(msg: Odometry) -> float:
    """Extract yaw (rad) from odometry quaternion."""
    q = msg.pose.pose.orientation
    siny_cosp = 2.0 * (q.w * q.z + q.x * q.y)
    cosy_cosp = 1.0 - 2.0 * (q.y * q.y + q.z * q.z)
    return math.atan2(siny_cosp, cosy_cosp)


def wrap_angle(angle: float) -> float:
    while angle > math.pi:
        angle -= 2.0 * math.pi
    while angle < -math.pi:
        angle += 2.0 * math.pi
    return angle


@dataclass(frozen=True)
class Pose2D:
    x: float
    y: float
    yaw: float = 0.0


@dataclass(frozen=True)
class DriveLimits:
    max_linear: float = 0.18
    max_angular: float = 0.5
    linear_gain: float = 0.8
    angular_gain: float = 1.6
    at_position_m: float = 0.06
    at_yaw_rad: float = 0.08


def pose_error(current: Pose2D, target: Pose2D) -> tuple[float, float, float]:
    """Return (distance, heading_to_goal, yaw_error)."""
    dx = target.x - current.x
    dy = target.y - current.y
    distance = math.hypot(dx, dy)
    heading = math.atan2(dy, dx)
    yaw_error = wrap_angle(target.yaw - current.yaw)
    return distance, heading, yaw_error


def at_pose(current: Pose2D, target: Pose2D, limits: DriveLimits) -> bool:
    distance, _, yaw_error = pose_error(current, target)
    return distance <= limits.at_position_m and abs(yaw_error) <= limits.at_yaw_rad


def cmd_vel_toward_pose(
    current: Pose2D,
    target: Pose2D,
    limits: DriveLimits,
) -> tuple[Twist, bool]:
    """Return (twist, reached). Turn-first unicycle controller."""
    distance, heading_to_goal, yaw_error = pose_error(current, target)

    if distance <= limits.at_position_m:
        if abs(yaw_error) <= limits.at_yaw_rad:
            return make_twist(0.0, 0.0), True
        angular = limits.angular_gain * yaw_error
        angular = clamp_velocity(0.0, angular, limits.max_linear, limits.max_angular)[1]
        return make_twist(0.0, angular), False

    heading_error = wrap_angle(heading_to_goal - current.yaw)
    if abs(heading_error) > 0.35:
        angular = limits.angular_gain * heading_error
        angular = clamp_velocity(0.0, angular, limits.max_linear, limits.max_angular)[1]
        return make_twist(0.0, angular), False

    linear = min(limits.max_linear, limits.linear_gain * distance)
    angular = limits.angular_gain * heading_error
    linear, angular = clamp_velocity(linear, angular, limits.max_linear, limits.max_angular)
    return make_twist(linear, angular), False
