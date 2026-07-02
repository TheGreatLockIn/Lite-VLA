"""Lite-VLA Inference Wrapper."""

from __future__ import annotations

import io
import logging
import time
import traceback
from pathlib import Path
from typing import Any

import cv2
import numpy as np
import torch
from PIL import Image
from transformers import AutoProcessor, AutoModelForImageTextToText

from litevla.preprocessing import ImagePreprocessor
from litevla.prompting import PromptFormatter

logger = logging.getLogger("litevla.inference")


class InferenceWrapper:
    """Wraps the VLM for robot control inference.

    Handles model weight loading, preprocessing inputs, generating predictions,
    timing execution latencies, and catching execution failures cleanly.
    """

    def __init__(self, config: dict):
        """Initialize the wrapper with the configuration dictionary."""
        self.config = config
        self.runtime_mode = config.get("runtime", {}).get("mode", "dummy")

        # Load preprocessor and prompting helper
        self.preprocessor = ImagePreprocessor(config)
        
        prompt_version = config.get("model", {}).get("prompt_version", "v1")
        self.prompt_formatter = PromptFormatter(version=prompt_version)

        # Initialize model variables
        self.device = None
        self.torch_dtype = None
        self.processor = None
        self.model = None

        if self.runtime_mode == "model":
            model_path = config.get("model", {}).get("path", "")
            device_name = config.get("model", {}).get("device", "cpu")

            if not model_path:
                raise ValueError("Model path must be specified when runtime mode is 'model'.")

            # Determine device and torch_dtype
            if device_name == "cuda" and torch.cuda.is_available():
                self.device = torch.device("cuda")
                self.torch_dtype = torch.bfloat16
            elif device_name == "mps" and torch.backends.mps.is_available():
                self.device = torch.device("mps")
                self.torch_dtype = torch.float32  # MPS often prefers float32
            else:
                self.device = torch.device("cpu")
                self.torch_dtype = torch.float32

            logger.info(
                f"Loading model '{model_path}' on device '{self.device}' with dtype '{self.torch_dtype}'..."
            )
            
            self.processor = AutoProcessor.from_pretrained(model_path)
            self.model = AutoModelForImageTextToText.from_pretrained(
                model_path,
                torch_dtype=self.torch_dtype,
                low_cpu_mem_usage=True
            ).to(self.device)
            
            logger.info("Model loaded successfully.")
        else:
            logger.info("Initializing in 'dummy' mode. Model weights will not be loaded.")

    def infer(self, image: np.ndarray, instruction: str, few_shot: bool = False) -> dict[str, Any]:
        """Perform visual-language-action inference on a camera image and goal instruction.

        Args:
            image: OpenCV BGR image array (H, W, 3) from the camera loop.
            instruction: Goal text instruction.
            few_shot: Whether to include in-context multi-image few-shot examples.

        Returns:
            A dictionary containing:
                - "action" (str): Predicted action token (or "STOP" fallback on error).
                - "timing" (dict): Latencies in milliseconds (preprocessing, prompting, inference, total).
                - "success" (bool): True if model executed successfully, False otherwise.
                - "error" (str or None): Error message if success is False.
        """
        start_total = time.perf_counter()
        
        preproc_ms = 0.0
        prompting_ms = 0.0
        inference_ms = 0.0

        try:
            # 1. Preprocess the live query image
            start_preproc = time.perf_counter()
            processed_query = self.preprocessor.preprocess(image)
            
            if isinstance(processed_query, bytes):
                query_pil = Image.open(io.BytesIO(processed_query))
            else:
                query_pil = Image.fromarray(processed_query)
            preproc_ms = (time.perf_counter() - start_preproc) * 1000.0

            # 2. Format the prompt and images list
            start_prompt = time.perf_counter()
            if few_shot:
                prompt_str, image_paths = self.prompt_formatter.format_few_shot_prompt(instruction)
                images_list = []
                for path in image_paths:
                    ref_bgr = cv2.imread(path)
                    if ref_bgr is None:
                        raise FileNotFoundError(f"Few-shot image path not found: {path}")
                    ref_processed = self.preprocessor.preprocess(ref_bgr)
                    if isinstance(ref_processed, bytes):
                        ref_pil = Image.open(io.BytesIO(ref_processed))
                    else:
                        ref_pil = Image.fromarray(ref_processed)
                    images_list.append(ref_pil)
                images_list.append(query_pil)
            else:
                prompt_str = self.prompt_formatter.format_prompt(instruction)
                images_list = query_pil
            prompting_ms = (time.perf_counter() - start_prompt) * 1000.0

            # 3. Model Inference execution
            if self.runtime_mode == "dummy":
                # Simulated dummy logic
                time.sleep(0.005)  # 5ms mock computation delay
                inference_ms = 5.0
                # Scripted deterministic mock outputs
                instruction_lower = instruction.lower()
                if "stop" in instruction_lower:
                    action = "STOP"
                elif "left" in instruction_lower:
                    action = "TURN_LEFT"
                elif "right" in instruction_lower:
                    action = "TURN_RIGHT"
                elif "slow" in instruction_lower:
                    action = "SLOW_DOWN"
                else:
                    action = "MOVE_FORWARD"
            else:
                start_infer = time.perf_counter()
                
                # Tokenize text and prepare visual features
                inputs = self.processor(
                    text=prompt_str,
                    images=images_list,
                    return_tensors="pt"
                )
                
                # Move tensors to target device (handles both BatchEncoding and test dict mocks)
                if hasattr(inputs, "to"):
                    inputs = inputs.to(self.device)
                else:
                    inputs = {
                        k: v.to(self.device) if isinstance(v, torch.Tensor) else v
                        for k, v in inputs.items()
                    }

                # Generate output tokens
                max_new_tokens = self.config.get("model", {}).get("max_tokens", 32)
                generated_ids = self.model.generate(
                    **inputs,
                    max_new_tokens=max_new_tokens,
                    do_sample=False  # Greedy decoding for deterministic actions
                )

                # Decode the response (exclude the input prompt tokens)
                input_len = inputs["input_ids"].shape[1]
                action = self.processor.batch_decode(
                    generated_ids[:, input_len:],
                    skip_special_tokens=True
                )[0].strip()
                
                inference_ms = (time.perf_counter() - start_infer) * 1000.0

            total_ms = (time.perf_counter() - start_total) * 1000.0
            return {
                "action": action,
                "timing": {
                    "preprocessing_ms": preproc_ms,
                    "prompting_ms": prompting_ms,
                    "inference_ms": inference_ms,
                    "total_ms": total_ms,
                },
                "success": True,
                "error": None,
            }

        except Exception as exc:
            logger.error(f"Inference failed with error: {exc}\n{traceback.format_exc()}")
            total_ms = (time.perf_counter() - start_total) * 1000.0
            return {
                "action": "STOP",  # Safe fallback action token
                "timing": {
                    "preprocessing_ms": preproc_ms,
                    "prompting_ms": prompting_ms,
                    "inference_ms": inference_ms,
                    "total_ms": total_ms,
                },
                "success": False,
                "error": str(exc),
            }
