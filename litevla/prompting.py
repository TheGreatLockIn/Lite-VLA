"""Lite-VLA Prompting Templates and Utilities."""

from __future__ import annotations

# The exact list of allowed discrete action tokens.
ALLOWED_ACTIONS = ("MOVE_FORWARD", "TURN_LEFT", "TURN_RIGHT", "STOP", "SLOW_DOWN")

# Few-shot navigation examples mapping visual state, instruction, and correct action.
FEW_SHOT_EXAMPLES: list[dict[str, str]] = [
    {
        "image_path": "data/examples/red_cone_centered.png",
        "instruction": "go to the red block",
        "action": "MOVE_FORWARD",
    },
    {
        "image_path": "data/examples/red_cone_left.png",
        "instruction": "go to the red block",
        "action": "TURN_LEFT",
    },
    {
        "image_path": "data/examples/red_cone_right.png",
        "instruction": "go to the red block",
        "action": "TURN_RIGHT",
    },
    {
        "image_path": "data/examples/stop_barrier_close.png",
        "instruction": "go to the red block",
        "action": "STOP",
    },
]

PROMPT_VERSIONS: dict[str, dict[str, str]] = {
    "v1": {
        "system": (
            "You are an autonomous mobile robot navigator. "
            "Analyze the visual frame and goal instruction, then select the single best action "
            "from the following allowed list:\n"
            f"Allowed Actions: {', '.join(ALLOWED_ACTIONS)}\n\n"
            "Respond with exactly one action token from the allowed list "
            "and absolutely nothing else. "
            "Do not include explanation, punctuation, or conversational text."
        ),
        "user": "Goal Instruction: {instruction}",
    },
    "v2": {
        "system": (
            "You are a Pioneer 3-DX wheeled mobile robot navigating "
            "a Webots simulation arena. "
            "Your front camera is active. You must navigate toward the "
            "target object and stop in front of it. "
            "Select the single best action from the allowed list:\n"
            f"Allowed Actions: {', '.join(ALLOWED_ACTIONS)}\n\n"
            "Constraints:\n"
            "- Output exactly one word from the allowed actions list.\n"
            "- Do not output markdown, formatting, quotes, or punctuation.\n"
            "- Do not output explainers, reasoning, or other text.\n"
            "- If target object is visible and close, output 'STOP'.\n"
            "- If target is centered, output 'MOVE_FORWARD'.\n"
            "- If target is to the left, output 'TURN_LEFT'.\n"
            "- If target is to the right, output 'TURN_RIGHT'."
        ),
        "user": "Navigate command: {instruction}",
    },
}


class PromptFormatter:
    """Formats system instructions and user goals into the standard LLaVA prompt structure."""

    def __init__(self, version: str = "v1"):
        """Initialize the formatter using a specific version key from PROMPT_VERSIONS."""
        if version not in PROMPT_VERSIONS:
            supported = list(PROMPT_VERSIONS.keys())
            raise ValueError(
                f"Unsupported prompt version: '{version}'. Supported: {supported}"
            )
        self.version = version
        self.system_instruction = PROMPT_VERSIONS[version]["system"]
        self.user_template = PROMPT_VERSIONS[version]["user"]

    def format_prompt(self, instruction: str) -> str:
        """Format the system instruction and user goal command into the final prompt string."""
        goal_text = self.user_template.format(instruction=instruction)
        # Standard LLaVA-1.5 prompt wrapper format: USER: <image>\n[Prompt]\nASSISTANT:
        # Note: <image> token tells llama.cpp where to project the image embeddings.
        return f"USER: <image>\n{self.system_instruction}\n\n{goal_text}\nASSISTANT:"

    def format_few_shot_prompt(self, instruction: str) -> tuple[str, list[str]]:
        """Format the system instruction, few-shot examples, and user goal into the final prompt.

        Returns:
            A tuple of (prompt_string, list_of_image_paths).
        """
        parts = []
        image_paths = []

        if FEW_SHOT_EXAMPLES:
            # Format the first few-shot example with the system instructions included
            first_ex = FEW_SHOT_EXAMPLES[0]
            first_user_text = self.user_template.format(instruction=first_ex["instruction"])
            parts.append(
                f"USER: <image>\n{self.system_instruction}\n\n{first_user_text}\n"
                f"ASSISTANT: {first_ex['action']}"
            )
            image_paths.append(first_ex["image_path"])

            # Format the remaining few-shot examples without repeating system instructions
            for ex in FEW_SHOT_EXAMPLES[1:]:
                user_text = self.user_template.format(instruction=ex["instruction"])
                parts.append(
                    f"USER: <image>\n{user_text}\n"
                    f"ASSISTANT: {ex['action']}"
                )
                image_paths.append(ex["image_path"])

        # Format the final user query (does not have an assistant action yet)
        query_user_text = self.user_template.format(instruction=instruction)
        parts.append(f"USER: <image>\n{query_user_text}\nASSISTANT:")

        prompt_str = "\n".join(parts)
        return prompt_str, image_paths

