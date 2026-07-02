"""Model-to-action adapter connecting inference wrapper output to parser/safety gate."""

from __future__ import annotations

import logging
from typing import Any

from litevla.actions.safety import safe_command_from_text, SafeCommand
from litevla.inference import InferenceWrapper

logger = logging.getLogger("litevla.actions.adapter")


class InferenceAdapter:
    """Adapts raw vision-language-action wrapper outputs to structured safety commands.

    Wraps the inference wrapper, parses text output using the discrete action parser,
    and applies configuration-specified safety limits to return bounded Twist velocities.
    """

    def __init__(self, wrapper: InferenceWrapper, config: dict):
        """Initialize the adapter with a wrapper instance and configuration."""
        self.wrapper = wrapper
        self.config = config
        
        # Extract safety velocity bounds from config
        safety_cfg = config.get("safety", {})
        self.max_linear_vel = safety_cfg.get("max_linear_vel", 0.5)
        self.max_angular_vel = safety_cfg.get("max_angular_vel", 1.0)

    def adapt_inference(self, image: Any, instruction: str, few_shot: bool = False) -> dict[str, Any]:
        """Perform inference and adapt the output to a safe action command.

        Args:
            image: OpenCV BGR image array (H, W, 3) from the camera loop.
            instruction: Goal text instruction.
            few_shot: Whether to include in-context multi-image few-shot examples.

        Returns:
            A dictionary containing:
                - "safe_command" (SafeCommand): The structured safety gate result.
                - "action" (str): The parsed discrete action string token.
                - "parse_status" (str): Reason/status of parsing (e.g. "ok", "parse_failure").
                - "raw_output" (str): Unparsed raw model text output.
                - "success" (bool): True if inference completed successfully.
                - "timing" (dict): Latency timings passed from the inference wrapper.
                - "error" (str or None): Error message if inference failed.
        """
        # 1. Run model inference
        infer_res = self.wrapper.infer(image, instruction, few_shot=few_shot)
        raw_text = infer_res["action"]

        # 2. Process through parser and safety gate
        safe_cmd = safe_command_from_text(
            raw_text,
            max_linear_vel=self.max_linear_vel,
            max_angular_vel=self.max_angular_vel,
            logger=logger,
        )

        # 3. Log raw and parsed output for debugging (Subtask 10086)
        logger.info(
            f"Adapter run: raw_output='{raw_text}', "
            f"parsed_action='{safe_cmd.action.value}'"
        )

        return {
            "safe_command": safe_cmd,
            "action": safe_cmd.action.value,
            "parse_status": safe_cmd.events[0].kind.value,
            "raw_output": raw_text,
            "success": infer_res["success"],
            "timing": infer_res["timing"],
            "error": infer_res["error"],
        }
