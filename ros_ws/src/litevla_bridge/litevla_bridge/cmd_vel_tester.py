"""Cycle movement test commands on /cmd_vel (VLA-25 / subtask 10041)."""

from __future__ import annotations

import rclpy
from rclpy.node import Node

from litevla_bridge.cmd_vel_publisher import CmdVelPublisher

# (label, linear_x, angular_z) — within Webots ros2_control limits (0.2 / 0.6)
_TEST_SEQUENCE: list[tuple[str, float, float]] = [
    ("forward", 0.15, 0.0),
    ("turn_left", 0.0, 0.4),
    ("turn_right", 0.0, -0.4),
    ("stop", 0.0, 0.0),
]


class CmdVelTester(Node):
    def __init__(self) -> None:
        super().__init__("litevla_cmd_vel_tester")
        self.declare_parameter("cmd_vel_topic", "/cmd_vel")
        self.declare_parameter("max_linear_vel", 0.2)
        self.declare_parameter("max_angular_vel", 0.6)
        self.declare_parameter("step_duration_sec", 2.0)

        self._step_duration = float(self.get_parameter("step_duration_sec").value)
        self._publisher = CmdVelPublisher(
            self,
            cmd_vel_topic=str(self.get_parameter("cmd_vel_topic").value),
            max_linear_vel=float(self.get_parameter("max_linear_vel").value),
            max_angular_vel=float(self.get_parameter("max_angular_vel").value),
        )
        self._index = 0
        self._timer = self.create_timer(self._step_duration, self._on_timer)
        self.get_logger().info(
            f"Cycling {len(_TEST_SEQUENCE)} cmd_vel test steps "
            f"every {self._step_duration:.1f}s"
        )
        self._publish_current()

    def _publish_current(self) -> None:
        label, linear_x, angular_z = _TEST_SEQUENCE[self._index]
        twist = self._publisher.publish_twist(linear_x, angular_z)
        self.get_logger().info(
            f"Step {self._index + 1}/{len(_TEST_SEQUENCE)} [{label}]: "
            f"linear.x={twist.linear.x:.3f} angular.z={twist.angular.z:.3f}"
        )

    def _on_timer(self) -> None:
        self._index = (self._index + 1) % len(_TEST_SEQUENCE)
        self._publish_current()


def main(args: list[str] | None = None) -> None:
    rclpy.init(args=args)
    node = CmdVelTester()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node._publisher.publish_stop()
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
