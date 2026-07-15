"""Tests for dataset versioning helpers (VLA-47)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from litevla.data.schema import TrainingRecord, write_jsonl
from litevla.data.validator import validate_dataset
from litevla.data.versioning import (
    build_version_artifacts,
    is_valid_processed_version,
    processed_dir,
    render_dataset_card,
    write_dataset_card,
    write_dataset_stats,
)


def test_version_pattern() -> None:
    assert is_valid_processed_version("v0.1.0")
    assert not is_valid_processed_version("0.1.0")


def test_processed_dir_rejects_bad_version() -> None:
    with pytest.raises(ValueError):
        processed_dir("bad-version")


def _write_tiny_png(path: Path) -> None:
    from PIL import Image

    Image.new("RGB", (2, 2), color=(128, 64, 32)).save(path)


def test_write_dataset_stats_and_card(tmp_path: Path) -> None:
    image_dir = tmp_path / "data" / "imgs"
    image_dir.mkdir(parents=True)
    _write_tiny_png(image_dir / "a.png")
    train = tmp_path / "train.jsonl"
    write_jsonl(
        train,
        iter(
            [
                TrainingRecord(
                    id="v1",
                    image_path="data/imgs/a.png",
                    instruction="Move.",
                    action="MOVE_FORWARD",
                    timestamp="2026-06-24T12:00:00+00:00",
                    source="reference",
                )
            ]
        ),
    )
    report = validate_dataset(train, repo_root=tmp_path, check_images=True)
    out_dir = tmp_path / "data" / "processed" / "v0.1.0"
    stats_path = write_dataset_stats(report, version="v0.1.0", output_dir=out_dir)
    card_path = write_dataset_card(
        render_dataset_card(version="v0.1.0", train_report=report),
        version="v0.1.0",
        output_dir=out_dir,
    )
    assert stats_path.is_file()
    assert card_path.is_file()
    assert "MOVE_FORWARD" in card_path.read_text(encoding="utf-8")
    payload = json.loads(stats_path.read_text(encoding="utf-8"))
    assert payload["valid"] is True


def test_build_version_artifacts(tmp_path: Path) -> None:
    version_dir = tmp_path / "data" / "processed" / "v0.2.0"
    version_dir.mkdir(parents=True)
    image_dir = tmp_path / "data" / "imgs"
    image_dir.mkdir(parents=True)
    _write_tiny_png(image_dir / "a.png")
    train = version_dir / "train.jsonl"
    write_jsonl(
        train,
        iter(
            [
                TrainingRecord(
                    id="t1",
                    image_path="data/imgs/a.png",
                    instruction="Stop.",
                    action="STOP",
                    timestamp="2026-06-24T12:00:00+00:00",
                    source="synthetic",
                )
            ]
        ),
    )
    result = build_version_artifacts(
        version="v0.2.0",
        train_jsonl=train,
        repo_root=tmp_path,
        check_images=True,
    )
    assert result["train_valid"] is True
    assert Path(result["dataset_card"]).is_file()
