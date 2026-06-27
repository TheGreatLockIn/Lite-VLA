"""Tests for Lite-VLA image preprocessing pipeline."""

from __future__ import annotations

import cv2
import numpy as np
import pytest
from litevla.preprocessing import ImagePreprocessor, PreprocessingError


@pytest.fixture
def dummy_bgr_image() -> np.ndarray:
    """Generate a dummy 3-channel BGR image array (640x480)."""
    # Create an image where the top half is solid Blue and bottom half is Red
    img = np.zeros((480, 640, 3), dtype=np.uint8)
    img[0:240, :, 0] = 255  # Blue channel in BGR
    img[240:, :, 2] = 255  # Red channel in BGR
    return img


def test_preprocessor_init_with_defaults() -> None:
    # Init preprocessor with an empty config dictionary (uses fallbacks)
    preprocessor = ImagePreprocessor({})
    assert preprocessor.resize_width == 512
    assert preprocessor.resize_height == 512
    assert preprocessor.color_format == "rgb"
    assert preprocessor.encoding == "jpeg"


def test_preprocessor_init_invalid_configs() -> None:
    with pytest.raises(PreprocessingError, match="Invalid resize dimensions"):
        ImagePreprocessor({"preprocessing": {"resize_width": -1, "resize_height": 512}})

    with pytest.raises(PreprocessingError, match="Unsupported color format"):
        ImagePreprocessor({"preprocessing": {"color_format": "hsv"}})

    with pytest.raises(PreprocessingError, match="Unsupported encoding"):
        ImagePreprocessor({"preprocessing": {"encoding": "gif"}})


def test_preprocessing_resize_and_color_rgb(dummy_bgr_image) -> None:
    config = {
        "preprocessing": {
            "resize_width": 224,
            "resize_height": 224,
            "color_format": "rgb",
            "encoding": "none",
        }
    }
    preprocessor = ImagePreprocessor(config)
    processed = preprocessor.preprocess(dummy_bgr_image)

    assert isinstance(processed, np.ndarray)
    assert processed.shape == (224, 224, 3)

    # Check color channels swapped correctly (BGR -> RGB)
    # The top half was BGR (255, 0, 0) -> RGB should be (0, 0, 255)
    # The bottom half was BGR (0, 0, 255) -> RGB should be (255, 0, 0)
    assert processed[50, 100, 2] == 255  # Blue channel now in index 2 (R, G, B)
    assert processed[50, 100, 0] == 0
    assert processed[150, 100, 0] == 255  # Red channel now in index 0 (R, G, B)
    assert processed[150, 100, 2] == 0


def test_preprocessing_gray(dummy_bgr_image) -> None:
    config = {
        "preprocessing": {
            "resize_width": 224,
            "resize_height": 224,
            "color_format": "gray",
            "encoding": "none",
        }
    }
    preprocessor = ImagePreprocessor(config)
    processed = preprocessor.preprocess(dummy_bgr_image)

    assert isinstance(processed, np.ndarray)
    assert processed.shape == (224, 224)  # 2D array for grayscale


def test_preprocessing_encoding_jpeg(dummy_bgr_image) -> None:
    config = {
        "preprocessing": {
            "resize_width": 128,
            "resize_height": 128,
            "color_format": "rgb",
            "encoding": "jpeg",
        }
    }
    preprocessor = ImagePreprocessor(config)
    processed = preprocessor.preprocess(dummy_bgr_image)

    assert isinstance(processed, bytes)
    # Decode to verify it's a valid JPEG image
    decoded = cv2.imdecode(np.frombuffer(processed, dtype=np.uint8), cv2.IMREAD_COLOR)
    assert decoded is not None
    assert decoded.shape == (128, 128, 3)


def test_preprocessing_input_validation() -> None:
    preprocessor = ImagePreprocessor({})

    # Invalid type
    with pytest.raises(PreprocessingError, match="must be a numpy ndarray"):
        preprocessor.preprocess("not_an_image")  # type: ignore

    # Invalid dimensions (2D grayscale not allowed as input, BGR raw expected)
    invalid_image = np.zeros((100, 100), dtype=np.uint8)
    with pytest.raises(PreprocessingError, match="must be a 3-channel"):
        preprocessor.preprocess(invalid_image)
