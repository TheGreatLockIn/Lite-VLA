"""Subscribe to camera frames and expose latest RGB array (VLA-24)."""

from __future__ import annotations

import time
from pathlib import Path
from typing import TYPE_CHECKING

import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Image

from litevla_bridge.image_utils import ros_image_to_rgb

if TYPE_CHECKING:
    import numpy as np


class CameraSubscriber(Node):
    """Receive camera frames; keep latest RGB array for downstream inference."""

    def __init__(self) -> None:
        super().__init__("litevla_camera_subscriber")
        self.declare_parameter("image_topic", "/image_raw")
        self.declare_parameter("record_frames", False)
        self.declare_parameter("frame_save_dir", "outputs/frames")
        self.declare_parameter("record_interval_sec", 1.0)

        self._image_topic = str(self.get_parameter("image_topic").value)
        self._record_frames = bool(self.get_parameter("record_frames").value)
        self._frame_save_dir = Path(str(self.get_parameter("frame_save_dir").value))
        self._record_interval = float(self.get_parameter("record_interval_sec").value)

        self.latest_frame: np.ndarray | None = None
        self.latest_stamp = None
        self._first_frame_logged = False
        self._last_save_time = 0.0
        self._frame_count = 0

        if self._record_frames:
            self._frame_save_dir.mkdir(parents=True, exist_ok=True)
            self.get_logger().info(f"Frame recording enabled → {self._frame_save_dir}")

        self.create_subscription(
            Image,
            self._image_topic,
            self._on_image,
            qos_profile_sensor_data,
        )
        self.get_logger().info(f"Subscribed to {self._image_topic}")

    def _on_image(self, msg: Image) -> None:
        self._frame_count += 1
        self.latest_stamp = msg.header.stamp

        if not self._first_frame_logged:
            self._first_frame_logged = True
            self.get_logger().info(
                f"First frame: {msg.width}x{msg.height} encoding={msg.encoding} "
                f"stamp={msg.header.stamp.sec}.{msg.header.stamp.nanosec:09d}"
            )

        try:
            self.latest_frame = ros_image_to_rgb(msg)
        except Exception as exc:  # noqa: BLE001 — log and skip bad frames
            self.get_logger().error(f"Failed to convert image: {exc}")
            return

        if self._record_frames:
            self._maybe_save_frame(msg)

    def _maybe_save_frame(self, msg: Image) -> None:
        now = time.monotonic()
        if now - self._last_save_time < self._record_interval:
            return
        self._last_save_time = now

        stamp = msg.header.stamp
        filename = f"{stamp.sec}_{stamp.nanosec:09d}.png"
        path = self._frame_save_dir / filename

        try:
            import cv2

            bgr = cv2.cvtColor(self.latest_frame, cv2.COLOR_RGB2BGR)
            cv2.imwrite(str(path), bgr)
            self.get_logger().info(f"Saved frame #{self._frame_count} → {path}")
        except ImportError:
            self.get_logger().warn("opencv not available; cannot save frames")
        except Exception as exc:  # noqa: BLE001
            self.get_logger().error(f"Failed to save frame: {exc}")


def main(args: list[str] | None = None) -> None:
    rclpy.init(args=args)
    node = CameraSubscriber()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
