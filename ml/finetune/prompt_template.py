"""Training prompt template for supervised fine-tuning (Epic 106 / Story 1036).

Aligns training text with Epic 104 inference prompts in ``litevla.prompting``
so the model sees the same USER / ASSISTANT layout at train and runtime.

Masking contract (applied by the training loop / collator in later stories):
- Train on tokens after ``ASSISTANT:`` (the discrete action target only).
- Mask system, user, and ``<image>`` placeholder tokens.
"""

from __future__ import annotations

from dataclasses import dataclass

from litevla.actions import ACTION_NAMES, is_valid_action
from litevla.prompting import PromptFormatter

ASSISTANT_PREFIX = "ASSISTANT:"
IMAGE_TOKEN = "<image>"


@dataclass(frozen=True)
class TrainingPromptParts:
    """Split prompt / target strings for one supervised example."""

    prompt: str
    """Text up to and including ``ASSISTANT:`` (no action yet)."""

    target: str
    """Discrete action token placed after the assistant prefix."""

    full_text: str
    """Complete training string: ``prompt + " " + target``."""

    prompt_version: str


class TrainingPromptTemplate:
    """Build SFT prompts that match :class:`~litevla.prompting.PromptFormatter`."""

    def __init__(self, version: str = "v1") -> None:
        self.formatter = PromptFormatter(version=version)
        self.version = version

    def build(self, instruction: str, action: str) -> TrainingPromptParts:
        """Format one image-instruction-action example for supervised fine-tuning."""
        token = action.strip().upper()
        if not is_valid_action(token):
            valid = ", ".join(ACTION_NAMES)
            raise ValueError(f"Unknown action {action!r}. Expected one of: {valid}")

        prompt = self.formatter.format_prompt(instruction)
        if not prompt.endswith(ASSISTANT_PREFIX):
            raise ValueError(
                f"Inference prompt must end with {ASSISTANT_PREFIX!r}; got: {prompt[-40:]!r}"
            )
        if IMAGE_TOKEN not in prompt:
            raise ValueError(f"Training prompt must include {IMAGE_TOKEN!r}")

        full_text = f"{prompt} {token}"
        return TrainingPromptParts(
            prompt=prompt,
            target=token,
            full_text=full_text,
            prompt_version=self.version,
        )


def build_training_prompt(
    instruction: str,
    action: str,
    *,
    version: str = "v1",
) -> TrainingPromptParts:
    """Convenience wrapper around :class:`TrainingPromptTemplate.build`."""
    return TrainingPromptTemplate(version=version).build(instruction, action)
