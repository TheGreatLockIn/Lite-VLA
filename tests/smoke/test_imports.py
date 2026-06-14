"""Verify core Python packages import successfully (requirements/base.txt)."""

from __future__ import annotations

import importlib

import pytest

BASE_MODULES = [
    "torch",
    "torchvision",
    "transformers",
    "accelerate",
    "huggingface_hub",
    "PIL",
    "numpy",
    "cv2",
    "yaml",
    "jsonschema",
    "tqdm",
    "pandas",
]

OPTIONAL_MODULES = {
    "train": ["peft", "datasets", "sklearn"],
    "deploy": ["bitsandbytes", "onnxruntime"],
}


@pytest.mark.parametrize("module_name", BASE_MODULES)
def test_import_base_module(module_name: str) -> None:
    module = importlib.import_module(module_name)
    assert module is not None


@pytest.mark.optional
@pytest.mark.parametrize(
    "module_name",
    OPTIONAL_MODULES["train"] + OPTIONAL_MODULES["deploy"],
)
def test_import_optional_module(module_name: str) -> None:
    pytest.importorskip(module_name)
    module = importlib.import_module(module_name)
    assert module is not None
