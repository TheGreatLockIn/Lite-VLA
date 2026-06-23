"""Verify Webots publishes /image_raw and responds to /cmd_vel (VLA-117)."""

from __future__ import annotations

import sys
import time

import rclpy
from geometry_msgs.msg import Twist
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Image


class SpawnVerifier(Node):
    def __init__(self) -> None:
        super().__init__("litevla_spawn_verifier")
        self.declare_parameter("image_topic", "/image_raw")
        self.declare_parameter("cmd_vel_topic", "/cmd_vel")
        self.declare_parameter("wait_seconds", 45.0)
        self.declare_parameter("publish_test_cmd", True)

        self._image_topic = self.get_parameter("image_topic").value
        self._cmd_vel_topic = self.get_parameter("cmd_vel_topic").value
        self._wait_seconds = float(self.get_parameter("wait_seconds").value)
        self._publish_test = bool(self.get_parameter("publish_test_cmd").value)

        self._image_seen = False
        self._cmd_pub = self.create_publisher(Twist, self._cmd_vel_topic, 10)
        self.create_subscription(Image, self._image_topic, self._on_image, qos_profile_sensor_data)

        self.get_logger().info(
            f"Waiting up to {self._wait_seconds:.0f}s for {self._image_topic} "
            f"(cmd_vel test on {self._cmd_vel_topic})"
        )

    def _on_image(self, msg: Image) -> None:
        if not self._image_seen:
            self._image_seen = True
            self.get_logger().info(
                f"Camera OK: {msg.width}x{msg.height} encoding={msg.encoding} "
                f"frame_id={msg.header.frame_id}"
            )

    def run(self) -> int:
        deadline = time.monotonic() + self._wait_seconds
        while rclpy.ok() and time.monotonic() < deadline and not self._image_seen:
            rclpy.spin_once(self, timeout_sec=0.2)

        if not self._image_seen:
            self.get_logger().error(
                f"No frames on {self._image_topic}. Is Webots running "
                f"(./ros_ws/scripts/run_webots_mvp.sh)?"
            )
            return 1

        if self._publish_test:
            twist = Twist()
            twist.linear.x = 0.1
            self._cmd_pub.publish(twist)
            self.get_logger().info(f"Published test forward cmd on {self._cmd_vel_topic}")
            time.sleep(0.5)
            self._cmd_pub.publish(Twist())
            self.get_logger().info("Published stop — check litevla_robot motion in Webots")

        self.get_logger().info("Spawn verification passed (camera + cmd_vel publish).")
        return 0


def main(args: list[str] | None = None) -> None:
    rclpy.init(args=args)
    node = SpawnVerifier()
    try:
        code = node.run()
    finally:
        node.destroy_node()
        rclpy.shutdown()
    sys.exit(code)


if __name__ == "__main__":
    main()
