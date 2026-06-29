"""Generate scripted discrete actions before ML is connected (VLA-26)."""

from __future__ import annotations

import rclpy
from geometry_msgs.msg import Twist
from rclpy.node import Node
from std_msgs.msg import String

from litevla_bridge.action_schema import (
    DEFAULT_ACTION_SEQUENCE,
    DiscreteAction,
    action_to_twist,
    parse_action,
)


class DummyActionGenerator(Node):
    """Emit desired twists and action labels for the heartbeat controller."""

    def __init__(self) -> None:
        super().__init__("litevla_dummy_action_generator")
        self.declare_parameter("control_mode", "dummy")
        self.declare_parameter("runtime_mode", "dummy")  # deprecated alias for control_mode
        self.declare_parameter("default_action", DiscreteAction.MOVE_FORWARD.value)
        self.declare_parameter("action_sequence", list(DEFAULT_ACTION_SEQUENCE))
        self.declare_parameter("sequence_step_sec", 2.0)
        self.declare_parameter("desired_twist_topic", "/litevla/desired_twist")
        self.declare_parameter("current_action_topic", "/litevla/current_action")
        self.declare_parameter("max_linear_vel", 0.2)
        self.declare_parameter("max_angular_vel", 0.6)

        control_mode = str(self.get_parameter("control_mode").value)
        if control_mode == "dummy":
            runtime_mode = str(self.get_parameter("runtime_mode").value)
            if runtime_mode != "dummy":
                control_mode = runtime_mode

        if control_mode != "dummy":
            self.get_logger().warn(
                f"control_mode={control_mode!r} — dummy generator idling "
                "(set control_mode:=dummy to run)"
            )
            self._active = False
            self.current_action = DiscreteAction.STOP.value
            self.last_linear = 0.0
            self.last_angular = 0.0
            return

        self._active = True
        self._sequence = self._load_sequence()
        self._index = 0
        self._step_duration = float(self.get_parameter("sequence_step_sec").value)
        max_linear = float(self.get_parameter("max_linear_vel").value)
        max_angular = float(self.get_parameter("max_angular_vel").value)
        self._max_linear = max_linear
        self._max_angular = max_angular

        desired_topic = str(self.get_parameter("desired_twist_topic").value)
        action_topic = str(self.get_parameter("current_action_topic").value)
        self._twist_pub = self.create_publisher(Twist, desired_topic, 10)
        self._action_pub = self.create_publisher(String, action_topic, 10)

        self.current_action = self._sequence[0]
        self.last_linear, self.last_angular = action_to_twist(
            self.current_action,
            max_linear_vel=max_linear,
            max_angular_vel=max_angular,
        )

        self._emit_current(log_transition=True)
        if len(self._sequence) > 1:
            self._sequence_timer = self.create_timer(self._step_duration, self._on_sequence_step)
        else:
            self._sequence_timer = None

        self.get_logger().info(
            f"Dummy mode active — sequence={list(self._sequence)} "
            f"step={self._step_duration:.1f}s → {desired_topic}"
        )

    def _load_sequence(self) -> list[str]:
        raw = self.get_parameter("action_sequence").value
        if not raw:
            default = str(self.get_parameter("default_action").value)
            return [parse_action(default)]
        return [parse_action(str(item)) for item in raw]

    def _emit_current(self, *, log_transition: bool) -> None:
        linear, angular = action_to_twist(
            self.current_action,
            max_linear_vel=self._max_linear,
            max_angular_vel=self._max_angular,
        )
        self.last_linear, self.last_angular = linear, angular

        twist = Twist()
        twist.linear.x = linear
        twist.angular.z = angular
        self._twist_pub.publish(twist)

        action_msg = String()
        action_msg.data = self.current_action
        self._action_pub.publish(action_msg)

        if log_transition:
            stamp = self.get_clock().now().to_msg()
            self.get_logger().info(
                f"action={self.current_action} linear={linear:.3f} angular={angular:.3f} "
                f"stamp={stamp.sec}.{stamp.nanosec:09d}"
            )

    def _on_sequence_step(self) -> None:
        if not self._active or len(self._sequence) <= 1:
            return
        self._index = (self._index + 1) % len(self._sequence)
        self.current_action = self._sequence[self._index]
        self._emit_current(log_transition=True)


def main(args: list[str] | None = None) -> None:
    rclpy.init(args=args)
    node = DummyActionGenerator()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
