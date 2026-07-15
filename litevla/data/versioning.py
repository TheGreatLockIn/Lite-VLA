"""Dataset version naming and documentation helpers (Epic 105 / VLA-47)."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from litevla.data.validator import DatasetValidationReport, validate_dataset, write_validation_report

VERSION_PATTERN = re.compile(r"^v\d+\.\d+\.\d+$")


def is_valid_processed_version(version: str) -> bool:
    """Return True when ``version`` matches ``vMAJOR.MINOR.PATCH``."""
    return bool(VERSION_PATTERN.match(version.strip()))


def processed_dir(version: str, *, repo_root: Path | None = None) -> Path:
    """Return ``data/processed/<version>/`` after validating the version string."""
    if not is_valid_processed_version(version):
        raise ValueError(f"Invalid processed dataset version: {version!r} (expected v0.1.0 style).")
    root = repo_root or Path(__file__).resolve().parents[2]
    return root / "data" / "processed" / version


def write_dataset_stats(
    report: DatasetValidationReport,
    *,
    version: str,
    output_dir: str | Path | None = None,
) -> Path:
    """Write ``validation_report.json`` under the processed version directory."""
    if output_dir is None:
        out_dir = processed_dir(version)
    else:
        out_dir = Path(output_dir)
    return write_validation_report(report, out_dir / "validation_report.json")


def render_dataset_card(
    *,
    version: str,
    train_report: DatasetValidationReport,
    val_report: DatasetValidationReport | None = None,
    scope: str = "Lite-VLA MVP starter dataset from reference frames, raw teleop, and augmentations.",
    limitations: str = "Augmentation-heavy; not representative of full deployment diversity.",
) -> str:
    """Render a markdown dataset card from validation reports."""
    generated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    lines = [
        f"# Dataset card — {version}",
        "",
        f"**Generated:** {generated_at}",
        "",
        "## Scope",
        "",
        scope,
        "",
        "## Files",
        "",
        f"- Train: `{train_report.jsonl_path}` ({train_report.record_count} rows)",
    ]
    if val_report is not None:
        lines.append(f"- Val: `{val_report.jsonl_path}` ({val_report.record_count} rows)")
    lines.extend(
        [
            "",
            "## Label distribution (train)",
            "",
        ]
    )
    for action, count in train_report.action_counts.items():
        lines.append(f"- `{action}`: {count}")
    lines.extend(["", "## Source mix (train)", ""])
    for source, count in train_report.source_counts.items():
        lines.append(f"- `{source}`: {count}")
    lines.extend(
        [
            "",
            "## Validation",
            "",
            f"- Train valid: **{'yes' if train_report.valid else 'no'}** "
            f"({train_report.error_count} errors, {train_report.warning_count} warnings)",
        ]
    )
    if val_report is not None:
        lines.append(
            f"- Val valid: **{'yes' if val_report.valid else 'no'}** "
            f"({val_report.error_count} errors, {val_report.warning_count} warnings)"
        )
    lines.extend(["", "## Limitations", "", limitations, ""])
    return "\n".join(lines)


def write_dataset_card(
    markdown: str,
    *,
    version: str,
    output_dir: str | Path | None = None,
) -> Path:
    """Write ``DATASET_CARD.md`` for a processed version."""
    if output_dir is None:
        out_dir = processed_dir(version)
    else:
        out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "DATASET_CARD.md"
    path.write_text(markdown, encoding="utf-8")
    return path


def build_version_artifacts(
    *,
    version: str,
    train_jsonl: str | Path,
    val_jsonl: str | Path | None = None,
    repo_root: Path | None = None,
    check_images: bool = True,
) -> dict[str, Any]:
    """Validate train/val JSONL and write stats + dataset card under ``data/processed/<version>/``."""
    train_report = validate_dataset(
        train_jsonl,
        repo_root=repo_root,
        check_images=check_images,
    )
    val_report = None
    if val_jsonl is not None and Path(val_jsonl).is_file():
        val_report = validate_dataset(
            val_jsonl,
            repo_root=repo_root,
            check_images=check_images,
        )

    out_dir = processed_dir(version, repo_root=repo_root)
    stats_path = write_dataset_stats(train_report, version=version, output_dir=out_dir)
    card_path = write_dataset_card(
        render_dataset_card(version=version, train_report=train_report, val_report=val_report),
        version=version,
        output_dir=out_dir,
    )
    if val_report is not None:
        write_validation_report(val_report, out_dir / "validation_report_val.json")

    return {
        "version": version,
        "output_dir": str(out_dir),
        "validation_report": str(stats_path),
        "dataset_card": str(card_path),
        "train_valid": train_report.valid,
        "val_valid": val_report.valid if val_report else None,
    }
