"""Tests for label review CSV workflow (VLA-44)."""

from __future__ import annotations

from pathlib import Path

import pytest

from litevla.data.label_review import (
    LabelReviewError,
    apply_reviews_to_records,
    export_jsonl_to_review_csv,
    import_review_csv_to_jsonl,
    read_review_csv,
)
from litevla.data.schema import FIXTURES_PATH, TrainingRecord, read_jsonl, write_jsonl

FIXTURE_CSV = Path("data/templates/label_review.csv")


def test_export_jsonl_to_review_csv(tmp_path: Path) -> None:
    out = tmp_path / "review.csv"
    count = export_jsonl_to_review_csv(FIXTURES_PATH, out)
    assert count == 6
    rows = read_review_csv(out)
    assert rows[0].id == "ref_001"
    assert rows[0].action_proposed == "MOVE_FORWARD"
    assert rows[0].review_status == "pending"


def test_import_approved_sets_manual_review_source(tmp_path: Path) -> None:
    csv_path = tmp_path / "review.csv"
    export_jsonl_to_review_csv(FIXTURES_PATH, csv_path)
    text = csv_path.read_text(encoding="utf-8")
    text = text.replace(
        "ref_001,data/reference_images/red_cone_centered.png,Move toward the red cube.,MOVE_FORWARD,,pending,,,",
        "ref_001,data/reference_images/red_cone_centered.png,Move toward the red cube.,MOVE_FORWARD,,approved,alice,looks good,2026-06-24T13:00:00+00:00",
    )
    csv_path.write_text(text, encoding="utf-8")

    out_jsonl = tmp_path / "train_reviewed.jsonl"
    stats = import_review_csv_to_jsonl(
        jsonl_path=FIXTURES_PATH,
        csv_path=csv_path,
        output_path=out_jsonl,
    )
    assert stats.approved == 1
    records = list(read_jsonl(out_jsonl))
    first = next(r for r in records if r.id == "ref_001")
    assert first.source == "manual_review"
    assert first.action == "MOVE_FORWARD"
    assert first.metadata["review"]["status"] == "approved"
    assert first.metadata["review"]["reviewer"] == "alice"


def test_import_corrected_changes_action(tmp_path: Path) -> None:
    csv_path = tmp_path / "review.csv"
    export_jsonl_to_review_csv(FIXTURES_PATH, csv_path)
    text = csv_path.read_text(encoding="utf-8")
    text = text.replace(
        "ref_004,data/reference_images/stop_barrier_close.png,Stop when close to the red cube.,STOP,,pending,,,",
        "ref_004,data/reference_images/stop_barrier_close.png,Stop when close to the red cube.,STOP,SLOW_DOWN,corrected,bob,still approaching,2026-06-24T13:01:00+00:00",
    )
    csv_path.write_text(text, encoding="utf-8")

    out_jsonl = tmp_path / "out.jsonl"
    stats = import_review_csv_to_jsonl(
        jsonl_path=FIXTURES_PATH,
        csv_path=csv_path,
        output_path=out_jsonl,
    )
    assert stats.corrected == 1
    record = next(r for r in read_jsonl(out_jsonl) if r.id == "ref_004")
    assert record.action == "SLOW_DOWN"
    assert record.metadata["review"]["original_action"] == "STOP"


def test_import_rejected_drops_row(tmp_path: Path) -> None:
    csv_path = tmp_path / "review.csv"
    export_jsonl_to_review_csv(FIXTURES_PATH, csv_path)
    text = csv_path.read_text(encoding="utf-8")
    text = text.replace(
        "syn_001,data/processed/v0.1.0/images/synthetic_slow_approach.png,Move toward the red cube.,SLOW_DOWN,,pending,,,",
        "syn_001,data/processed/v0.1.0/images/synthetic_slow_approach.png,Move toward the red cube.,SLOW_DOWN,,rejected,alice,duplicate aug,2026-06-24T13:02:00+00:00",
    )
    csv_path.write_text(text, encoding="utf-8")

    out_jsonl = tmp_path / "out.jsonl"
    stats = import_review_csv_to_jsonl(
        jsonl_path=FIXTURES_PATH,
        csv_path=csv_path,
        output_path=out_jsonl,
    )
    assert stats.rejected == 1
    ids = {r.id for r in read_jsonl(out_jsonl)}
    assert "syn_001" not in ids


def test_read_review_csv_rejects_invalid_action(tmp_path: Path) -> None:
    csv_path = tmp_path / "bad.csv"
    csv_path.write_text(
        "id,image_path,instruction,action_proposed,action_reviewed,review_status,reviewer,review_notes,reviewed_at\n"
        "x,data/a.png,Go,FORWARD,,approved,,,\n",
        encoding="utf-8",
    )
    with pytest.raises(LabelReviewError, match="FORWARD"):
        read_review_csv(csv_path)


def test_read_review_csv_corrected_requires_action_reviewed(tmp_path: Path) -> None:
    csv_path = tmp_path / "bad.csv"
    csv_path.write_text(
        "id,image_path,instruction,action_proposed,action_reviewed,review_status,reviewer,review_notes,reviewed_at\n"
        "x,data/a.png,Go,MOVE_FORWARD,,corrected,,,\n",
        encoding="utf-8",
    )
    with pytest.raises(LabelReviewError, match="action_reviewed"):
        read_review_csv(csv_path)


def test_apply_reviews_leaves_unmatched_records_unchanged() -> None:
    record = TrainingRecord(
        id="only",
        image_path="data/a.png",
        instruction="Move.",
        action="STOP",
        timestamp="2026-06-24T12:00:00+00:00",
        source="reference",
    )
    merged, stats = apply_reviews_to_records(iter([record]), [])
    assert len(merged) == 1
    assert stats.unchanged == 1
    assert merged[0].source == "reference"


def test_fixture_template_csv_is_valid() -> None:
    rows = read_review_csv(FIXTURE_CSV)
    assert len(rows) == 2
    assert all(r.review_status == "pending" for r in rows)
