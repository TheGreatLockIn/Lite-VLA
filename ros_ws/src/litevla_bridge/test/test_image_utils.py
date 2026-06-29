"""Tests for image_utils (requires ROS message types + cv_bridge at runtime)."""

import pytest
from sensor_msgs.msg import Image

cv_bridge = pytest.importorskip("cv_bridge")

from litevla_bridge.image_utils import ros_image_to_rgb  # noqa: E402


def _make_rgb8_image(width: int, height: int, pixel: tuple[int, int, int]) -> Image:
    msg = Image()
    msg.height = height
    msg.width = width
    msg.encoding = "rgb8"
    msg.is_bigendian = 0
    msg.step = width * 3
    r, g, b = pixel
    msg.data = bytes([r, g, b] * width * height)
    return msg


def test_ros_image_to_rgb_shape_and_dtype() -> None:
    msg = _make_rgb8_image(4, 3, (10, 20, 30))
    array = ros_image_to_rgb(msg)
    assert array.shape == (3, 4, 3)
    assert array.dtype.name == "uint8"
    assert tuple(array[0, 0]) == (10, 20, 30)


def test_ros_image_to_rgb_bgr8() -> None:
    msg = Image()
    msg.height = 1
    msg.width = 1
    msg.encoding = "bgr8"
    msg.is_bigendian = 0
    msg.step = 3
    msg.data = bytes([0, 255, 0])  # green in BGR → (0, 255, 0) RGB
    array = ros_image_to_rgb(msg)
    assert tuple(array[0, 0]) == (0, 255, 0)
