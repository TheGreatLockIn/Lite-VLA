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

from litevla_bridge.action_schema import DiscreteAction
from litevla_bridge.teleop_utils import (
    TELEOP_HELP,
    active_keys,
    apply_key_hold,
    twist_from_keys,
)


class TeleopKeyboard(Node):
    """Read keyboard input and publish desired twists for the heartbeat."""

    def __init__(self) -> None:
        super().__init__("litevla_teleop_keyboard")
        self.declare_parameter("control_mode", "teleop")
        self.declare_parameter("poll_hz", 50.0)
        self.declare_parameter("hold_sec", 0.12)
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
        poll_hz = float(self.get_parameter("poll_hz").value)
        self._hold_sec = float(self.get_parameter("hold_sec").value)

        desired_topic = str(self.get_parameter("desired_twist_topic").value)
        action_topic = str(self.get_parameter("current_action_topic").value)
        self._twist_pub = self.create_publisher(Twist, desired_topic, 10)
        self._action_pub = self.create_publisher(String, action_topic, 10)

        self._key_holds: dict[str, float] = {}
        self._last_action = DiscreteAction.STOP.value
        self._stdin_fd = sys.stdin.fileno()
        self._term_settings = termios.tcgetattr(self._stdin_fd)
        tty.setcbreak(self._stdin_fd)

        self._poll_timer = self.create_timer(1.0 / poll_hz, self._tick)
        self._publish_twist(0.0, 0.0, DiscreteAction.STOP.value)
        self.get_logger().info(TELEOP_HELP.strip())

    def destroy_node(self) -> bool:
        if getattr(self, "_active", False):
            termios.tcsetattr(self._stdin_fd, termios.TCSADRAIN, self._term_settings)
        return super().destroy_node()

    def _now(self) -> float:
        return self.get_clock().now().nanoseconds / 1e9

    def _publish_twist(self, linear: float, angular: float, action: str) -> None:
        twist = Twist()
        twist.linear.x = linear
        twist.angular.z = angular
        self._twist_pub.publish(twist)
        action_msg = String()
        action_msg.data = action
        self._action_pub.publish(action_msg)
        changed = action != self._last_action
        self._last_action = action
        if changed:
            self.get_logger().info(
                f"teleop action={action} linear={linear:.3f} angular={angular:.3f}"
            )

    def _read_key(self) -> str | None:
        ready, _, _ = select.select([sys.stdin], [], [], 0.0)
        if not ready:
            return None
        ch = sys.stdin.read(1)
        if ch != "\x1b":
            return ch
        ready, _, _ = select.select([sys.stdin], [], [], 0.0)
        if not ready:
            return ch
        ch += sys.stdin.read(1)
        ready, _, _ = select.select([sys.stdin], [], [], 0.0)
        if not ready:
            return ch
        return ch + sys.stdin.read(1)

    def _drain_keys(self) -> list[str]:
        keys: list[str] = []
        while True:
            key = self._read_key()
            if key is None:
                break
            keys.append(key)
        return keys

    def _tick(self) -> None:
        if not self._active:
            return

        now = self._now()
        for key in self._drain_keys():
            if key in {"q", "Q"}:
                self.get_logger().info("Teleop quit requested")
                self._publish_twist(0.0, 0.0, DiscreteAction.STOP.value)
                raise KeyboardInterrupt
            updated = apply_key_hold(
                key,
                self._key_holds,
                now=now,
                hold_sec=self._hold_sec,
            )
            if updated is None:
                continue
            self._key_holds = updated

        active = active_keys(self._key_holds, now=now)
        if active:
            linear, angular, action = twist_from_keys(
                active,
                max_linear_vel=self._max_linear,
                max_angular_vel=self._max_angular,
            )
            self._publish_twist(linear, angular, action)
            return

        if self._last_action != DiscreteAction.STOP.value:
            self._key_holds.clear()
            self._publish_twist(0.0, 0.0, DiscreteAction.STOP.value)


def main(args: list[str] | None = None) -> None:
    rclpy.init(args=args)
    node = TeleopKeyboard()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        if getattr(node, "_active", False):
            node._publish_twist(0.0, 0.0, DiscreteAction.STOP.value)
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
