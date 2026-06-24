"""Drive the robot in Webots and save Purshottam reference camera frames (BGR PNG)."""

from __future__ import annotations

import math
import time
from dataclasses import dataclass
from pathlib import Path

import cv2
import rclpy
from cv_bridge import CvBridge
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Image

from litevla_bridge.drive_pose_utils import (
    DriveLimits,
    Pose2D,
    at_pose,
    cmd_vel_toward_pose,
    yaw_from_odom,
)

# Fixed red cube in mvp_arena.wbt: translation 2 0 0.1
# Robot drives to these poses so the onboard camera matches each action label.
DEFAULT_SCENARIOS: tuple[tuple[str, float, float, float], ...] = (
    ("red_cone_centered.png", 0.22, 0.00, 0.00),
    ("red_cone_left.png", 0.40, -0.58, 0.22),
    ("red_cone_right.png", 0.40, 0.58, -0.22),
    ("stop_barrier_close.png", 1.70, 0.00, 0.00),
)


@dataclass
class Scenario:
    filename: str
    pose: Pose2D


class ReferenceFrameCapture(Node):
    """Drive to preset poses and save /image_raw as 640x480 BGR PNG."""

    def __init__(self) -> None:
        super().__init__("litevla_reference_frame_capture")
        self.declare_parameter("output_dir", "data/reference_images")
        self.declare_parameter("image_topic", "/image_raw")
        self.declare_parameter("cmd_vel_topic", "/cmd_vel")
        self.declare_parameter("expected_width", 640)
        self.declare_parameter("expected_height", 480)
        self.declare_parameter("startup_wait_sec", 3.0)
        self.declare_parameter("ready_timeout_sec", 120.0)
        self.declare_parameter("settle_sec", 1.5)
        self.declare_parameter("drive_timeout_sec", 45.0)
        self.declare_parameter("control_hz", 10.0)

        out = Path(str(self.get_parameter("output_dir").value))
        if not out.is_absolute():
            repo_root = Path(__file__).resolve().parents[4]
            out = repo_root / out
        out.mkdir(parents=True, exist_ok=True)
        self._output_dir = out

        self._expected_size = (
            int(self.get_parameter("expected_width").value),
            int(self.get_parameter("expected_height").value),
        )
        self._settle_sec = float(self.get_parameter("settle_sec").value)
        self._drive_timeout = float(self.get_parameter("drive_timeout_sec").value)
        self._limits = DriveLimits()
        self._bridge = CvBridge()

        self._odom: Odometry | None = None
        self._image: Image | None = None
        self._scenarios = [
            Scenario(name, Pose2D(x, y, yaw)) for name, x, y, yaw in DEFAULT_SCENARIOS
        ]

        image_topic = str(self.get_parameter("image_topic").value)
        cmd_topic = str(self.get_parameter("cmd_vel_topic").value)

        self.create_subscription(Odometry, "/odom", self._on_odom, 10)
        self.create_subscription(Image, image_topic, self._on_image, qos_profile_sensor_data)
        self._cmd_pub = self.create_publisher(Twist, cmd_topic, 10)

        hz = float(self.get_parameter("control_hz").value)
        self._timer = self.create_timer(1.0 / hz, self._tick)
        self._phase = "wait"
        self._phase_started = time.monotonic()
        self._scenario_index = 0
        self._startup_wait = float(self.get_parameter("startup_wait_sec").value)
        self._ready_timeout = float(self.get_parameter("ready_timeout_sec").value)

        self.get_logger().info(f"Reference capture → {self._output_dir}")

    def _on_odom(self, msg: Odometry) -> None:
        self._odom = msg

    def _on_image(self, msg: Image) -> None:
        self._image = msg

    def _current_pose(self) -> Pose2D | None:
        if self._odom is None:
            return None
        p = self._odom.pose.pose.position
        return Pose2D(p.x, p.y, yaw_from_odom(self._odom))

    def _stop(self) -> None:
        self._cmd_pub.publish(Twist())

    def _save_image(self, filename: str) -> None:
        if self._image is None:
            raise RuntimeError("No camera frame available on /image_raw")

        if (self._image.width, self._image.height) != self._expected_size:
            raise RuntimeError(
                f"Expected {self._expected_size[0]}x{self._expected_size[1]}, "
                f"got {self._image.width}x{self._image.height}. "
                "Update mvp_arena.wbt Camera width/height to 640x480."
            )

        bgr = self._bridge.imgmsg_to_cv2(self._image, desired_encoding="bgr8")
        path = self._output_dir / filename
        if not cv2.imwrite(str(path), bgr):
            raise RuntimeError(f"cv2.imwrite failed for {path}")
        self.get_logger().info(f"Saved {path}")

    def _tick(self) -> None:
        now = time.monotonic()

        if self._phase == "wait":
            if self._odom is None or self._image is None:
                if now - self._phase_started > self._ready_timeout:
                    self.get_logger().error(
                        "Timed out waiting for /odom and /image_raw — "
                        "is ros2_control up? Try re-running after a clean Webots start."
                    )
                    self._phase = "done"
                return
            if now - self._phase_started < self._startup_wait:
                return
            self.get_logger().info("Sim ready — starting driven capture sequence")
            self._phase = "drive"
            self._phase_started = now
            return

        if self._phase == "done":
            self._stop()
            rclpy.shutdown()
            return

        if self._scenario_index >= len(self._scenarios):
            self.get_logger().info("All reference frames captured")
            self._phase = "done"
            return

        scenario = self._scenarios[self._scenario_index]
        pose = self._current_pose()
        if pose is None:
            return

        if self._phase == "drive":
            if now - self._phase_started > self._drive_timeout:
                self.get_logger().error(
                    f"Drive timeout reaching {scenario.filename} "
                    f"(target {scenario.pose.x:.2f}, {scenario.pose.y:.2f})"
                )
                rclpy.shutdown()
                return

            twist, reached = cmd_vel_toward_pose(pose, scenario.pose, self._limits)
            self._cmd_pub.publish(twist)
            if reached or at_pose(pose, scenario.pose, self._limits):
                self._stop()
                self.get_logger().info(
                    f"Reached pose for {scenario.filename} at "
                    f"({pose.x:.2f}, {pose.y:.2f}, {math.degrees(pose.yaw):.1f}°)"
                )
                self._phase = "settle"
                self._phase_started = now
            return

        if self._phase == "settle":
            self._stop()
            if now - self._phase_started < self._settle_sec:
                return
            try:
                self._save_image(scenario.filename)
            except RuntimeError as exc:
                self.get_logger().error(str(exc))
                rclpy.shutdown()
                return
            self._scenario_index += 1
            self._phase = "drive"
            self._phase_started = now


def main() -> None:
    rclpy.init()
    node = ReferenceFrameCapture()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        if rclpy.ok():
            try:
                node._stop()
            except Exception:  # noqa: BLE001 — shutdown race with launch
                pass
            node.destroy_node()
            rclpy.shutdown()


if __name__ == "__main__":
    main()
