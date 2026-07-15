"""Tests for Lite-VLA training record schema (VLA-41)."""

from __future__ import annotations

from pathlib import Path

import pytest

from litevla.actions import ACTION_NAMES
from litevla.data.schema import (
    FIXTURES_PATH,
    RecordSchemaError,
    TrainingRecord,
    load_record_schema,
    parse_training_record,
    read_jsonl,
    training_record_to_dict,
    validate_record_dict,
    write_jsonl,
)


def test_fixture_file_validates_against_schema() -> None:
    schema = load_record_schema()
    for record in read_jsonl(FIXTURES_PATH, schema=schema):
        assert record.action in ACTION_NAMES


def test_parse_training_record_round_trip() -> None:
    raw = {
        "id": "test_1",
        "image_path": "data/reference_images/red_cone_centered.png",
        "instruction": "Move toward the red cube.",
        "action": "MOVE_FORWARD",
        "timestamp": "2026-06-24T12:00:00+00:00",
        "source": "reference",
        "episode_id": "ep1",
        "metadata": {"world": "mvp_arena.wbt"},
    }
    record = parse_training_record(raw)
    assert record == TrainingRecord(
        image_path=raw["image_path"],
        instruction=raw["instruction"],
        action="MOVE_FORWARD",
        timestamp=raw["timestamp"],
        source="reference",
        id="test_1",
        episode_id="ep1",
        metadata={"world": "mvp_arena.wbt"},
    )
    assert training_record_to_dict(record)["action"] == "MOVE_FORWARD"


def test_missing_required_field_fails() -> None:
    with pytest.raises(RecordSchemaError, match="instruction"):
        parse_training_record(
            {
                "image_path": "data/x.png",
                "action": "STOP",
                "timestamp": "2026-06-24T12:00:00+00:00",
                "source": "synthetic",
            }
        )


def test_invalid_action_fails() -> None:
    with pytest.raises(RecordSchemaError, match="FORWARD"):
        parse_training_record(
            {
                "image_path": "data/x.png",
                "instruction": "Go.",
                "action": "FORWARD",
                "timestamp": "2026-06-24T12:00:00+00:00",
                "source": "synthetic",
            }
        )


def test_invalid_source_enum_fails() -> None:
    with pytest.raises(RecordSchemaError):
        parse_training_record(
            {
                "image_path": "data/x.png",
                "instruction": "Go.",
                "action": "STOP",
                "timestamp": "2026-06-24T12:00:00+00:00",
                "source": "unknown_source",
            }
        )


def test_write_and_read_jsonl(tmp_path: Path) -> None:
    records = [
        TrainingRecord(
            image_path="data/a.png",
            instruction="Move toward the red cube.",
            action="MOVE_FORWARD",
            timestamp="2026-06-24T12:00:00+00:00",
            source="synthetic",
            id="w1",
        )
    ]
    out = tmp_path / "mini.jsonl"
    assert write_jsonl(out, iter(records)) == 1
    loaded = list(read_jsonl(out))
    assert len(loaded) == 1
    assert loaded[0].action == "MOVE_FORWARD"


def test_validate_record_dict_rejects_extra_top_level_keys() -> None:
    with pytest.raises(RecordSchemaError):
        validate_record_dict(
            {
                "image_path": "data/x.png",
                "instruction": "Go.",
                "action": "STOP",
                "timestamp": "2026-06-24T12:00:00+00:00",
                "source": "synthetic",
                "unexpected": True,
            }
        )
