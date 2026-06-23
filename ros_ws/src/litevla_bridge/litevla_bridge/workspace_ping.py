"""Minimal ROS 2 node to verify the workspace build and package registration."""

from __future__ import annotations

import rclpy
from rclpy.node import Node


class WorkspacePing(Node):
    """Logs once so `ros2 run litevla_bridge workspace_ping` confirms the overlay works."""

    def __init__(self) -> None:
        super().__init__("litevla_workspace_ping")
        self.get_logger().info(
            "litevla_bridge workspace is built and sourced (VLA-19 smoke check)."
        )


def main(args: list[str] | None = None) -> None:
    rclpy.init(args=args)
    node = WorkspacePing()
    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()
