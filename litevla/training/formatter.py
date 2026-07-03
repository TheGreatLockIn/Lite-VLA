"""Formatter to convert VLA demonstration records into tokenized inputs and masked label targets."""

from __future__ import annotations

import logging
from typing import Any

import numpy as np
import torch
from PIL import Image

from litevla.prompting import PROMPT_VERSIONS

logger = logging.getLogger(__name__)


class SFTDataFormatter:
    """Formats raw VLA training records (image, instruction, action) for model SFT training.

    Handles conversational structuring, multimodal prompt generation, tokenization,
    and label masking (setting prompt token labels to -100).
    """

    def __init__(self, processor: Any, prompt_version: str = "v1"):
        """Initialize the SFT data formatter.

        Args:
            processor: Hugging Face processor (e.g. SmolVLM processor).
            prompt_version: Version key from PROMPT_VERSIONS (v1, v2).
        """
        self.processor = processor
        self.prompt_version = prompt_version

        if prompt_version not in PROMPT_VERSIONS:
            supported = list(PROMPT_VERSIONS.keys())
            raise ValueError(
                f"Unsupported prompt version: '{prompt_version}'. Supported: {supported}"
            )
        self.system_instruction = PROMPT_VERSIONS[prompt_version]["system"]
        self.user_template = PROMPT_VERSIONS[prompt_version]["user"]

    def format_conversation(self, instruction: str, action: str) -> list[dict[str, Any]]:
        """Build standard Hugging Face messages structure for the training record.

        Args:
            instruction: Goal text instruction.
            action: Target discrete action string.

        Returns:
            A list of conversation turn dicts matching Hugging Face specifications.
        """
        user_text = self.user_template.format(instruction=instruction)

        # Standard conversational dictionary template format (ChatML style / SmolVLM expected input)
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "image"},
                    {"type": "text", "text": f"{self.system_instruction}\n\n{user_text}"},
                ],
            },
            {
                "role": "assistant",
                "content": [
                    {"type": "text", "text": action},
                ],
            },
        ]
        return messages

    def __call__(self, image: Any, instruction: str, action: str) -> dict[str, torch.Tensor]:
        """Convert a training record into a dict of PyTorch tensors ready for training.

        Args:
            image: OpenCV BGR image array, RGB array, or PIL Image.
            instruction: Goal text command.
            action: Expected discrete action word.

        Returns:
            A dictionary containing:
                - input_ids: Tensor of token ids (seq_len,)
                - labels: Tensor of target action label ids (seq_len,), masked with -100 for the prompt.
                - pixel_values: Preprocessed image tensor/features.
                - pixel_attention_mask: (Optional) Preprocessed image attention mask tensor.
        """
        # 1. Standardize image input to a PIL Image
        if isinstance(image, np.ndarray):
            if len(image.shape) == 3 and image.shape[2] == 3:
                # Convert BGR (OpenCV standard) to RGB for PIL Image conversion
                image = Image.fromarray(image[:, :, ::-1])
            else:
                image = Image.fromarray(image)
        elif not isinstance(image, Image.Image):
            raise TypeError("image must be a PIL Image or a numpy.ndarray")

        # 2. Format conversation dictionaries
        messages = self.format_conversation(instruction, action)

        # 3. Compile prompt text (USER) only using processor's template
        # add_generation_prompt=True appends the assistant starter tag wrapper
        prompt_messages = messages[:1]
        prompt_text = self.processor.apply_chat_template(
            prompt_messages,
            add_generation_prompt=True,
            tokenize=False,
        )

        # 4. Compile full conversation text (USER + ASSISTANT)
        full_text = self.processor.apply_chat_template(
            messages,
            add_generation_prompt=False,
            tokenize=False,
        )

        # 5. Tokenize both sequences using the processor.
        # We pass the same image to both so that image placeholder expansion matches exactly.
        prompt_encoding = self.processor(text=prompt_text, images=image, return_tensors="pt")
        full_encoding = self.processor(text=full_text, images=image, return_tensors="pt")

        prompt_len = prompt_encoding["input_ids"].shape[1]
        full_len = full_encoding["input_ids"].shape[1]

        # Squeeze batch dimension to return 1D sequences
        input_ids = full_encoding["input_ids"].squeeze(0)  # Shape (seq_len,)

        # 6. Construct labels matching input_ids size, masking prompt tokens with -100
        labels = input_ids.clone()
        labels[:prompt_len] = -100

        result = {
            "input_ids": input_ids,
            "labels": labels,
        }

        # 7. Extract vision features generated by the processor
        if "pixel_values" in full_encoding:
            result["pixel_values"] = full_encoding["pixel_values"].squeeze(0)
        if "pixel_attention_mask" in full_encoding:
            result["pixel_attention_mask"] = full_encoding["pixel_attention_mask"].squeeze(0)

        return result
