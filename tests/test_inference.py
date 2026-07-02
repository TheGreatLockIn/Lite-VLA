"""Unit tests for the Lite-VLA Inference Wrapper."""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import cv2
import numpy as np
import pytest

from litevla.config import default_config
from litevla.inference import InferenceWrapper


@pytest.fixture
def dummy_bgr_image() -> np.ndarray:
    """Generate a 3-channel dummy BGR camera frame (100x100)."""
    return np.zeros((100, 100, 3), dtype=np.uint8)


def test_inference_wrapper_dummy_mode_initialization() -> None:
    """Verify that dummy mode initializes quickly and does not load VLM weights."""
    config = default_config()
    config["runtime"]["mode"] = "dummy"

    wrapper = InferenceWrapper(config)
    
    assert wrapper.runtime_mode == "dummy"
    assert wrapper.processor is None
    assert wrapper.model is None
    assert wrapper.device is None
    assert wrapper.torch_dtype is None


@pytest.mark.parametrize(
    "instruction,expected_action",
    [
        ("go forward to the cone", "MOVE_FORWARD"),
        ("please stop now", "STOP"),
        ("turn left", "TURN_LEFT"),
        ("turn right toward the block", "TURN_RIGHT"),
        ("slow down near the gate", "SLOW_DOWN"),
    ],
)
def test_inference_wrapper_dummy_mode_infer(
    dummy_bgr_image: np.ndarray, instruction: str, expected_action: str
) -> None:
    """Verify scripted deterministic outputs and timing values in dummy mode."""
    config = default_config()
    config["runtime"]["mode"] = "dummy"

    wrapper = InferenceWrapper(config)
    result = wrapper.infer(dummy_bgr_image, instruction, few_shot=False)

    assert result["success"] is True
    assert result["error"] is None
    assert result["action"] == expected_action
    
    # Verify timing metrics
    timing = result["timing"]
    for key in ["preprocessing_ms", "prompting_ms", "inference_ms", "total_ms"]:
        assert key in timing
        assert isinstance(timing[key], float)
        assert timing[key] >= 0.0


def test_inference_wrapper_dummy_mode_few_shot(dummy_bgr_image: np.ndarray) -> None:
    """Verify that few-shot preprocessing runs successfully in dummy mode using real files."""
    config = default_config()
    config["runtime"]["mode"] = "dummy"

    wrapper = InferenceWrapper(config)
    result = wrapper.infer(dummy_bgr_image, "go forward", few_shot=True)

    assert result["success"] is True
    assert result["action"] == "MOVE_FORWARD"
    assert result["timing"]["preprocessing_ms"] > 0.0
    assert result["timing"]["prompting_ms"] > 0.0


def test_inference_wrapper_missing_model_path_raises_error() -> None:
    """Verify that initialization raises ValueError if mode is model but model path is empty."""
    config = default_config()
    config["runtime"]["mode"] = "model"
    config["model"]["path"] = ""

    with pytest.raises(ValueError, match="Model path must be specified"):
        InferenceWrapper(config)


@patch("litevla.inference.AutoModelForImageTextToText")
@patch("litevla.inference.AutoProcessor")
def test_inference_wrapper_model_mode_initialization_and_device_routing(
    mock_processor_cls: MagicMock, mock_model_cls: MagicMock
) -> None:
    """Verify correct HuggingFace loading parameters and device placement logic."""
    config = default_config()
    config["runtime"]["mode"] = "model"
    config["model"]["path"] = "mock-vlm-path"
    config["model"]["device"] = "cpu"

    # Set up mocks
    mock_processor = MagicMock()
    mock_model = MagicMock()
    mock_processor_cls.from_pretrained.return_value = mock_processor
    mock_model_cls.from_pretrained.return_value = mock_model
    mock_model.to.return_value = mock_model

    wrapper = InferenceWrapper(config)

    # Verify Hub download calls
    mock_processor_cls.from_pretrained.assert_called_once_with("mock-vlm-path")
    mock_model_cls.from_pretrained.assert_called_once_with(
        "mock-vlm-path", torch_dtype=wrapper.torch_dtype, low_cpu_mem_usage=True
    )
    mock_model.to.assert_called_once_with(wrapper.device)


@patch("litevla.inference.AutoModelForImageTextToText")
@patch("litevla.inference.AutoProcessor")
def test_inference_wrapper_model_inference_execution(
    mock_processor_cls: MagicMock, mock_model_cls: MagicMock, dummy_bgr_image: np.ndarray
) -> None:
    """Verify successful execution flow through processor, model forward pass, and decoder."""
    config = default_config()
    config["runtime"]["mode"] = "model"
    config["model"]["path"] = "mock-vlm-path"
    config["model"]["device"] = "cpu"
    config["model"]["max_tokens"] = 16

    # Mock the processor and model instances
    mock_processor = MagicMock()
    mock_model = MagicMock()
    mock_processor_cls.from_pretrained.return_value = mock_processor
    mock_model_cls.from_pretrained.return_value = mock_model
    mock_model.to.return_value = mock_model

    # Mock tokenization output (input dict)
    mock_inputs = {"input_ids": MagicMock()}
    mock_inputs["input_ids"].shape = (1, 100)  # mock prompt length = 100
    mock_processor.return_value = mock_inputs

    # Mock model generation output
    mock_generated_ids = MagicMock()
    mock_model.generate.return_value = mock_generated_ids
    
    # Mock decoder output
    mock_processor.batch_decode.return_value = ["TURN_LEFT"]

    wrapper = InferenceWrapper(config)
    result = wrapper.infer(dummy_bgr_image, "navigate left", few_shot=False)

    assert result["success"] is True
    assert result["action"] == "TURN_LEFT"
    assert result["timing"]["inference_ms"] > 0.0

    # Ensure processor was called with prompt and image
    mock_processor.assert_called_once()
    args, kwargs = mock_processor.call_args
    assert "text" in kwargs
    assert "images" in kwargs

    # Ensure model.generate was called with max_tokens and greedy decoding parameters
    mock_model.generate.assert_called_once_with(
        **mock_inputs, max_new_tokens=16, do_sample=False
    )


@patch("litevla.inference.AutoModelForImageTextToText")
@patch("litevla.inference.AutoProcessor")
def test_inference_wrapper_error_handling_and_fallback(
    mock_processor_cls: MagicMock, mock_model_cls: MagicMock, dummy_bgr_image: np.ndarray
) -> None:
    """Verify that a model forward crash is caught and returns the safe fallback action STOP."""
    config = default_config()
    config["runtime"]["mode"] = "model"
    config["model"]["path"] = "mock-vlm-path"
    config["model"]["device"] = "cpu"

    # Setup mocks to crash during model forward generation
    mock_processor = MagicMock()
    mock_model = MagicMock()
    mock_processor_cls.from_pretrained.return_value = mock_processor
    mock_model_cls.from_pretrained.return_value = mock_model
    mock_model.to.return_value = mock_model

    mock_inputs = {"input_ids": MagicMock()}
    mock_inputs["input_ids"].shape = (1, 50)
    mock_processor.return_value = mock_inputs

    mock_model.generate.side_effect = RuntimeError("Mock CUDA Out of Memory")

    wrapper = InferenceWrapper(config)
    result = wrapper.infer(dummy_bgr_image, "go forward", few_shot=False)

    # Assert safe recovery boundary
    assert result["success"] is False
    assert result["action"] == "STOP"
    assert "Mock CUDA Out of Memory" in result["error"]
