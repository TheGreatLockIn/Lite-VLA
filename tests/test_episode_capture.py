"""Tests for raw episode capture helpers (VLA-42)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from litevla.data.episode import (
    EpisodeMetadata,
    EpisodeSchemaError,
    frame_filename,
    init_raw_episode,
    load_episode_schema,
    read_episode_json,
    validate_episode_dict,
    write_episode_json,
)


def test_init_raw_episode_creates_layout(tmp_path: Path) -> None:
    episode_dir = init_raw_episode(
        base_dir=tmp_path,
        instruction="Move toward the red cube.",
        source="teleop",
        world="mvp_arena.wbt",
        record_frames_hz=5.0,
        episode_id="20260624T120000Z",
    )
    assert episode_dir.is_dir()
    assert (episode_dir / "frames").is_dir()
    assert (episode_dir / "episode.json").is_file()
    meta = read_episode_json(episode_dir)
    assert meta.episode_id == "20260624T120000Z"
    assert meta.instruction == "Move toward the red cube."
    assert meta.record_frames_hz == 5.0


def test_episode_schema_rejects_unknown_source() -> None:
    with pytest.raises(EpisodeSchemaError):
        validate_episode_dict(
            {
                "episode_id": "ep1",
                "instruction": "Go.",
                "source": "unknown",
                "world": "mvp_arena.wbt",
                "started_at": "2026-06-24T12:00:00+00:00",
                "record_frames_hz": 5.0,
            },
            schema=load_episode_schema(),
        )


def test_frame_filename_matches_camera_subscriber() -> None:
    assert frame_filename(12, 340000000) == "12_340000000.png"


def test_write_episode_json_round_trip(tmp_path: Path) -> None:
    episode_dir = tmp_path / "ep_test"
    episode_dir.mkdir()
    meta = EpisodeMetadata(
        episode_id="ep_test",
        instruction="Stop near the cone.",
        source="teleop",
        world="mvp_arena.wbt",
        started_at="2026-06-24T12:00:00+00:00",
        record_frames_hz=5.0,
    )
    write_episode_json(episode_dir, meta)
    raw = json.loads((episode_dir / "episode.json").read_text(encoding="utf-8"))
    assert raw["schema_version"] == "1"
    assert read_episode_json(episode_dir).instruction == "Stop near the cone."
