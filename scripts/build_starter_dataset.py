#!/usr/bin/env python3
"""Build the Lite-VLA starter processed dataset (Epic 105 / VLA-43)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from litevla.data.builder import BuildResult, DatasetBuildError, build_starter_dataset
from litevla.data.versioning import build_version_artifacts


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build processed train/val JSONL from reference frames and raw episodes.",
    )
    parser.add_argument("--version", default="v0.1.0", help="Processed dataset version directory.")
    parser.add_argument("--min-records", type=int, default=200, help="Minimum total records (train+val).")
    parser.add_argument("--val-ratio", type=float, default=0.1, help="Validation fraction (0-1).")
    parser.add_argument("--seed", type=int, default=42, help="Shuffle/augmentation seed.")
    parser.add_argument(
        "--variants-per-image",
        type=int,
        default=None,
        help="Augmented PNGs per reference image (auto-computed to reach min-records if omitted).",
    )
    parser.add_argument(
        "--max-variants-per-image",
        type=int,
        default=25,
        help="Upper bound on synthetic variants per reference PNG (default: 25).",
    )
    parser.add_argument(
        "--reference-manifest",
        default="data/reference_images/manifest.json",
        help="Reference image label manifest.",
    )
    parser.add_argument(
        "--reference-images-dir",
        default="data/reference_images",
        help="Directory containing reference PNGs.",
    )
    parser.add_argument(
        "--raw-episodes-dir",
        default="data/raw/episodes",
        help="Raw capture episodes from VLA-42.",
    )
    parser.add_argument(
        "--skip-raw-episodes",
        action="store_true",
        help="Do not ingest data/raw/episodes (reference + synthetic only).",
    )
    parser.add_argument(
        "--write-artifacts",
        action="store_true",
        help="After build, run validation and write DATASET_CARD.md + validation_report.json (VLA-47).",
    )
    parser.add_argument(
        "--skip-image-check",
        action="store_true",
        help="Pass --skip-image-check to post-build validation (e.g. partial image checkout).",
    )
    return parser.parse_args()


def _print_summary(result: BuildResult) -> None:
    stats = result.stats
    print(f"Dataset version: {result.version}")
    print(f"Train: {result.train_path} ({result.train_count} rows)")
    print(f"Val:   {result.val_path} ({result.val_count} rows)")
    print(
        "Sources:"
        f" reference={stats.reference_base},"
        f" synthetic={stats.synthetic_augmented},"
        f" raw_episode={stats.raw_episode},"
        f" skipped_missing={stats.skipped_missing_image}"
    )


def main() -> int:
    args = _parse_args()
    try:
        result = build_starter_dataset(
            version=args.version,
            min_records=args.min_records,
            val_ratio=args.val_ratio,
            seed=args.seed,
            variants_per_image=args.variants_per_image,
            max_variants_per_image=args.max_variants_per_image,
            reference_manifest_path=args.reference_manifest,
            reference_images_dir=args.reference_images_dir,
            raw_episodes_dir=args.raw_episodes_dir,
            include_raw_episodes=not args.skip_raw_episodes,
        )
    except DatasetBuildError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    _print_summary(result)

    if args.write_artifacts:
        artifacts = build_version_artifacts(
            version=result.version,
            train_jsonl=result.train_path,
            val_jsonl=result.val_path,
            check_images=not args.skip_image_check,
        )
        print(f"Artifacts: {artifacts['dataset_card']}")
        if not artifacts["train_valid"]:
            print("WARNING: train validation failed — see validation_report.json", file=sys.stderr)
            return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
