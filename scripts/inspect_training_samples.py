#!/usr/bin/env python3
"""Inspect formatted SFT samples before training (Epic 106 / 1036 / 10110)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from litevla.actions import ACTION_NAMES, is_valid_action  # noqa: E402
from litevla.data.schema import read_jsonl  # noqa: E402
from litevla.prompting import PROMPT_VERSIONS  # noqa: E402
from ml.finetune.format_dataset import (  # noqa: E402
    FormattedSFTExample,
    format_training_records,
)
from ml.finetune.prompt_template import ASSISTANT_PREFIX, IMAGE_TOKEN  # noqa: E402


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Manually review formatted training examples before fine-tuning."
    )
    parser.add_argument(
        "--input",
        default="data/fixtures/sample_train.jsonl",
        help="Epic 105 JSONL (converted on the fly) or already-formatted SFT JSONL.",
    )
    parser.add_argument(
        "--from-sft",
        action="store_true",
        help="Treat --input as already-formatted SFT JSONL.",
    )
    parser.add_argument(
        "--prompt-version",
        default="v1",
        choices=sorted(PROMPT_VERSIONS),
        help="Prompt version when converting Epic 105 JSONL.",
    )
    parser.add_argument(
        "--n",
        type=int,
        default=10,
        help="Number of samples to print (default: 10).",
    )
    parser.add_argument(
        "--check-image",
        action="store_true",
        help="Report whether image paths exist on disk.",
    )
    parser.add_argument(
        "--require-images",
        action="store_true",
        help="Fail inspection when any reviewed sample is missing its image file.",
    )
    return parser.parse_args()


def _load_sft_jsonl(path: Path) -> list[FormattedSFTExample]:
    examples: list[FormattedSFTExample] = []
    with path.open(encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            text = line.strip()
            if not text:
                continue
            raw = json.loads(text)
            try:
                examples.append(
                    FormattedSFTExample(
                        image_path=str(raw["image_path"]),
                        instruction=str(raw["instruction"]),
                        action=str(raw["action"]),
                        prompt=str(raw["prompt"]),
                        target=str(raw["target"]),
                        full_text=str(raw["full_text"]),
                        prompt_version=str(raw.get("prompt_version", "v1")),
                        id=str(raw["id"]) if raw.get("id") is not None else None,
                        source=str(raw["source"]) if raw.get("source") is not None else None,
                        episode_id=(
                            str(raw["episode_id"]) if raw.get("episode_id") is not None else None
                        ),
                        image_exists=raw.get("image_exists"),
                    )
                )
            except KeyError as exc:
                raise ValueError(f"{path}:{line_no}: missing field {exc}") from exc
    return examples


def _check_example(
    example: FormattedSFTExample,
    repo_root: Path,
    *,
    require_images: bool,
) -> tuple[list[str], list[str]]:
    """Return (hard_issues, soft_warnings)."""
    issues: list[str] = []
    warnings: list[str] = []
    if IMAGE_TOKEN not in example.prompt:
        issues.append("prompt missing <image> token")
    if not example.prompt.rstrip().endswith(ASSISTANT_PREFIX):
        issues.append(f"prompt does not end with {ASSISTANT_PREFIX}")
    if example.target != example.action:
        issues.append(f"target {example.target!r} != action {example.action!r}")
    if not is_valid_action(example.target):
        issues.append(f"invalid target action {example.target!r}")
    if not example.full_text.endswith(example.target):
        issues.append("full_text does not end with target action")
    if f"{ASSISTANT_PREFIX} {example.target}" in example.prompt:
        issues.append("action already present after ASSISTANT: in prompt")
    path = Path(example.image_path)
    if not path.is_absolute():
        path = repo_root / path
    if not path.is_file():
        message = f"image missing: {example.image_path}"
        if require_images:
            issues.append(message)
        else:
            warnings.append(message)
    return issues, warnings


def _print_example(
    index: int,
    example: FormattedSFTExample,
    issues: list[str],
    warnings: list[str],
) -> None:
    if issues:
        status = "ISSUES"
    elif warnings:
        status = "WARN"
    else:
        status = "OK"
    print(f"\n===== sample {index} [{status}] id={example.id} source={example.source} =====")
    print(f"image_path: {example.image_path}")
    print(f"instruction: {example.instruction}")
    print(f"target action: {example.target}")
    print(f"prompt_version: {example.prompt_version}")
    print("--- prompt (input / masked during loss) ---")
    print(example.prompt)
    print("--- target (trained tokens) ---")
    print(example.target)
    print("--- full_text (ends with target) ---")
    lines = example.full_text.splitlines()
    preview = "\n".join(lines[-6:]) if len(lines) > 6 else example.full_text
    print(preview)
    for issue in issues:
        print(f"  ! {issue}")
    for warning in warnings:
        print(f"  ~ {warning}")


def main() -> int:
    args = _parse_args()
    input_path = Path(args.input)
    if not input_path.is_file():
        print(f"ERROR: input not found: {input_path}", file=sys.stderr)
        return 1

    if args.from_sft:
        examples = _load_sft_jsonl(input_path)
    else:
        records = list(read_jsonl(input_path))
        examples = format_training_records(
            records,
            prompt_version=args.prompt_version,
            repo_root=ROOT,
            check_image=args.check_image or args.require_images,
        )

    if not examples:
        print("ERROR: no examples to inspect", file=sys.stderr)
        return 1

    n = min(max(args.n, 1), len(examples))
    print(f"Inspecting {n}/{len(examples)} samples from {input_path}")
    print(f"Allowed actions: {', '.join(ACTION_NAMES)}")

    issue_count = 0
    warn_count = 0
    for i, example in enumerate(examples[:n], start=1):
        issues, warnings = _check_example(
            example,
            ROOT,
            require_images=args.require_images,
        )
        if issues:
            issue_count += 1
        if warnings:
            warn_count += 1
        _print_example(i, example, issues, warnings)

    print(
        f"\nSummary: {n - issue_count}/{n} samples passed format checks"
        f" ({warn_count} with image warnings)"
    )
    if issue_count:
        print(f"ERROR: {issue_count} sample(s) failed format checks", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
