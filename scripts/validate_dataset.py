#!/usr/bin/env python3
"""Validate processed training JSONL and optionally write version artifacts (VLA-45, VLA-47)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from litevla.data.validator import (  # noqa: E402
    format_report_summary,
    validate_dataset,
    write_validation_report,
)
from litevla.data.versioning import build_version_artifacts  # noqa: E402


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate Lite-VLA processed JSONL datasets.")
    parser.add_argument("--jsonl", help="Single JSONL file to validate.")
    parser.add_argument("--train", help="Train JSONL (with --version for full artifacts).")
    parser.add_argument("--val", help="Optional val JSONL for version artifacts.")
    parser.add_argument("--version", help="Processed version id (e.g. v0.1.0) for stats + dataset card.")
    parser.add_argument("--repo-root", default=str(ROOT), help="Repo root for resolving image paths.")
    parser.add_argument("--skip-image-check", action="store_true", help="Do not require PNG files on disk.")
    parser.add_argument("--output", help="Write JSON validation report to this path.")
    parser.add_argument(
        "--write-artifacts",
        action="store_true",
        help="With --version, write validation_report.json and DATASET_CARD.md under data/processed/<version>/.",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    repo_root = Path(args.repo_root)
    check_images = not args.skip_image_check

    if args.version and args.write_artifacts:
        train_path = args.train or str(repo_root / "data" / "processed" / args.version / "train.jsonl")
        val_path = args.val or str(repo_root / "data" / "processed" / args.version / "val.jsonl")
        if not Path(train_path).is_file():
            print(f"Error: train JSONL not found: {train_path}", file=sys.stderr)
            return 1
        artifacts = build_version_artifacts(
            version=args.version,
            train_jsonl=train_path,
            val_jsonl=val_path if Path(val_path).is_file() else None,
            repo_root=repo_root,
            check_images=check_images,
        )
        print(f"Wrote artifacts under {artifacts['output_dir']}")
        print(f"  validation_report: {artifacts['validation_report']}")
        print(f"  dataset_card: {artifacts['dataset_card']}")
        return 0 if artifacts["train_valid"] else 1

    jsonl_path = args.jsonl or args.train
    if not jsonl_path:
        print("Error: pass --jsonl or --train (or --version --write-artifacts).", file=sys.stderr)
        return 1

    report = validate_dataset(jsonl_path, repo_root=repo_root, check_images=check_images)
    print(format_report_summary(report))

    if args.output:
        path = write_validation_report(report, args.output)
        print(f"\nWrote report → {path}")

    return 0 if report.valid else 1


if __name__ == "__main__":
    raise SystemExit(main())
