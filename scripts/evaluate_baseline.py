"""Evaluate the baseline VLA model on the generated test set."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

import cv2
import numpy as np

# Adjust path to import package
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from litevla.config import ConfigError, load_config
from litevla.actions import InferenceAdapter
from litevla.inference import InferenceWrapper
from litevla.prompting import ALLOWED_ACTIONS

DEFAULT_META_PATH = ROOT / "data" / "evaluation" / "metadata.json"
DEFAULT_OUTPUT_PATH = ROOT / "data" / "evaluation" / "results.json"


def evaluate_baseline(
    config_path: Path | None = None,
    metadata_path: Path = DEFAULT_META_PATH,
    output_path: Path = DEFAULT_OUTPUT_PATH,
    few_shot: bool = False,
) -> int:
    """Run VLA baseline evaluation loop."""
    print("Initializing evaluation wrapper...")
    try:
        config = load_config(config_path)
    except ConfigError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 1

    wrapper = InferenceWrapper(config)
    adapter = InferenceAdapter(wrapper, config)

    if not metadata_path.is_file():
        print(f"Error: Evaluation dataset metadata file not found at {metadata_path}", file=sys.stderr)
        print("Please run scripts/generate_test_set.py first to compile the dataset.", file=sys.stderr)
        return 1

    with open(metadata_path, "r", encoding="utf-8") as f:
        metadata = json.load(f)

    print(f"Loaded {len(metadata)} evaluation records.")
    print(f"Mode: {config['runtime']['mode']} | Few-Shot: {few_shot}")
    print("Running inference evaluations...")

    runs = []
    valid_action_count = 0
    correct_action_count = 0

    preproc_latencies = []
    prompting_latencies = []
    inference_latencies = []
    total_latencies = []

    for i, record in enumerate(metadata):
        img_id = record["image_id"]
        rel_path = record["image_path"]
        instruction = record["instruction"]
        expected = record["expected_action"]
        var_type = record["variation_type"]
        src_img = record["source_image"]

        abs_path = ROOT / rel_path
        image = cv2.imread(str(abs_path))
        if image is None:
            print(f"Error: Failed to load image at {abs_path}", file=sys.stderr)
            continue

        # Perform VLA inference
        res = adapter.adapt_inference(image, instruction, few_shot=few_shot)
        predicted = res["action"]
        success = res["success"]
        error_msg = res["error"]
        timing = res["timing"]

        # Parse validity and correctness
        is_valid = predicted in ALLOWED_ACTIONS
        is_correct = predicted == expected

        if is_valid:
            valid_action_count += 1
        if is_correct:
            correct_action_count += 1

        # Track latencies
        preproc_latencies.append(timing["preprocessing_ms"])
        prompting_latencies.append(timing["prompting_ms"])
        inference_latencies.append(timing["inference_ms"])
        total_latencies.append(timing["total_ms"])

        runs.append({
            "image_id": img_id,
            "image_path": rel_path,
            "instruction": instruction,
            "expected_action": expected,
            "predicted_action": predicted,
            "is_valid_token": is_valid,
            "is_correct_action": is_correct,
            "source_image": src_img,
            "variation_type": var_type,
            "success": success,
            "error": error_msg,
            "timing_ms": timing,
        })

        print(
            f"[{i+1:02d}/{len(metadata):02d}] id={img_id} expected={expected:12s} "
            f"predicted={predicted:12s} success={str(success):5s} valid={str(is_valid):5s} correct={str(is_correct):5s}"
        )

    # Compute summary stats
    total = len(runs)
    valid_rate = (valid_action_count / total) if total > 0 else 0.0
    correct_rate = (correct_action_count / total) if total > 0 else 0.0

    stats = {
        "evaluation_timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "runtime_mode": config["runtime"]["mode"],
        "model_path": config["model"]["path"],
        "device": config["model"]["device"],
        "few_shot": few_shot,
        "total_evaluated": total,
        "valid_action_count": valid_action_count,
        "correct_action_count": correct_action_count,
        "valid_action_rate": valid_rate,
        "correct_action_rate": correct_rate,
        "averages_ms": {
            "preprocessing_ms": float(np.mean(preproc_latencies)) if preproc_latencies else 0.0,
            "prompting_ms": float(np.mean(prompting_latencies)) if prompting_latencies else 0.0,
            "inference_ms": float(np.mean(inference_latencies)) if inference_latencies else 0.0,
            "total_ms": float(np.mean(total_latencies)) if total_latencies else 0.0,
        }
    }

    report = {
        "summary": stats,
        "runs": runs,
    }

    # Save report JSON
    os.makedirs(output_path.parent, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print()
    print("=================== EVALUATION SUMMARY ===================")
    print(f"  Runtime Mode:           {stats['runtime_mode']}")
    print(f"  Total Evaluated:        {stats['total_evaluated']}")
    print(f"  Valid Action Rate:      {stats['valid_action_rate'] * 100:.1f}% ({valid_action_count}/{total})")
    print(f"  Correct Action Rate:    {stats['correct_action_rate'] * 100:.1f}% ({correct_action_count}/{total})")
    print("  Average Latency:")
    print(f"    Preprocessing:        {stats['averages_ms']['preprocessing_ms']:.2f} ms")
    print(f"    Prompting:            {stats['averages_ms']['prompting_ms']:.2f} ms")
    print(f"    Model Inference:      {stats['averages_ms']['inference_ms']:.2f} ms")
    print(f"    Total Pipeline:       {stats['averages_ms']['total_ms']:.2f} ms")
    print("==========================================================")
    print(f"Results saved to {output_path}")
    
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help="Path to YAML or JSON config (default: configs/default.example.yaml)",
    )
    parser.add_argument(
        "--metadata",
        type=Path,
        default=DEFAULT_META_PATH,
        help="Path to metadata.json dataset (default: data/evaluation/metadata.json)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help="Path to save evaluation results (default: data/evaluation/results.json)",
    )
    parser.add_argument(
        "--few-shot",
        action="store_true",
        help="Perform multi-image few-shot evaluation",
    )
    args = parser.parse_args()
    return evaluate_baseline(args.config, args.metadata, args.output, args.few_shot)


if __name__ == "__main__":
    sys.exit(main())
