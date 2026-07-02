"""Tests for Lite-VLA prompting templates and utilities."""

from __future__ import annotations

import pytest
from litevla.prompting import ALLOWED_ACTIONS, PROMPT_VERSIONS, PromptFormatter


def test_allowed_actions_list() -> None:
    """Verify ALLOWED_ACTIONS contains the correct discrete actions in order."""
    expected_actions = ("MOVE_FORWARD", "TURN_LEFT", "TURN_RIGHT", "STOP", "SLOW_DOWN")
    assert ALLOWED_ACTIONS == expected_actions
    assert len(ALLOWED_ACTIONS) == 5


def test_prompt_formatter_invalid_version() -> None:
    """Verify that PromptFormatter raises ValueError for unsupported versions."""
    with pytest.raises(ValueError, match="Unsupported prompt version: 'v3'"):
        PromptFormatter(version="v3")


def test_prompt_formatter_valid_versions() -> None:
    """Verify that PromptFormatter initializes successfully for supported versions."""
    for version in PROMPT_VERSIONS:
        formatter = PromptFormatter(version=version)
        assert formatter.version == version
        assert formatter.system_instruction == PROMPT_VERSIONS[version]["system"]
        assert formatter.user_template == PROMPT_VERSIONS[version]["user"]


def test_format_prompt_structure() -> None:
    """Verify the formatted prompt structure conforms to LLaVA conventions and contains <image>."""
    formatter = PromptFormatter(version="v1")
    instruction = "go forward to the red block"
    prompt = formatter.format_prompt(instruction)

    # LLaVA prompt wrapper check: USER: <image>\n[System]\n\n[User Goal]\nASSISTANT:
    assert prompt.startswith("USER: <image>\n")
    assert prompt.endswith("\nASSISTANT:")
    assert "Goal Instruction: go forward to the red block" in prompt
    assert "<image>" in prompt
    assert prompt.count("<image>") == 1


def test_prompt_v1_constraints() -> None:
    """Verify v1 prompts restrict outputs to exactly the allowed actions list."""
    formatter = PromptFormatter(version="v1")
    instruction = "test instruction"
    prompt = formatter.format_prompt(instruction)

    for action in ALLOWED_ACTIONS:
        assert action in prompt
    assert "exactly one action token" in prompt


def test_prompt_v2_constraints() -> None:
    """Verify v2 prompts restrict outputs and mention Webots/Pioneer constraints."""
    formatter = PromptFormatter(version="v2")
    instruction = "test instruction v2"
    prompt = formatter.format_prompt(instruction)

    for action in ALLOWED_ACTIONS:
        assert action in prompt
    assert "Pioneer 3-DX" in prompt
    assert "Webots simulation" in prompt
    assert "Navigate command: test instruction v2" in prompt


def test_format_few_shot_prompt() -> None:
    """Verify that few-shot prompts compile correctly with multiple images."""
    from litevla.prompting import FEW_SHOT_EXAMPLES

    formatter = PromptFormatter(version="v1")
    query_instr = "navigate to red cylinder"
    prompt, image_paths = formatter.format_few_shot_prompt(query_instr)

    # Output type validation
    assert isinstance(prompt, str)
    assert isinstance(image_paths, list)

    # Number of images in path list and corresponding <image> tokens in prompt
    assert len(image_paths) == len(FEW_SHOT_EXAMPLES)
    assert prompt.count("<image>") == len(FEW_SHOT_EXAMPLES) + 1  # reference images + current frame

    # Correct image order
    for idx, ex in enumerate(FEW_SHOT_EXAMPLES):
        assert image_paths[idx] == ex["image_path"]
        assert ex["action"] in prompt

    # Verify that the system instruction is present only once
    assert prompt.count(formatter.system_instruction) == 1
    # Check that it contains the final query instruction
    assert "navigate to red cylinder" in prompt
    assert prompt.endswith("ASSISTANT:")


def test_format_few_shot_prompt_v2() -> None:
    """Verify few-shot formatting behaves properly with version v2 configuration."""
    formatter = PromptFormatter(version="v2")
    query_instr = "turn around"
    prompt, image_paths = formatter.format_few_shot_prompt(query_instr)

    assert len(image_paths) == 4
    assert prompt.count("<image>") == 5
    assert "Navigate command: turn around" in prompt
    assert "Pioneer 3-DX" in prompt


def test_few_shot_images_exist_and_are_valid() -> None:
    """Verify that all configured few-shot images exist on disk and can be successfully loaded."""
    import os
    import cv2
    from litevla.prompting import FEW_SHOT_EXAMPLES

    assert len(FEW_SHOT_EXAMPLES) > 0, "FEW_SHOT_EXAMPLES should not be empty."

    for ex in FEW_SHOT_EXAMPLES:
        path = ex["image_path"]
        # Ensure file exists
        assert os.path.isfile(path), f"Few-shot image file does not exist: {path}"

        # Ensure it is a valid image loadable by OpenCV
        img = cv2.imread(path)
        assert img is not None, f"Failed to load image at {path}"
        assert img.ndim == 3 and img.shape[2] == 3, f"Image at {path} is not a valid 3-channel image"


