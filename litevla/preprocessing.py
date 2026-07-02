"""Lite-VLA Image Preprocessing Pipeline."""

from __future__ import annotations

import cv2
import numpy as np


class PreprocessingError(ValueError):
    """Raised when image preprocessing fails due to input validation or format issues."""


class ImagePreprocessor:
    """Preprocesses raw camera frames for VLM inference based on configuration settings."""

    def __init__(self, config: dict):
        """Initialize the preprocessor using the global configuration dictionary."""
        preproc_cfg = config.get("preprocessing", {})
        if not preproc_cfg:
            # Fallback defaults if missing or empty
            preproc_cfg = {
                "resize_width": 512,
                "resize_height": 512,
                "color_format": "rgb",
                "encoding": "jpeg",
            }

        self.resize_width = preproc_cfg.get("resize_width", 512)
        self.resize_height = preproc_cfg.get("resize_height", 512)
        self.color_format = preproc_cfg.get("color_format", "rgb")
        self.encoding = preproc_cfg.get("encoding", "jpeg")

        # Validate settings
        if self.resize_width <= 0 or self.resize_height <= 0:
            raise PreprocessingError(
                f"Invalid resize dimensions: {self.resize_width}x{self.resize_height}"
            )
        if self.color_format not in {"rgb", "bgr", "gray"}:
            raise PreprocessingError(f"Unsupported color format: {self.color_format}")
        if self.encoding not in {"jpeg", "png", "none"}:
            raise PreprocessingError(f"Unsupported encoding: {self.encoding}")

    def preprocess(self, image: np.ndarray) -> bytes | np.ndarray:
        """Process a raw OpenCV BGR image numpy array according to configurations."""
        if not isinstance(image, np.ndarray):
            raise PreprocessingError("Input image must be a numpy ndarray.")

        if image.ndim != 3 or image.shape[2] != 3:
            raise PreprocessingError(
                f"Input image must be a 3-channel (H, W, 3) BGR array, got shape {image.shape}"
            )

        # 1. Color space conversion
        try:
            if self.color_format == "rgb":
                processed = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            elif self.color_format == "gray":
                processed = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            else:
                # Keep BGR as is
                processed = image.copy()
        except cv2.error as exc:
            raise PreprocessingError(f"Color space conversion failed: {exc}") from exc

        # 2. Resize
        try:
            processed = cv2.resize(
                processed,
                (self.resize_width, self.resize_height),
                interpolation=cv2.INTER_LINEAR,
            )
        except cv2.error as exc:
            raise PreprocessingError(f"Image resize failed: {exc}") from exc

        # 3. Encoding
        if self.encoding == "none":
            return processed

        ext = f".{self.encoding}"
        try:
            success, encoded_img = cv2.imencode(ext, processed)
            if not success:
                raise PreprocessingError(f"Failed to encode image to {self.encoding} format")
            return encoded_img.tobytes()
        except cv2.error as exc:
            raise PreprocessingError(f"Image encoding failed: {exc}") from exc
