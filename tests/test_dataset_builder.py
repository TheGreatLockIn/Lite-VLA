"""Tests for starter dataset builder (VLA-43)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from PIL import Image

from litevla.data.builder import (
    DatasetBuildError,
    build_starter_dataset,
    load_reference_manifest,
    parse_frame_stamp,
    records_from_raw_episode,
    split_records,
)
from litevla.data.schema import TrainingRecord, read_jsonl


def _write_png(path: Path, color: tuple[int, int, int] = (128, 64, 32)) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (32, 24), color=color).save(path)


def _write_manifest(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "episode_id": "test_ref",
                "world": "mvp_arena.wbt",
                "entries": [
                    {
                        "filename": "scene_a.png",
                        "instruction": "Move toward the red cube.",
                        "action": "MOVE_FORWARD",
                    },
                    {
                        "filename": "scene_b.png",
                        "instruction": "Stop when close to the red cube.",
                        "action": "STOP",
                    },
                ],
            }
        ),
        encoding="utf-8",
    )


def test_parse_frame_stamp() -> None:
    assert parse_frame_stamp("12_340000000.png") == (12, 340000000)
    assert parse_frame_stamp("bad.png") is None


def test_records_from_raw_episode_forward_fills_actions(tmp_path: Path) -> None:
    episode_dir = tmp_path / "20260624T120000Z"
    frames_dir = episode_dir / "frames"
    frames_dir.mkdir(parents=True)
    _write_png(frames_dir / "10_000000000.png")
    _write_png(frames_dir / "11_000000000.png")
    _write_png(frames_dir / "12_000000000.png")

    (episode_dir / "episode.json").write_text(
        json.dumps(
            {
                "episode_id": "20260624T120000Z",
                "instruction": "Move toward the red cube.",
                "source": "teleop",
                "world": "mvp_arena.wbt",
                "started_at": "2026-06-24T12:00:00+00:00",
                "record_frames_hz": 5.0,
                "schema_version": "1",
            }
        ),
        encoding="utf-8",
    )
    commands = [
        {
            "stamp": "2026-06-24T12:00:01+00:00",
            "sim_stamp_sec": 10,
            "sim_stamp_nanosec": 0,
            "source": "teleop",
            "action": "MOVE_FORWARD",
            "linear_x": 0.2,
            "angular_z": 0.0,
        },
        {
            "stamp": "2026-06-24T12:00:02+00:00",
            "sim_stamp_sec": 12,
            "sim_stamp_nanosec": 0,
            "source": "teleop",
            "action": "STOP",
            "linear_x": 0.0,
            "angular_z": 0.0,
        },
    ]
    with (episode_dir / "commands.jsonl").open("w", encoding="utf-8") as handle:
        for row in commands:
            handle.write(json.dumps(row) + "\n")

    records, count = records_from_raw_episode(episode_dir, repo_root=tmp_path)
    assert count == 3
    assert records[0].action == "MOVE_FORWARD"
    assert records[1].action == "MOVE_FORWARD"
    assert records[2].action == "STOP"
    assert records[0].source == "teleop"


def test_split_records_unique_ids(tmp_path: Path) -> None:
    records = [
        TrainingRecord(
            image_path=f"data/x{i}.png",
            instruction="Go.",
            action="STOP",
            timestamp="2026-06-24T12:00:00+00:00",
            source="synthetic",
            id=f"id_{i}",
        )
        for i in range(10)
    ]
    train, val = split_records(records, val_ratio=0.2, seed=42)
    assert len(train) == 8
    assert len(val) == 2
    train_ids = {record.id for record in train}
    val_ids = {record.id for record in val}
    assert train_ids.isdisjoint(val_ids)


def test_split_records_rejects_duplicate_ids() -> None:
    records = [
        TrainingRecord(
            image_path="data/x.png",
            instruction="Go.",
            action="STOP",
            timestamp="2026-06-24T12:00:00+00:00",
            source="synthetic",
            id="dup",
        ),
        TrainingRecord(
            image_path="data/y.png",
            instruction="Go.",
            action="STOP",
            timestamp="2026-06-24T12:00:01+00:00",
            source="synthetic",
            id="dup",
        ),
    ]
    with pytest.raises(DatasetBuildError, match="Duplicate record ids"):
        split_records(records, val_ratio=0.5, seed=1)


def test_build_starter_dataset_reaches_min_records(tmp_path: Path) -> None:
    ref_dir = tmp_path / "data" / "reference_images"
    manifest_path = ref_dir / "manifest.json"
    _write_manifest(manifest_path)
    _write_png(ref_dir / "scene_a.png")
    _write_png(ref_dir / "scene_b.png")

    result = build_starter_dataset(
        version="v0.1.0",
        min_records=20,
        val_ratio=0.1,
        seed=7,
        reference_manifest_path=manifest_path,
        reference_images_dir=ref_dir,
        raw_episodes_dir=tmp_path / "data" / "raw" / "episodes",
        processed_root=tmp_path / "data" / "processed",
        repo_root=tmp_path,
        include_raw_episodes=False,
    )

    assert result.train_count + result.val_count >= 20
    assert result.stats.reference_base == 2
    assert result.stats.synthetic_augmented > 0
    assert result.train_path.is_file()
    assert result.val_path.is_file()

    train_rows = list(read_jsonl(result.train_path))
    val_rows = list(read_jsonl(result.val_path))
    all_ids = [row.id for row in train_rows + val_rows if row.id]
    assert len(all_ids) == len(set(all_ids))


def test_load_reference_manifest() -> None:
    manifest = load_reference_manifest(
        Path("data/reference_images/manifest.json"),
    )
    assert len(manifest.entries) == 4
    assert manifest.entries[0].action == "MOVE_FORWARD"
