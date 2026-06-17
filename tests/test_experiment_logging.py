"""Tests for experiment run directory and logging helpers."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
import yaml

from litevla.experiment import (
    CONFIG_FILENAME,
    METADATA_FILENAME,
    METRICS_FILENAME,
    ExperimentRun,
    collect_metadata,
    make_run_id,
    run_directory,
    save_config_snapshot,
    save_metrics,
    slugify_label,
)


def test_slugify_label_normalizes_text() -> None:
    assert slugify_label("Dummy Pipeline") == "dummy-pipeline"
    assert slugify_label("  baseline_v2  ") == "baseline-v2"


def test_slugify_label_rejects_empty_result() -> None:
    with pytest.raises(ValueError, match="alphanumeric"):
        slugify_label("---")


def test_make_run_id_with_fixed_timestamp() -> None:
    moment = datetime(2025, 6, 17, 14, 30, 22, tzinfo=UTC)
    assert make_run_id(now=moment) == "20250617T143022"
    assert make_run_id("Baseline", now=moment) == "baseline_20250617T143022"


def test_run_directory_creates_expected_layout(tmp_path: Path) -> None:
    run_dir = run_directory("benchmark", run_id="test-run", base_dir=tmp_path)

    assert run_dir == tmp_path / "benchmark" / "test-run"
    assert run_dir.is_dir()
    assert (run_dir / "artifacts").is_dir()


def test_experiment_run_writes_config_and_metadata(tmp_path: Path) -> None:
    config = {"runtime": {"mode": "dummy"}, "benchmark": {"iterations": 10, "warmup": 1}}

    with ExperimentRun(
        "inference",
        config,
        run_id="fixed-run",
        base_dir=tmp_path,
        config_path="configs/default.example.yaml",
        repo_root=tmp_path,
    ) as run:
        assert run.directory == tmp_path / "inference" / "fixed-run"
        run.write_metrics({"status": "success", "duration_ms": 5})

    saved_config = yaml.safe_load((run.directory / CONFIG_FILENAME).read_text(encoding="utf-8"))
    assert saved_config == config

    metadata = json.loads((run.directory / METADATA_FILENAME).read_text(encoding="utf-8"))
    assert metadata["run_id"] == "fixed-run"
    assert metadata["kind"] == "inference"
    assert metadata["config_path"] == "configs/default.example.yaml"
    assert metadata["git"]["commit"] is None

    metrics = json.loads((run.directory / METRICS_FILENAME).read_text(encoding="utf-8"))
    assert metrics["status"] == "success"
    assert metrics["duration_ms"] == 5


def test_collect_metadata_includes_core_fields() -> None:
    metadata = collect_metadata(kind="deploy", run_id="demo", config_path=None)

    assert metadata["run_id"] == "demo"
    assert metadata["kind"] == "deploy"
    assert "created_at" in metadata
    assert "python_version" in metadata
    assert "hostname" in metadata
    assert "git" in metadata


def test_save_helpers_write_expected_files(tmp_path: Path) -> None:
    run_dir = tmp_path / "manual"
    run_dir.mkdir()

    config_path = save_config_snapshot(run_dir, {"runtime": {"mode": "model"}})
    metrics_path = save_metrics(run_dir, {"status": "failed", "error": "boom"})

    assert config_path.name == CONFIG_FILENAME
    assert metrics_path.name == METRICS_FILENAME
    assert yaml.safe_load(config_path.read_text(encoding="utf-8"))["runtime"]["mode"] == "model"


def test_dummy_pipeline_log_run_writes_artifacts(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from scripts.run_dummy_pipeline import run_dummy_pipeline

    monkeypatch.chdir(tmp_path)
    config = {
        "runtime": {
            "mode": "dummy",
            "heartbeat_hz": 10,
            "default_instruction": "go",
        },
        "ros": {"image_topic": "/image_raw", "cmd_vel_topic": "/cmd_vel"},
        "safety": {"max_linear_vel": 0.5, "max_angular_vel": 1.0},
    }

    assert run_dummy_pipeline(config, log_run=True, run_label="ci") == 0

    run_dirs = list((tmp_path / "runs" / "inference").iterdir())
    assert len(run_dirs) == 1
    run_dir = run_dirs[0]
    assert (run_dir / CONFIG_FILENAME).is_file()
    assert (run_dir / METADATA_FILENAME).is_file()
    metrics = json.loads((run_dir / METRICS_FILENAME).read_text(encoding="utf-8"))
    assert metrics["status"] == "success"
    assert metrics["action_count"] == 2
