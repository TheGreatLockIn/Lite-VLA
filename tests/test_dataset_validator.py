"""Tests for dataset validation (VLA-45)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from litevla.data.schema import FIXTURES_PATH, TrainingRecord, write_jsonl
from litevla.data.validator import (
    DatasetValidationReport,
    validate_dataset,
    write_validation_report,
)


def _write_mini_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")


def test_validate_fixtures_schema_only(tmp_path: Path) -> None:
    report = validate_dataset(FIXTURES_PATH, check_images=False)
    assert report.record_count == 6
    assert report.error_count == 0
    assert report.action_counts["MOVE_FORWARD"] >= 1
    assert report.source_counts["reference"] >= 1


def test_validate_missing_image_is_error(tmp_path: Path) -> None:
    jsonl = tmp_path / "train.jsonl"
    _write_mini_jsonl(
        jsonl,
        [
            {
                "id": "m1",
                "image_path": "data/does_not_exist/missing.png",
                "instruction": "Move.",
                "action": "STOP",
                "timestamp": "2026-06-24T12:00:00+00:00",
                "source": "synthetic",
            }
        ],
    )
    report = validate_dataset(jsonl, repo_root=tmp_path, check_images=True)
    assert not report.valid
    assert report.error_count == 1
    assert report.issues[0].code == "missing_image"


def test_validate_invalid_json_and_schema(tmp_path: Path) -> None:
    jsonl = tmp_path / "bad.jsonl"
    jsonl.write_text(
        "not json\n"
        '{"id":"x","image_path":"a.png","instruction":"Go","action":"FORWARD",'
        '"timestamp":"2026-06-24T12:00:00+00:00","source":"synthetic"}\n',
        encoding="utf-8",
    )
    report = validate_dataset(jsonl, check_images=False)
    assert report.error_count >= 2
    codes = {issue.code for issue in report.issues}
    assert "invalid_json" in codes
    assert "schema_invalid" in codes


def test_validate_duplicate_id(tmp_path: Path) -> None:
    row = {
        "id": "dup",
        "image_path": "data/a.png",
        "instruction": "Move.",
        "action": "STOP",
        "timestamp": "2026-06-24T12:00:00+00:00",
        "source": "synthetic",
    }
    jsonl = tmp_path / "dup.jsonl"
    _write_mini_jsonl(jsonl, [row, row])
    report = validate_dataset(jsonl, check_images=False)
    assert not report.valid
    assert "dup" in report.duplicate_ids


def test_validate_action_imbalance_warning(tmp_path: Path) -> None:
    rows = [
        {
            "id": f"r{i}",
            "image_path": "data/a.png",
            "instruction": "Move.",
            "action": "MOVE_FORWARD",
            "timestamp": "2026-06-24T12:00:00+00:00",
            "source": "synthetic",
        }
        for i in range(4)
    ] + [
        {
            "id": "r_stop",
            "image_path": "data/a.png",
            "instruction": "Stop.",
            "action": "STOP",
            "timestamp": "2026-06-24T12:00:01+00:00",
            "source": "synthetic",
        }
    ]
    jsonl = tmp_path / "imbalanced.jsonl"
    _write_mini_jsonl(jsonl, rows)
    report = validate_dataset(jsonl, check_images=False)
    assert report.valid
    assert any(issue.code == "action_imbalance" for issue in report.issues)


def test_write_validation_report(tmp_path: Path) -> None:
    report = validate_dataset(FIXTURES_PATH, check_images=False)
    out = tmp_path / "report.json"
    write_validation_report(report, out)
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["record_count"] == 6
    assert "action_counts" in data
