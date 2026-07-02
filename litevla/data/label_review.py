"""Human label review CSV export/import for processed JSONL (Epic 105 / VLA-44)."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from litevla.actions import parse_action
from litevla.data.schema import (
    TrainingRecord,
    read_jsonl,
    write_jsonl,
)

REVIEW_COLUMNS: tuple[str, ...] = (
    "id",
    "image_path",
    "instruction",
    "action_proposed",
    "action_reviewed",
    "review_status",
    "reviewer",
    "review_notes",
    "reviewed_at",
)

REVIEW_STATUSES: frozenset[str] = frozenset({"pending", "approved", "corrected", "rejected"})
DEFAULT_REVIEW_STATUS = "pending"


class LabelReviewError(ValueError):
    """Raised when a review CSV row is invalid or cannot be merged."""


@dataclass
class ImportReviewStats:
    """Counts from applying a review CSV onto a JSONL dataset."""

    input_rows: int = 0
    exported_for_review: int = 0
    approved: int = 0
    corrected: int = 0
    rejected: int = 0
    pending_skipped: int = 0
    output_rows: int = 0
    unchanged: int = 0


@dataclass
class ReviewRow:
    """One human review row keyed by training record ``id``."""

    id: str
    image_path: str
    instruction: str
    action_proposed: str
    action_reviewed: str = ""
    review_status: str = DEFAULT_REVIEW_STATUS
    reviewer: str = ""
    review_notes: str = ""
    reviewed_at: str = ""

    def to_csv_dict(self) -> dict[str, str]:
        return {
            "id": self.id,
            "image_path": self.image_path,
            "instruction": self.instruction,
            "action_proposed": self.action_proposed,
            "action_reviewed": self.action_reviewed,
            "review_status": self.review_status,
            "reviewer": self.reviewer,
            "review_notes": self.review_notes,
            "reviewed_at": self.reviewed_at,
        }


def _record_id(record: TrainingRecord, line_no: int) -> str:
    if record.id:
        return record.id
    return f"anon_{line_no:05d}"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def export_jsonl_to_review_csv(jsonl_path: str | Path, csv_path: str | Path) -> int:
    """Write a review spreadsheet from processed JSONL. Returns row count."""
    out_path = Path(csv_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with out_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(REVIEW_COLUMNS))
        writer.writeheader()
        for line_no, record in enumerate(read_jsonl(jsonl_path), start=1):
            row = ReviewRow(
                id=_record_id(record, line_no),
                image_path=record.image_path,
                instruction=record.instruction,
                action_proposed=record.action,
                review_status=DEFAULT_REVIEW_STATUS,
            )
            writer.writerow(row.to_csv_dict())
            count += 1
    return count


def read_review_csv(csv_path: str | Path) -> list[ReviewRow]:
    """Parse and validate a label review CSV."""
    path = Path(csv_path)
    if not path.is_file():
        raise FileNotFoundError(f"Review CSV not found: {path}")

    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise LabelReviewError(f"{path}: missing header row.")
        missing = [col for col in REVIEW_COLUMNS if col not in reader.fieldnames]
        if missing:
            raise LabelReviewError(f"{path}: missing columns: {', '.join(missing)}")

        rows: list[ReviewRow] = []
        for line_no, raw in enumerate(reader, start=2):
            row_id = str(raw.get("id", "")).strip()
            if not row_id:
                raise LabelReviewError(f"{path}:{line_no}: id is required.")

            status = str(raw.get("review_status", DEFAULT_REVIEW_STATUS)).strip().lower() or DEFAULT_REVIEW_STATUS
            if status not in REVIEW_STATUSES:
                allowed = ", ".join(sorted(REVIEW_STATUSES))
                raise LabelReviewError(f"{path}:{line_no}: review_status must be one of {allowed}.")

            action_proposed = str(raw.get("action_proposed", "")).strip()
            if not action_proposed:
                raise LabelReviewError(f"{path}:{line_no}: action_proposed is required.")
            try:
                parse_action(action_proposed)
            except ValueError as exc:
                raise LabelReviewError(f"{path}:{line_no}: {exc}") from exc

            action_reviewed = str(raw.get("action_reviewed", "")).strip()
            if action_reviewed:
                try:
                    parse_action(action_reviewed)
                except ValueError as exc:
                    raise LabelReviewError(f"{path}:{line_no}: {exc}") from exc

            if status == "corrected" and not action_reviewed:
                raise LabelReviewError(
                    f"{path}:{line_no}: corrected rows must set action_reviewed to a valid action."
                )

            rows.append(
                ReviewRow(
                    id=row_id,
                    image_path=str(raw.get("image_path", "")).strip(),
                    instruction=str(raw.get("instruction", "")).strip(),
                    action_proposed=action_proposed,
                    action_reviewed=action_reviewed,
                    review_status=status,
                    reviewer=str(raw.get("reviewer", "")).strip(),
                    review_notes=str(raw.get("review_notes", "")).strip(),
                    reviewed_at=str(raw.get("reviewed_at", "")).strip(),
                )
            )
        return rows


def _final_action(row: ReviewRow) -> str:
    if row.review_status == "corrected":
        return row.action_reviewed
    if row.action_reviewed:
        return row.action_reviewed
    return row.action_proposed


def _merge_review(record: TrainingRecord, row: ReviewRow) -> TrainingRecord | None:
    """Apply one review row. Returns ``None`` when the record is rejected."""
    if row.review_status == "pending":
        return record
    if row.review_status == "rejected":
        return None

    final_action = _final_action(row)
    meta: dict[str, Any] = dict(record.metadata)
    meta["review"] = {
        "status": row.review_status,
        "reviewer": row.reviewer or None,
        "notes": row.review_notes or None,
        "reviewed_at": row.reviewed_at or _utc_now_iso(),
        "original_action": record.action,
        "original_source": record.source,
    }
    meta["review"] = {k: v for k, v in meta["review"].items() if v is not None}

    return TrainingRecord(
        image_path=record.image_path,
        instruction=record.instruction,
        action=final_action,
        timestamp=record.timestamp,
        source="manual_review",
        id=record.id or row.id,
        episode_id=record.episode_id,
        metadata=meta,
    )


def apply_reviews_to_records(
    records: Iterator[TrainingRecord],
    reviews: list[ReviewRow],
) -> tuple[list[TrainingRecord], ImportReviewStats]:
    """Merge review rows onto training records matched by ``id``."""
    review_by_id = {row.id: row for row in reviews}
    stats = ImportReviewStats()
    out: list[TrainingRecord] = []

    for line_no, record in enumerate(records, start=1):
        stats.input_rows += 1
        record_id = _record_id(record, line_no)
        row = review_by_id.get(record_id)
        if row is None:
            out.append(record)
            stats.unchanged += 1
            continue

        if row.review_status == "pending":
            out.append(record)
            stats.pending_skipped += 1
            continue

        merged = _merge_review(record, row)
        if merged is None:
            stats.rejected += 1
            continue

        if row.review_status == "approved":
            stats.approved += 1
        elif row.review_status == "corrected":
            stats.corrected += 1

        out.append(merged)

    stats.output_rows = len(out)
    return out, stats


def validate_review_csv_no_pending(
    csv_path: str | Path,
    *,
    jsonl_path: str | Path | None = None,
) -> list[str]:
    """Return ids still marked ``pending`` in a review CSV (VLA-45 release gate)."""
    rows = read_review_csv(csv_path)
    pending = [row.id for row in rows if row.review_status == "pending"]
    if jsonl_path is not None:
        jsonl_ids = {
            record.id
            for record in read_jsonl(jsonl_path)
            if record.id
        }
        pending = [row_id for row_id in pending if row_id in jsonl_ids]
    return pending


def bulk_approve_review_csv(
    csv_path: str | Path,
    *,
    reviewer: str,
    notes: str = "Machine-labeled reference/synthetic row approved for starter release.",
    reviewed_at: str | None = None,
) -> int:
    """Mark every ``pending`` row as ``approved`` in place. Returns rows updated."""
    path = Path(csv_path)
    rows = read_review_csv(path)
    ts = reviewed_at or _utc_now_iso()
    updated = 0
    for row in rows:
        if row.review_status != "pending":
            continue
        row.review_status = "approved"
        row.reviewer = reviewer
        row.review_notes = notes
        row.reviewed_at = ts
        updated += 1
    if updated:
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(REVIEW_COLUMNS))
            writer.writeheader()
            for row in rows:
                writer.writerow(row.to_csv_dict())
    return updated


def import_review_csv_to_jsonl(
    *,
    jsonl_path: str | Path,
    csv_path: str | Path,
    output_path: str | Path,
) -> ImportReviewStats:
    """Apply reviewed CSV onto JSONL and write validated output."""
    reviews = read_review_csv(csv_path)
    merged, stats = apply_reviews_to_records(read_jsonl(jsonl_path), reviews)
    write_jsonl(output_path, iter(merged))
    return stats
