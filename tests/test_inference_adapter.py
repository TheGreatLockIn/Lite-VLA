"""Unit tests for the InferenceAdapter connecting model output to safety gate."""

from __future__ import annotations

import logging
from unittest.mock import MagicMock, patch

import pytest
import numpy as np

from litevla.actions import DiscreteAction, InferenceAdapter, SafeCommand
from litevla.inference import InferenceWrapper


@pytest.fixture
def dummy_config() -> dict:
    return {
        "runtime": {"mode": "dummy"},
        "safety": {"max_linear_vel": 0.5, "max_angular_vel": 1.0},
    }


@pytest.fixture
def mock_wrapper() -> MagicMock:
    wrapper = MagicMock(spec=InferenceWrapper)
    # Default mock output
    wrapper.infer.return_value = {
        "action": "MOVE_FORWARD",
        "timing": {
            "preprocessing_ms": 1.0,
            "prompting_ms": 2.0,
            "inference_ms": 5.0,
            "total_ms": 8.0,
        },
        "success": True,
        "error": None,
    }
    return wrapper


def test_adapter_initialization(dummy_config, mock_wrapper) -> None:
    adapter = InferenceAdapter(mock_wrapper, dummy_config)
    assert adapter.max_linear_vel == 0.5
    assert adapter.max_angular_vel == 1.0


def test_adapter_valid_action_parsing(dummy_config, mock_wrapper) -> None:
    adapter = InferenceAdapter(mock_wrapper, dummy_config)
    image = np.zeros((100, 100, 3), dtype=np.uint8)
    
    res = adapter.adapt_inference(image, "go forward")
    
    assert res["success"] is True
    assert res["action"] == "MOVE_FORWARD"
    assert res["parse_status"] == "ok"
    assert res["raw_output"] == "MOVE_FORWARD"
    
    cmd = res["safe_command"]
    assert isinstance(cmd, SafeCommand)
    assert cmd.action == DiscreteAction.MOVE_FORWARD
    assert cmd.linear_x == pytest.approx(0.2)
    assert cmd.angular_z == pytest.approx(0.0)


def test_adapter_noisy_action_parsing(dummy_config, mock_wrapper) -> None:
    # Set wrapper to return noisy string
    mock_wrapper.infer.return_value["action"] = "turn_left. "
    adapter = InferenceAdapter(mock_wrapper, dummy_config)
    image = np.zeros((100, 100, 3), dtype=np.uint8)
    
    res = adapter.adapt_inference(image, "turn left")
    
    assert res["success"] is True
    assert res["action"] == "TURN_LEFT"
    assert res["parse_status"] == "ok"
    assert res["raw_output"] == "turn_left. "
    
    cmd = res["safe_command"]
    assert cmd.action == DiscreteAction.TURN_LEFT
    assert cmd.linear_x == pytest.approx(0.0)
    assert cmd.angular_z == pytest.approx(0.6)


def test_adapter_fallback_on_invalid_output(dummy_config, mock_wrapper) -> None:
    # Set wrapper to return invalid text token (Subtask 10085)
    mock_wrapper.infer.return_value["action"] = "GO_FAST"
    adapter = InferenceAdapter(mock_wrapper, dummy_config)
    image = np.zeros((100, 100, 3), dtype=np.uint8)
    
    res = adapter.adapt_inference(image, "go fast")
    
    assert res["success"] is True
    assert res["action"] == "STOP"
    assert res["parse_status"] == "parse_failure"
    assert res["raw_output"] == "GO_FAST"
    
    cmd = res["safe_command"]
    assert cmd.action == DiscreteAction.STOP
    assert cmd.linear_x == pytest.approx(0.0)
    assert cmd.angular_z == pytest.approx(0.0)


def test_adapter_exception_fallback(dummy_config, mock_wrapper) -> None:
    # Set wrapper to return unsuccessful run (Subtask 10085)
    mock_wrapper.infer.return_value = {
        "action": "STOP",
        "timing": {"preprocessing_ms": 0.0, "prompting_ms": 0.0, "inference_ms": 0.0, "total_ms": 1.0},
        "success": False,
        "error": "CUDA OOM",
    }
    adapter = InferenceAdapter(mock_wrapper, dummy_config)
    image = np.zeros((100, 100, 3), dtype=np.uint8)
    
    res = adapter.adapt_inference(image, "move left")
    
    assert res["success"] is False
    assert res["action"] == "STOP"
    assert res["parse_status"] == "ok"  # "STOP" resolves to OK
    assert res["raw_output"] == "STOP"
    assert res["error"] == "CUDA OOM"
    
    cmd = res["safe_command"]
    assert cmd.action == DiscreteAction.STOP


def test_adapter_logging_contains_required_fields(dummy_config, mock_wrapper) -> None:
    mock_wrapper.infer.return_value["action"] = "MOVE_FORWARD"
    adapter = InferenceAdapter(mock_wrapper, dummy_config)
    image = np.zeros((100, 100, 3), dtype=np.uint8)
    
    # Subtask 10086: Save both raw text and parsed action for debugging, log must contain raw_output and parsed_action fields
    with patch("litevla.actions.adapter.logger") as mock_logger:
        adapter.adapt_inference(image, "go forward")
        
        # Verify info log is called with raw_output and parsed_action strings
        mock_logger.info.assert_called_once()
        log_msg = mock_logger.info.call_args[0][0]
        assert "raw_output=" in log_msg
        assert "parsed_action=" in log_msg
        assert "MOVE_FORWARD" in log_msg
