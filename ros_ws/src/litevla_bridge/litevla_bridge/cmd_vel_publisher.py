"""Publish velocity commands for diff-drive (VLA-25).

On ROS 2 Jazzy+, diff_drive_controller requires geometry_msgs/TwistStamped on
~/cmd_vel. Older distros use unstamped Twist.
"""

from __future__ import annotations

import os

from geometry_msgs.msg import Twist, TwistStamped

import rclpy
from rclpy.node import Node

from litevla_bridge.twist_utils import clamp_velocity, make_twist


def use_twist_stamped() -> bool:
    return os.environ.get("ROS_DISTRO", "") in {"jazzy", "kilted", "rolling"}


class CmdVelPublisher:
    """Reusable cmd_vel publisher for dummy, heartbeat, and teleop nodes."""

    def __init__(
        self,
        node: Node,
        cmd_vel_topic: str = "/cmd_vel",
        max_linear_vel: float = 0.2,
        max_angular_vel: float = 0.6,
        queue_size: int = 10,
        frame_id: str = "base_link",
    ) -> None:
        self._node = node
        self._max_linear = float(max_linear_vel)
        self._max_angular = float(max_angular_vel)
        self._topic = cmd_vel_topic
        self._frame_id = frame_id
        self._stamped = use_twist_stamped()
        msg_type = TwistStamped if self._stamped else Twist
        self._publisher = node.create_publisher(msg_type, cmd_vel_topic, queue_size)
        self._last_twist = make_twist(0.0, 0.0)
        node.get_logger().info(
            f"cmd_vel publisher ready on {cmd_vel_topic} "
            f"type={'TwistStamped' if self._stamped else 'Twist'} "
            f"(limits: linear={self._max_linear}, angular={self._max_angular})"
        )

    @property
    def topic(self) -> str:
        return self._topic

    @property
    def last_twist(self) -> Twist:
        return self._last_twist

    def publish_twist(self, linear_x: float, angular_z: float) -> Twist:
        """Clamp, publish, and return the Twist payload."""
        linear_x, angular_z = clamp_velocity(
            linear_x, angular_z, self._max_linear, self._max_angular
        )
        twist = make_twist(linear_x, angular_z)
        if self._stamped:
            stamped = TwistStamped()
            stamped.header.stamp = self._node.get_clock().now().to_msg()
            stamped.header.frame_id = self._frame_id
            stamped.twist = twist
            self._publisher.publish(stamped)
        else:
            self._publisher.publish(twist)
        self._last_twist = twist
        return twist

    def publish_stop(self) -> Twist:
        return self.publish_twist(0.0, 0.0)


class CmdVelPublisherNode(Node):
    """Standalone node exposing CmdVelPublisher (for launch/testing)."""

    def __init__(self) -> None:
        super().__init__("litevla_cmd_vel_publisher")
        self.declare_parameter("cmd_vel_topic", "/cmd_vel")
        self.declare_parameter("max_linear_vel", 0.2)
        self.declare_parameter("max_angular_vel", 0.6)
        self._bridge = CmdVelPublisher(
            self,
            cmd_vel_topic=str(self.get_parameter("cmd_vel_topic").value),
            max_linear_vel=float(self.get_parameter("max_linear_vel").value),
            max_angular_vel=float(self.get_parameter("max_angular_vel").value),
        )

    @property
    def publisher(self) -> CmdVelPublisher:
        return self._bridge


def main(args: list[str] | None = None) -> None:
    rclpy.init(args=args)
    node = CmdVelPublisherNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
