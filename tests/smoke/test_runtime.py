"""Lightweight runtime checks for the base ML and utility stack."""

from __future__ import annotations

import json
from io import StringIO

import jsonschema
import numpy as np
import pytest
import torch
import yaml
from PIL import Image


def test_torch_tensor_ops() -> None:
    tensor = torch.tensor([1.0, 2.0, 3.0])
    assert tensor.shape == (3,)
    assert tensor.sum().item() == pytest.approx(6.0)


def test_torchvision_transforms_import() -> None:
    from torchvision import transforms

    resize = transforms.Resize((64, 64))
    assert resize.size == (64, 64)


def test_yaml_roundtrip() -> None:
    payload = {"model": {"path": "models/demo", "max_tokens": 32}}
    loaded = yaml.safe_load(yaml.safe_dump(payload))
    assert loaded == payload


def test_jsonschema_validates_action_record() -> None:
    schema = {
        "type": "object",
        "properties": {
            "instruction": {"type": "string"},
            "action": {"type": "string"},
        },
        "required": ["instruction", "action"],
    }
    record = {"instruction": "move forward", "action": "MOVE_FORWARD"}
    jsonschema.validate(instance=record, schema=schema)


def test_pillow_image_buffer() -> None:
    image = Image.new("RGB", (128, 96), color=(10, 20, 30))
    assert image.size == (128, 96)
    array = np.asarray(image)
    assert array.shape == (96, 128, 3)


def test_opencv_resize() -> None:
    import cv2

    frame = np.zeros((120, 160, 3), dtype=np.uint8)
    resized = cv2.resize(frame, (64, 48))
    assert resized.shape == (48, 64, 3)


def test_pandas_json_roundtrip() -> None:
    import pandas as pd

    frame = pd.DataFrame([{"instruction": "stop", "action": "STOP"}])
    payload = json.dumps(frame.to_dict(orient="records"))
    restored = pd.read_json(StringIO(payload))
    assert restored.iloc[0]["action"] == "STOP"


def test_transformers_has_core_symbols() -> None:
    import transformers

    assert hasattr(transformers, "AutoProcessor")
    vlm_auto_classes = (
        "AutoModelForVision2Seq",
        "AutoModelForImageTextToText",
    )
    assert any(hasattr(transformers, name) for name in vlm_auto_classes)
