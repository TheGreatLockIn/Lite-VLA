"""ROS sensor_msgs/Image helpers for Lite-VLA (VLA-24)."""

from __future__ import annotations

import numpy as np
from cv_bridge import CvBridge
from sensor_msgs.msg import Image

_BRIDGE = CvBridge()


def ros_image_to_rgb(msg: Image) -> np.ndarray:
    """Convert a sensor_msgs/Image to an HxWx3 uint8 RGB ndarray."""
    if msg.encoding in ("rgb8", "RGB8"):
        array = _BRIDGE.imgmsg_to_cv2(msg, desired_encoding="rgb8")
    elif msg.encoding in ("bgr8", "BGR8"):
        array = _BRIDGE.imgmsg_to_cv2(msg, desired_encoding="bgr8")
        array = array[:, :, ::-1].copy()
    else:
        array = _BRIDGE.imgmsg_to_cv2(msg, desired_encoding="rgb8")

    if array.ndim == 2:
        array = np.stack([array, array, array], axis=-1)
    return np.ascontiguousarray(array, dtype=np.uint8)
