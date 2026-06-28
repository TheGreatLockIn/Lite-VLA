"""Tests for the Lite-VLA baseline evaluation dataset."""

from __future__ import annotations

import json
import os
from pathlib import Path
import cv2
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
EVAL_DIR = REPO_ROOT / "data" / "evaluation"
META_PATH = EVAL_DIR / "metadata.json"


def test_evaluation_metadata_exists_and_is_valid() -> None:
    """Verify that the evaluation metadata.json file exists and is structured correctly."""
    assert META_PATH.is_file(), f"Evaluation metadata file missing: {META_PATH}"

    with open(META_PATH, "r", encoding="utf-8") as f:
        metadata = json.load(f)

    assert isinstance(metadata, list), "Metadata root must be a list of records."
    assert len(metadata) >= 20, f"Expected at least 20 test images, got {len(metadata)}"

    required_keys = {
        "image_id",
        "image_path",
        "instruction",
        "expected_action",
        "source_image",
        "variation_type",
    }

    for idx, entry in enumerate(metadata):
        # Verify keys are present
        assert required_keys.issubset(entry.keys()), (
            f"Entry at index {idx} is missing required fields. "
            f"Found: {list(entry.keys())}"
        )

        # Verify paths and file presence
        rel_path = entry["image_path"]
        abs_path = REPO_ROOT / rel_path
        assert abs_path.is_file(), f"Test image file not found on disk: {abs_path}"

        # Verify image is valid and can be loaded
        img = cv2.imread(str(abs_path))
        assert img is not None, f"Failed to load image at: {abs_path}"
        assert img.ndim == 3 and img.shape[2] == 3, (
            f"Image {rel_path} must be a 3-channel BGR/RGB array, "
            f"got shape {img.shape if img is not None else 'None'}"
        )
