#!/usr/bin/env python3
"""Convert Epic 105 JSONL into supervised fine-tuning format (Epic 106 / 1036)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from litevla.prompting import PROMPT_VERSIONS  # noqa: E402
from ml.finetune.format_dataset import convert_jsonl_to_sft  # noqa: E402


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert processed training JSONL into model-ready SFT JSONL."
    )
    parser.add_argument(
        "--input",
        default="data/fixtures/sample_train.jsonl",
        help="Epic 105 training JSONL path.",
    )
    parser.add_argument(
        "--output",
        default="data/processed/v0.1.0/sft_train.jsonl",
        help="Output path for formatted SFT JSONL.",
    )
    parser.add_argument(
        "--prompt-version",
        default="v1",
        choices=sorted(PROMPT_VERSIONS),
        help="Prompt template version (must match inference).",
    )
    parser.add_argument(
        "--check-image",
        action="store_true",
        help="Record whether each image_path resolves on disk.",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    input_path = Path(args.input)
    if not input_path.is_file():
        print(f"ERROR: input JSONL not found: {input_path}", file=sys.stderr)
        return 1

    examples = convert_jsonl_to_sft(
        input_path,
        args.output,
        prompt_version=args.prompt_version,
        repo_root=ROOT,
        check_image=args.check_image,
    )
    missing = sum(1 for ex in examples if ex.image_exists is False)
    print(f"Wrote {len(examples)} SFT examples → {args.output}")
    print(f"Prompt version: {args.prompt_version}")
    if args.check_image:
        print(f"Images missing on disk: {missing}/{len(examples)}")
    if examples:
        sample = examples[0]
        print("--- first sample ---")
        print(f"id={sample.id} action={sample.target}")
        print(f"image_path={sample.image_path}")
        print(f"prompt ends with: {sample.prompt[-20:]!r}")
        print(f"target={sample.target!r}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
