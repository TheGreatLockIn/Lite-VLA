"""Tests for the Lite-VLA baseline evaluation runner script."""

from __future__ import annotations

import json
from pathlib import Path
import pytest

from scripts.evaluate_baseline import evaluate_baseline

REPO_ROOT = Path(__file__).resolve().parent.parent
META_PATH = REPO_ROOT / "data" / "evaluation" / "metadata.json"
RESULTS_PATH = REPO_ROOT / "data" / "evaluation" / "results.json"


def test_evaluation_runner_dummy_mode(tmp_path: Path) -> None:
    """Verify that the evaluation runner script executes cleanly in dummy mode and saves output."""
    # Define a temporary results path to avoid overwriting default evaluations
    temp_results_path = tmp_path / "results_temp.json"

    # Run the evaluation loop in dummy mode
    exit_code = evaluate_baseline(
        config_path=None,  # default configs (uses dummy mode)
        metadata_path=META_PATH,
        output_path=temp_results_path,
        few_shot=False,
    )

    # Assert success exit code
    assert exit_code == 0

    # Assert output JSON file was created
    assert temp_results_path.is_file(), f"Evaluation output results file was not created: {temp_results_path}"

    # Load and parse output
    with open(temp_results_path, "r", encoding="utf-8") as f:
        report = json.load(f)

    # Validate output structure
    assert "summary" in report
    assert "runs" in report

    summary = report["summary"]
    runs = report["runs"]

    # Verify summary metrics
    assert summary["runtime_mode"] == "dummy"
    assert summary["total_evaluated"] == len(runs)
    assert summary["total_evaluated"] == 20
    assert summary["valid_action_rate"] == 1.0  # Dummy mode outputs valid tokens
    assert summary["correct_action_rate"] == 0.25  # exactly 5/20 correct

    # Verify latencies are captured
    averages = summary["averages_ms"]
    for key in ["preprocessing_ms", "prompting_ms", "inference_ms", "total_ms"]:
        assert key in averages
        assert isinstance(averages[key], float)
        assert averages[key] >= 0.0

    # Verify individual runs are detailed
    for run in runs:
        assert "image_id" in run
        assert "expected_action" in run
        assert "predicted_action" in run
        assert "is_valid_token" in run
        assert "is_correct_action" in run
        assert "timing_ms" in run
