"""geometry_msgs/Twist helpers for diff-drive commands (VLA-25)."""

from __future__ import annotations

from geometry_msgs.msg import Twist


def make_twist(linear_x: float = 0.0, angular_z: float = 0.0) -> Twist:
    """Build a diff-drive Twist (linear.x + angular.z only)."""
    twist = Twist()
    twist.linear.x = float(linear_x)
    twist.angular.z = float(angular_z)
    return twist


def clamp_velocity(
    linear_x: float,
    angular_z: float,
    max_linear: float,
    max_angular: float,
) -> tuple[float, float]:
    """Clamp linear and angular velocities to symmetric safety limits."""
    max_linear = abs(max_linear)
    max_angular = abs(max_angular)
    linear_x = max(-max_linear, min(max_linear, linear_x))
    angular_z = max(-max_angular, min(max_angular, angular_z))
    return linear_x, angular_z
