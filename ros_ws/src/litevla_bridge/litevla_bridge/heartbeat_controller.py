"""Stable /cmd_vel heartbeat with safety timeouts and diagnostics (VLA-27)."""

from __future__ import annotations

import json

import rclpy
from geometry_msgs.msg import Twist
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Image
from std_msgs.msg import String

from litevla_bridge.action_schema import DiscreteAction
from litevla_bridge.cmd_vel_publisher import CmdVelPublisher
from litevla_bridge.heartbeat_utils import (
    build_diagnostics,
    format_age_ms,
    is_timed_out,
    seconds_since,
    select_velocities,
)


class HeartbeatController(Node):
    """Publish /cmd_vel at a fixed rate from the latest safe desired command."""

    def __init__(self) -> None:
        super().__init__("litevla_heartbeat_controller")
        self.declare_parameter("heartbeat_hz", 10.0)
        self.declare_parameter("cmd_vel_topic", "/cmd_vel")
        self.declare_parameter("diagnostics_topic", "/litevla/diagnostics")
        self.declare_parameter("desired_twist_topic", "/litevla/desired_twist")
        self.declare_parameter("current_action_topic", "/litevla/current_action")
        self.declare_parameter("image_topic", "/image_raw")
        self.declare_parameter("action_timeout_sec", 0.5)
        self.declare_parameter("frame_timeout_sec", 2.0)
        self.declare_parameter("max_linear_vel", 0.2)
        self.declare_parameter("max_angular_vel", 0.6)
        self.declare_parameter("require_frame", True)
        self.declare_parameter("control_mode", "dummy")
        self.declare_parameter("teleop_startup_grace_sec", 0.0)

        self._heartbeat_hz = float(self.get_parameter("heartbeat_hz").value)
        if self._heartbeat_hz <= 0:
            raise ValueError("heartbeat_hz must be positive")

        self._action_timeout = float(self.get_parameter("action_timeout_sec").value)
        self._frame_timeout = float(self.get_parameter("frame_timeout_sec").value)
        self._require_frame = bool(self.get_parameter("require_frame").value)
        self._control_mode = str(self.get_parameter("control_mode").value)
        self._teleop_grace = float(self.get_parameter("teleop_startup_grace_sec").value)

        self._desired_linear = 0.0
        self._desired_angular = 0.0
        self._current_action = DiscreteAction.STOP.value
        self._last_action_time: float | None = None
        self._last_frame_time: float | None = None
        self._last_publish_stamp = ""
        self._timed_out = True
        self._warned_no_teleop = False
        self._started_at = self._now()

        self._cmd_vel = CmdVelPublisher(
            self,
            cmd_vel_topic=str(self.get_parameter("cmd_vel_topic").value),
            max_linear_vel=float(self.get_parameter("max_linear_vel").value),
            max_angular_vel=float(self.get_parameter("max_angular_vel").value),
        )
        diagnostics_topic = str(self.get_parameter("diagnostics_topic").value)
        self._diagnostics_pub = self.create_publisher(String, diagnostics_topic, 10)

        desired_topic = str(self.get_parameter("desired_twist_topic").value)
        action_topic = str(self.get_parameter("current_action_topic").value)
        image_topic = str(self.get_parameter("image_topic").value)

        self.create_subscription(Twist, desired_topic, self._on_desired_twist, 10)
        self.create_subscription(String, action_topic, self._on_current_action, 10)
        self.create_subscription(Image, image_topic, self._on_image, qos_profile_sensor_data)

        self._heartbeat_timer = self.create_timer(1.0 / self._heartbeat_hz, self._on_heartbeat)
        self._diag_log_timer = self.create_timer(1.0, self._on_diag_log)

        self.get_logger().info(
            f"Heartbeat {self._heartbeat_hz:.1f} Hz on {self._cmd_vel.topic} "
            f"control_mode={self._control_mode} "
            f"(action_timeout={self._action_timeout}s frame_timeout={self._frame_timeout}s)"
        )

    def _now(self) -> float:
        return self.get_clock().now().nanoseconds / 1e9

    def _on_desired_twist(self, msg: Twist) -> None:
        self._desired_linear = float(msg.linear.x)
        self._desired_angular = float(msg.angular.z)
        self._last_action_time = self._now()

    def _on_current_action(self, msg: String) -> None:
        self._current_action = msg.data.strip() or DiscreteAction.STOP.value
        self._last_action_time = self._now()

    def _on_image(self, _msg: Image) -> None:
        self._last_frame_time = self._now()

    def _on_heartbeat(self) -> None:
        now = self._now()
        self._timed_out = is_timed_out(
            now,
            self._last_action_time,
            self._last_frame_time,
            action_timeout_sec=self._action_timeout,
            frame_timeout_sec=self._frame_timeout,
            require_frame=self._require_frame,
        )
        linear, angular = select_velocities(
            self._desired_linear,
            self._desired_angular,
            timed_out=self._timed_out,
        )
        self._cmd_vel.publish_twist(linear, angular)
        stamp = self.get_clock().now().to_msg()
        self._last_publish_stamp = f"{stamp.sec}.{stamp.nanosec:09d}"

        action_age = seconds_since(self._last_action_time, now)
        frame_age = seconds_since(self._last_frame_time, now)
        payload = build_diagnostics(
            heartbeat_hz=self._heartbeat_hz,
            last_cmd=self._current_action,
            last_publish_stamp=self._last_publish_stamp,
            action_age_ms=None if action_age is None else action_age * 1000.0,
            frame_age_ms=None if frame_age is None else frame_age * 1000.0,
            timed_out=self._timed_out,
        )
        payload["control_mode"] = self._control_mode
        diag = String()
        diag.data = json.dumps(payload)
        self._diagnostics_pub.publish(diag)

    def _on_diag_log(self) -> None:
        now = self._now()
        action_age = seconds_since(self._last_action_time, now)
        frame_age = seconds_since(self._last_frame_time, now)
        if (
            self._control_mode == "teleop"
            and action_age is None
            and not self._warned_no_teleop
            and (now - self._started_at) >= self._teleop_grace
        ):
            self._warned_no_teleop = True
            self.get_logger().error(
                "No teleop commands received (action_age=n/a). "
                "teleop_keyboard is idle or not in an interactive terminal — "
                "run ./ros_ws/scripts/run_teleop_sim.sh from GNOME Terminal / Konsole."
            )
        self.get_logger().info(
            f"heartbeat health timed_out={self._timed_out} "
            f"action={self._current_action} "
            f"action_age_ms={format_age_ms(action_age)} "
            f"frame_age_ms={format_age_ms(frame_age)}",
            throttle_duration_sec=1.0,
        )


def main(args: list[str] | None = None) -> None:
    rclpy.init(args=args)
    node = HeartbeatController()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node._cmd_vel.publish_stop()
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
