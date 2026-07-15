"""Dataset validation for processed JSONL (Epic 105 / VLA-45)."""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from litevla.actions import ACTION_NAMES
from litevla.data.schema import (
    REPO_ROOT,
    RecordSchemaError,
    load_record_schema,
    parse_training_record,
)

from litevla.data.label_review import LabelReviewError, validate_review_csv_no_pending

IMBALANCE_WARNING_RATIO = 0.5


@dataclass(frozen=True)
class ValidationIssue:
    """One schema, label, or filesystem problem."""

    severity: str  # error | warning
    code: str
    message: str
    line: int | None = None
    record_id: str | None = None


@dataclass
class DatasetValidationReport:
    """Aggregated validation output for one JSONL file."""

    jsonl_path: str
    record_count: int = 0
    error_count: int = 0
    warning_count: int = 0
    action_counts: dict[str, int] = field(default_factory=dict)
    source_counts: dict[str, int] = field(default_factory=dict)
    missing_images: list[str] = field(default_factory=list)
    duplicate_ids: list[str] = field(default_factory=list)
    issues: list[ValidationIssue] = field(default_factory=list)

    @property
    def valid(self) -> bool:
        return self.error_count == 0

    def add_issue(self, issue: ValidationIssue) -> None:
        self.issues.append(issue)
        if issue.severity == "error":
            self.error_count += 1
        else:
            self.warning_count += 1

    def to_dict(self) -> dict[str, Any]:
        return {
            "jsonl_path": self.jsonl_path,
            "valid": self.valid,
            "record_count": self.record_count,
            "error_count": self.error_count,
            "warning_count": self.warning_count,
            "action_counts": dict(self.action_counts),
            "source_counts": dict(self.source_counts),
            "missing_images": list(self.missing_images),
            "duplicate_ids": list(self.duplicate_ids),
            "issues": [
                {
                    "severity": issue.severity,
                    "code": issue.code,
                    "message": issue.message,
                    "line": issue.line,
                    "record_id": issue.record_id,
                }
                for issue in self.issues
            ],
        }


def resolve_image_path(image_path: str, *, repo_root: Path) -> Path:
    """Resolve a repo-relative training image path."""
    path = Path(image_path)
    if path.is_absolute():
        return path
    return repo_root / path


def validate_dataset(
    jsonl_path: str | Path,
    *,
    repo_root: Path | None = None,
    check_images: bool = True,
    require_unique_ids: bool = True,
    warn_on_imbalance: bool = True,
    review_csv_path: str | Path | None = None,
) -> DatasetValidationReport:
    """Validate a processed JSONL dataset and return a summary report."""
    file_path = Path(jsonl_path)
    if not file_path.is_file():
        raise FileNotFoundError(f"JSONL dataset not found: {file_path}")

    root = repo_root or REPO_ROOT
    schema = load_record_schema()
    report = DatasetValidationReport(jsonl_path=str(file_path))

    seen_ids: dict[str, int] = {}
    action_counter: Counter[str] = Counter()
    source_counter: Counter[str] = Counter()
    missing_images: set[str] = set()

    with file_path.open(encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            text = line.strip()
            if not text:
                report.add_issue(
                    ValidationIssue(
                        severity="warning",
                        code="empty_line",
                        message="Blank line skipped.",
                        line=line_no,
                    )
                )
                continue

            try:
                raw = json.loads(text)
            except json.JSONDecodeError as exc:
                report.add_issue(
                    ValidationIssue(
                        severity="error",
                        code="invalid_json",
                        message=str(exc),
                        line=line_no,
                    )
                )
                continue

            record_id = str(raw.get("id", "")).strip() or None
            try:
                record = parse_training_record(raw, schema=schema)
            except RecordSchemaError as exc:
                report.add_issue(
                    ValidationIssue(
                        severity="error",
                        code="schema_invalid",
                        message=str(exc),
                        line=line_no,
                        record_id=record_id,
                    )
                )
                continue

            report.record_count += 1
            action_counter[record.action] += 1
            source_counter[record.source] += 1

            if record.id:
                if record.id in seen_ids:
                    report.duplicate_ids.append(record.id)
                    report.add_issue(
                        ValidationIssue(
                            severity="error",
                            code="duplicate_id",
                            message=f"Duplicate id {record.id!r} (first at line {seen_ids[record.id]}).",
                            line=line_no,
                            record_id=record.id,
                        )
                    )
                else:
                    seen_ids[record.id] = line_no
            elif require_unique_ids:
                report.add_issue(
                    ValidationIssue(
                        severity="warning",
                        code="missing_id",
                        message="Record has no id; harder to audit and review.",
                        line=line_no,
                    )
                )

            if check_images:
                image_file = resolve_image_path(record.image_path, repo_root=root)
                if not image_file.is_file():
                    missing_images.add(record.image_path)
                    report.add_issue(
                        ValidationIssue(
                            severity="error",
                            code="missing_image",
                            message=f"Image not found: {record.image_path}",
                            line=line_no,
                            record_id=record.id,
                        )
                    )

    report.action_counts = dict(sorted(action_counter.items()))
    report.source_counts = dict(sorted(source_counter.items()))
    report.missing_images = sorted(missing_images)

    if report.record_count == 0 and report.error_count == 0:
        report.add_issue(
            ValidationIssue(
                severity="error",
                code="empty_dataset",
                message="No valid training records found.",
            )
        )

    if warn_on_imbalance and report.record_count > 0:
        top_action, top_count = action_counter.most_common(1)[0]
        ratio = top_count / report.record_count
        if ratio > IMBALANCE_WARNING_RATIO:
            report.add_issue(
                ValidationIssue(
                    severity="warning",
                    code="action_imbalance",
                    message=(
                        f"{top_action} is {ratio:.0%} of rows ({top_count}/{report.record_count}). "
                        f"Consider rebalancing before fine-tuning."
                    ),
                )
            )

        missing_actions = sorted(set(ACTION_NAMES) - set(action_counter))
        if missing_actions and report.record_count >= len(ACTION_NAMES):
            report.add_issue(
                ValidationIssue(
                    severity="warning",
                    code="missing_action_coverage",
                    message=f"No examples for: {', '.join(missing_actions)}.",
                )
            )

    if review_csv_path is not None:
        csv_file = Path(review_csv_path)
        if not csv_file.is_file():
            report.add_issue(
                ValidationIssue(
                    severity="error",
                    code="review_csv_missing",
                    message=f"Review CSV not found: {csv_file}",
                )
            )
        else:
            try:
                pending_ids = validate_review_csv_no_pending(csv_file, jsonl_path=file_path)
            except LabelReviewError as exc:
                report.add_issue(
                    ValidationIssue(
                        severity="error",
                        code="review_csv_invalid",
                        message=str(exc),
                    )
                )
            else:
                if pending_ids:
                    preview = ", ".join(pending_ids[:5])
                    suffix = f" (+{len(pending_ids) - 5} more)" if len(pending_ids) > 5 else ""
                    report.add_issue(
                        ValidationIssue(
                            severity="error",
                            code="review_pending",
                            message=f"{len(pending_ids)} review row(s) still pending: {preview}{suffix}.",
                        )
                    )

    return report


def write_validation_report(report: DatasetValidationReport, output_path: str | Path) -> Path:
    """Write a JSON validation report (VLA-47 stats artifact)."""
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report.to_dict(), indent=2) + "\n", encoding="utf-8")
    return out


def format_report_summary(report: DatasetValidationReport) -> str:
    """Human-readable one-screen summary for CLI output."""
    lines = [
        f"Dataset: {report.jsonl_path}",
        f"Valid:   {'yes' if report.valid else 'NO'}",
        f"Records: {report.record_count}",
        f"Errors:  {report.error_count}  Warnings: {report.warning_count}",
        "",
        "Action distribution:",
    ]
    for action, count in report.action_counts.items():
        lines.append(f"  {action}: {count}")
    lines.append("")
    lines.append("Source distribution:")
    for source, count in report.source_counts.items():
        lines.append(f"  {source}: {count}")
    if report.missing_images:
        lines.append("")
        lines.append(f"Missing images: {len(report.missing_images)}")
    if report.duplicate_ids:
        lines.append(f"Duplicate ids: {', '.join(report.duplicate_ids)}")
    if report.issues:
        lines.append("")
        lines.append("Issues:")
        for issue in report.issues[:20]:
            loc = f"line {issue.line}" if issue.line else "file"
            rid = f" id={issue.record_id}" if issue.record_id else ""
            lines.append(f"  [{issue.severity}] {issue.code} ({loc}{rid}): {issue.message}")
        if len(report.issues) > 20:
            lines.append(f"  ... and {len(report.issues) - 20} more")
    return "\n".join(lines)
