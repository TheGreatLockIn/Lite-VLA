"""Save one onboard camera frame as 640x480 BGR PNG, then exit."""

from __future__ import annotations

import os
import sys

from controller import Camera, Robot

try:
    import cv2
    import numpy as np
except ImportError:  # pragma: no cover - Webots may use a minimal Python env
    cv2 = None
    np = None


def _save_bgr_png(camera: Camera, output_path: str) -> bool:
    width = camera.getWidth()
    height = camera.getHeight()
    raw = camera.getImage()
    if raw is None:
        return False

    if cv2 is not None and np is not None:
        # Webots getImage() is BGRA row-major.
        bgra = np.frombuffer(raw, dtype=np.uint8).reshape((height, width, 4))
        bgr = bgra[:, :, :3]
        return bool(cv2.imwrite(output_path, bgr))

    return camera.saveImage(output_path, 95) == 0


def main() -> None:
    robot = Robot()
    timestep = int(robot.getBasicTimeStep())
    camera = robot.getDevice("camera")
    camera.enable(timestep)

    for _ in range(30):
        robot.step(timestep)

    output_path = os.environ.get("LITEVLA_CAPTURE_PATH", "capture.png")
    if not _save_bgr_png(camera, output_path):
        print(f"Failed to save image to {output_path}", file=sys.stderr)
        sys.exit(1)

    print(f"Saved {output_path} ({camera.getWidth()}x{camera.getHeight()})")
    sys.exit(0)


if __name__ == "__main__":
    main()
