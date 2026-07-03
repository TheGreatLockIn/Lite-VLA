"""Unit tests for the supervised fine-tuning training formatter (SFTDataFormatter)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import numpy as np
import pytest
import torch
from PIL import Image

from litevla.training import SFTDataFormatter


@pytest.fixture
def mock_processor() -> MagicMock:
    """Mock Hugging Face AutoProcessor to bypass weight loading."""
    processor = MagicMock()
    
    # Mock apply_chat_template to return strings
    def mock_apply_chat_template(messages, add_generation_prompt=False, tokenize=False):
        if add_generation_prompt:
            return "USER: <image> Go forward. ASSISTANT:"
        return "USER: <image> Go forward. ASSISTANT: MOVE_FORWARD"

    processor.apply_chat_template.side_effect = mock_apply_chat_template
    
    # Mock processor call to return tokenized encodings
    def mock_processor_call(text, images, return_tensors="pt"):
        mock_encoding = MagicMock()
        if "MOVE_FORWARD" in text:
            # Full sequence has 7 tokens
            input_ids = torch.tensor([[1002, 3811, 492, 18, 93, 2409, 2]], dtype=torch.long)
        else:
            # Prompt sequence has 5 tokens
            input_ids = torch.tensor([[1002, 3811, 492, 18, 93]], dtype=torch.long)
            
        mock_encoding.__getitem__.side_effect = lambda k: {
            "input_ids": input_ids,
            "pixel_values": torch.zeros((1, 3, 224, 224), dtype=torch.float32),
        }[k]
        
        # Supporting 'in' checks
        mock_encoding.__contains__.side_effect = lambda k: k in ["input_ids", "pixel_values"]
        
        return mock_encoding

    processor.side_effect = mock_processor_call
    return processor


def test_formatter_initialization(mock_processor) -> None:
    """Verify correct initialization and parameter validation."""
    formatter = SFTDataFormatter(mock_processor, prompt_version="v1")
    assert formatter.processor == mock_processor
    assert formatter.prompt_version == "v1"

    with pytest.raises(ValueError, match="Unsupported prompt version"):
        SFTDataFormatter(mock_processor, prompt_version="v_invalid")


def test_formatter_conversation_structure(mock_processor) -> None:
    """Verify that format_conversation produces standard messages dict structures."""
    formatter = SFTDataFormatter(mock_processor, prompt_version="v1")
    messages = formatter.format_conversation("go to red block", "MOVE_FORWARD")

    assert len(messages) == 2
    assert messages[0]["role"] == "user"
    assert messages[0]["content"][0]["type"] == "image"
    assert "Allowed Actions" in messages[0]["content"][1]["text"]
    assert "go to red block" in messages[0]["content"][1]["text"]

    assert messages[1]["role"] == "assistant"
    assert messages[1]["content"][0]["text"] == "MOVE_FORWARD"


def test_formatter_image_standardization(mock_processor) -> None:
    """Verify that different input image types (PIL, BGR/RGB numpy) are processed safely."""
    formatter = SFTDataFormatter(mock_processor, prompt_version="v1")
    
    # 1. PIL Image input
    pil_image = Image.new("RGB", (100, 100))
    res_pil = formatter(pil_image, "go", "MOVE_FORWARD")
    assert isinstance(res_pil["input_ids"], torch.Tensor)

    # 2. Numpy BGR array (OpenCV standard)
    bgr_array = np.zeros((100, 100, 3), dtype=np.uint8)
    res_bgr = formatter(bgr_array, "go", "MOVE_FORWARD")
    assert isinstance(res_bgr["input_ids"], torch.Tensor)

    # 3. Invalid type raising TypeError
    with pytest.raises(TypeError, match="image must be a PIL Image"):
        formatter("not-an-image", "go", "MOVE_FORWARD")


def test_formatter_label_masking(mock_processor) -> None:
    """Verify that prompt tokens are masked with -100 while target action labels remain intact."""
    formatter = SFTDataFormatter(mock_processor, prompt_version="v1")
    pil_image = Image.new("RGB", (100, 100))
    
    res = formatter(pil_image, "go forward", "MOVE_FORWARD")
    
    input_ids = res["input_ids"]
    labels = res["labels"]

    # Verify matching shapes
    assert input_ids.shape == labels.shape
    assert input_ids.shape == (7,)

    # First N (5) tokens of labels should be masked to -100 (prompt text)
    assert torch.equal(labels[:5], torch.tensor([-100, -100, -100, -100, -100], dtype=torch.long))

    # Remaining M-N (2) tokens must match input_ids exactly (target action + EOS)
    assert torch.equal(labels[5:], input_ids[5:])
    assert labels[5].item() == 2409
    assert labels[6].item() == 2
