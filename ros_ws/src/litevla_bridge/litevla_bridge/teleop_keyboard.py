"""Keyboard teleoperation for Lite-VLA MVP (VLA-28)."""

from __future__ import annotations

import select
import sys
import termios
import tty

import rclpy
from geometry_msgs.msg import Twist
from rclpy.node import Node
from std_msgs.msg import String

from litevla_bridge.action_schema import DiscreteAction, action_to_twist
from litevla_bridge.teleop_utils import TELEOP_HELP, key_to_action


class TeleopKeyboard(Node):
    """Read keyboard input and publish desired twists for the heartbeat."""

    def __init__(self) -> None:
        super().__init__("litevla_teleop_keyboard")
        self.declare_parameter("control_mode", "teleop")
        self.declare_parameter("refresh_hz", 10.0)
        self.declare_parameter("desired_twist_topic", "/litevla/desired_twist")
        self.declare_parameter("current_action_topic", "/litevla/current_action")
        self.declare_parameter("max_linear_vel", 0.2)
        self.declare_parameter("max_angular_vel", 0.6)

        control_mode = str(self.get_parameter("control_mode").value)
        if control_mode != "teleop":
            self.get_logger().warn(
                f"control_mode={control_mode!r} — teleop idle (set control_mode:=teleop)"
            )
            self._active = False
            return

        if not sys.stdin.isatty():
            self.get_logger().error("stdin is not a TTY — run teleop in an interactive terminal")
            self._active = False
            return

        self._active = True
        self._max_linear = float(self.get_parameter("max_linear_vel").value)
        self._max_angular = float(self.get_parameter("max_angular_vel").value)
        refresh_hz = float(self.get_parameter("refresh_hz").value)

        desired_topic = str(self.get_parameter("desired_twist_topic").value)
        action_topic = str(self.get_parameter("current_action_topic").value)
        self._twist_pub = self.create_publisher(Twist, desired_topic, 10)
        self._action_pub = self.create_publisher(String, action_topic, 10)

        self.current_action = DiscreteAction.STOP.value
        self._stdin_fd = sys.stdin.fileno()
        self._term_settings = termios.tcgetattr(self._stdin_fd)
        tty.setcbreak(self._stdin_fd)

        self._refresh_timer = self.create_timer(1.0 / refresh_hz, self._refresh_command)
        self._poll_timer = self.create_timer(0.05, self._poll_keyboard)
        self._emit_stop()
        self.get_logger().info(TELEOP_HELP.strip())

    def destroy_node(self) -> bool:
        if getattr(self, "_active", False):
            termios.tcsetattr(self._stdin_fd, termios.TCSADRAIN, self._term_settings)
        return super().destroy_node()

    def _publish(self, action: str) -> None:
        self.current_action = action
        linear, angular = action_to_twist(
            action,
            max_linear_vel=self._max_linear,
            max_angular_vel=self._max_angular,
        )
        twist = Twist()
        twist.linear.x = linear
        twist.angular.z = angular
        self._twist_pub.publish(twist)
        action_msg = String()
        action_msg.data = action
        self._action_pub.publish(action_msg)
        self.get_logger().info(f"teleop action={action} linear={linear:.3f} angular={angular:.3f}")

    def _emit_stop(self) -> None:
        self._publish(DiscreteAction.STOP.value)

    def _refresh_command(self) -> None:
        if not self._active:
            return
        if self.current_action == DiscreteAction.STOP.value:
            return
        self._publish(self.current_action)

    def _read_key(self) -> str | None:
        ready, _, _ = select.select([sys.stdin], [], [], 0.0)
        if not ready:
            return None
        ch = sys.stdin.read(1)
        if ch != "\x1b":
            return ch
        ready, _, _ = select.select([sys.stdin], [], [], 0.01)
        if not ready:
            return ch
        ch += sys.stdin.read(1)
        ready, _, _ = select.select([sys.stdin], [], [], 0.01)
        if not ready:
            return ch
        return ch + sys.stdin.read(1)

    def _poll_keyboard(self) -> None:
        if not self._active:
            return
        key = self._read_key()
        if key is None:
            return
        if key in {"q", "Q"}:
            self.get_logger().info("Teleop quit requested")
            self._emit_stop()
            raise KeyboardInterrupt
        action = key_to_action(key)
        if action is None:
            return
        self._publish(action)


def main(args: list[str] | None = None) -> None:
    rclpy.init(args=args)
    node = TeleopKeyboard()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        if getattr(node, "_active", False):
            node._emit_stop()
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
