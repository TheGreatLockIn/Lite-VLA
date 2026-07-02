#!/usr/bin/env python3
"""Smoke-test LiteVLADataset + DataLoader on processed JSONL (Epic 105 / VLA-46)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from litevla.data.loader import LiteVLADataset  # noqa: E402
from litevla.data.validator import format_report_summary, validate_dataset  # noqa: E402


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Load one batch from processed train JSONL.")
    parser.add_argument(
        "--jsonl",
        default="data/processed/v0.1.0/train.jsonl",
        help="Processed JSONL path.",
    )
    parser.add_argument("--batch-size", type=int, default=4, help="DataLoader batch size.")
    parser.add_argument("--skip-validate", action="store_true", help="Skip pre-load validation.")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    jsonl_path = Path(args.jsonl)
    if not jsonl_path.is_file():
        print(f"ERROR: JSONL not found: {jsonl_path}", file=sys.stderr)
        return 1

    if not args.skip_validate:
        report = validate_dataset(jsonl_path, repo_root=ROOT, check_images=True)
        print(format_report_summary(report))
        print()
        if not report.valid:
            return 1

    try:
        import torch
        from torch.utils.data import DataLoader
    except ImportError:
        dataset = LiteVLADataset(jsonl_path, repo_root=ROOT)
        sample = dataset[0]
        print(f"Loaded 1 sample without torch: id={sample['id']} action={sample['action']}")
        print(f"  image size={sample['image'].size} instruction={sample['instruction'][:60]!r}")
        print("Install torch to run DataLoader batch smoke test.")
        return 0

    dataset = LiteVLADataset(jsonl_path, repo_root=ROOT)
    loader = DataLoader(dataset, batch_size=min(args.batch_size, len(dataset)))
    batch = next(iter(loader))
    print(f"Dataset rows: {len(dataset)}")
    print(f"Batch actions: {batch['action']}")
    print(f"Batch instructions: {len(batch['instruction'])}")
    images = batch["image"]
    if isinstance(images, list):
        print(f"Batch images: {len(images)} PIL frames, first size={images[0].size}")
    else:
        print(f"Batch images tensor shape: {tuple(images.shape)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
