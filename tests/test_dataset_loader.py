"""Tests for Lite-VLA PyTorch dataset loader (VLA-46)."""

from __future__ import annotations

from pathlib import Path

import pytest

from litevla.data.loader import LiteVLADataset
from litevla.data.schema import TrainingRecord, write_jsonl


def _write_tiny_png(path: Path) -> None:
    from PIL import Image

    Image.new("RGB", (2, 2), color=(128, 64, 32)).save(path)


def test_loader_reads_image_and_labels(tmp_path: Path) -> None:
    image_dir = tmp_path / "data" / "imgs"
    image_dir.mkdir(parents=True)
    image_path = image_dir / "frame.png"
    _write_tiny_png(image_path)

    jsonl = tmp_path / "train.jsonl"
    write_jsonl(
        jsonl,
        iter(
            [
                TrainingRecord(
                    id="l1",
                    image_path="data/imgs/frame.png",
                    instruction="Move toward the red cube.",
                    action="MOVE_FORWARD",
                    timestamp="2026-06-24T12:00:00+00:00",
                    source="reference",
                )
            ]
        ),
    )

    dataset = LiteVLADataset(jsonl, repo_root=tmp_path)
    assert len(dataset) == 1
    sample = dataset[0]
    assert sample["action"] == "MOVE_FORWARD"
    assert sample["instruction"] == "Move toward the red cube."
    assert sample["id"] == "l1"
    assert hasattr(sample["image"], "size")


def test_loader_batch_via_dataloader(tmp_path: Path) -> None:
    torch = pytest.importorskip("torch")
    image_dir = tmp_path / "data" / "imgs"
    image_dir.mkdir(parents=True)
    _write_tiny_png(image_dir / "a.png")
    jsonl = tmp_path / "train.jsonl"
    write_jsonl(
        jsonl,
        iter(
            [
                TrainingRecord(
                    id="b1",
                    image_path="data/imgs/a.png",
                    instruction="Turn left.",
                    action="TURN_LEFT",
                    timestamp="2026-06-24T12:00:00+00:00",
                    source="synthetic",
                ),
                TrainingRecord(
                    id="b2",
                    image_path="data/imgs/a.png",
                    instruction="Stop.",
                    action="STOP",
                    timestamp="2026-06-24T12:00:01+00:00",
                    source="synthetic",
                ),
            ]
        ),
    )

    dataset = LiteVLADataset(jsonl, repo_root=tmp_path)
    loader = torch.utils.data.DataLoader(dataset, batch_size=2)
    batch = next(iter(loader))
    assert len(batch["action"]) == 2
    assert batch["action"][0] == "TURN_LEFT"
