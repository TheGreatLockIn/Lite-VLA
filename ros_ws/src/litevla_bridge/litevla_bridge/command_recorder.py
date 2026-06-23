"""Record command history to JSONL for dataset capture (VLA-28)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import rclpy
from geometry_msgs.msg import Twist
from rclpy.node import Node
from std_msgs.msg import String


class CommandRecorder(Node):
    """Append desired twists and action labels to a JSONL log."""

    def __init__(self) -> None:
        super().__init__("litevla_command_recorder")
        self.declare_parameter("enabled", True)
        self.declare_parameter("output_dir", "outputs/teleop")
        self.declare_parameter("source", "teleop")
        self.declare_parameter("desired_twist_topic", "/litevla/desired_twist")
        self.declare_parameter("current_action_topic", "/litevla/current_action")

        self._enabled = bool(self.get_parameter("enabled").value)
        if not self._enabled:
            self.get_logger().info("Command recording disabled")
            self._log_path = None
            return

        base = Path(str(self.get_parameter("output_dir").value))
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        self._run_dir = base / stamp
        self._run_dir.mkdir(parents=True, exist_ok=True)
        self._log_path = self._run_dir / "commands.jsonl"
        self._source = str(self.get_parameter("source").value)
        self._latest_action = "STOP"
        self._latest_linear = 0.0
        self._latest_angular = 0.0

        twist_topic = str(self.get_parameter("desired_twist_topic").value)
        action_topic = str(self.get_parameter("current_action_topic").value)
        self.create_subscription(Twist, twist_topic, self._on_twist, 10)
        self.create_subscription(String, action_topic, self._on_action, 10)
        self.get_logger().info(f"Recording commands → {self._log_path}")

    def _stamp_iso(self) -> str:
        now = self.get_clock().now().to_msg()
        return datetime.fromtimestamp(now.sec + now.nanosec / 1e9, tz=timezone.utc).isoformat()

    def _append(self) -> None:
        if self._log_path is None:
            return
        record = {
            "stamp": self._stamp_iso(),
            "source": self._source,
            "action": self._latest_action,
            "linear_x": self._latest_linear,
            "angular_z": self._latest_angular,
        }
        with self._log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record) + "\n")

    def _on_action(self, msg: String) -> None:
        self._latest_action = msg.data.strip() or "STOP"
        self._append()

    def _on_twist(self, msg: Twist) -> None:
        self._latest_linear = float(msg.linear.x)
        self._latest_angular = float(msg.angular.z)
        # Record on action transitions; twist cache updated here first.


def main(args: list[str] | None = None) -> None:
    rclpy.init(args=args)
    node = CommandRecorder()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
