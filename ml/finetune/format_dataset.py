"""Convert Epic 105 training records into model-ready SFT JSONL (Epic 106 / 1036)."""

from __future__ import annotations

import json
from collections.abc import Iterator
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from litevla.data.schema import REPO_ROOT, TrainingRecord, read_jsonl

from ml.finetune.prompt_template import TrainingPromptTemplate


@dataclass(frozen=True)
class FormattedSFTExample:
    """One model-ready supervised fine-tuning example."""

    image_path: str
    instruction: str
    action: str
    prompt: str
    target: str
    full_text: str
    prompt_version: str
    id: str | None = None
    source: str | None = None
    episode_id: str | None = None
    image_exists: bool | None = None


def format_training_record(
    record: TrainingRecord,
    *,
    template: TrainingPromptTemplate | None = None,
    prompt_version: str = "v1",
    repo_root: Path | None = None,
    check_image: bool = False,
) -> FormattedSFTExample:
    """Convert one :class:`TrainingRecord` into an SFT example."""
    tmpl = template or TrainingPromptTemplate(version=prompt_version)
    parts = tmpl.build(record.instruction, record.action)

    image_exists: bool | None = None
    if check_image:
        root = repo_root or REPO_ROOT
        path = Path(record.image_path)
        if not path.is_absolute():
            path = root / path
        image_exists = path.is_file()

    return FormattedSFTExample(
        id=record.id,
        image_path=record.image_path,
        instruction=record.instruction,
        action=record.action,
        prompt=parts.prompt,
        target=parts.target,
        full_text=parts.full_text,
        prompt_version=parts.prompt_version,
        source=record.source,
        episode_id=record.episode_id,
        image_exists=image_exists,
    )


def format_training_records(
    records: Iterator[TrainingRecord] | list[TrainingRecord],
    *,
    prompt_version: str = "v1",
    repo_root: Path | None = None,
    check_image: bool = False,
) -> list[FormattedSFTExample]:
    """Format many training records with a shared prompt template."""
    template = TrainingPromptTemplate(version=prompt_version)
    return [
        format_training_record(
            record,
            template=template,
            repo_root=repo_root,
            check_image=check_image,
        )
        for record in records
    ]


def formatted_example_to_dict(example: FormattedSFTExample) -> dict[str, Any]:
    """Serialize a formatted example for JSONL (omit None optional fields)."""
    raw = asdict(example)
    return {key: value for key, value in raw.items() if value is not None}


def write_sft_jsonl(path: str | Path, examples: list[FormattedSFTExample]) -> int:
    """Write formatted SFT examples as JSONL. Returns row count."""
    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with file_path.open("w", encoding="utf-8") as handle:
        for example in examples:
            handle.write(json.dumps(formatted_example_to_dict(example), separators=(",", ":")))
            handle.write("\n")
            count += 1
    return count


def convert_jsonl_to_sft(
    input_jsonl: str | Path,
    output_jsonl: str | Path,
    *,
    prompt_version: str = "v1",
    repo_root: Path | None = None,
    check_image: bool = False,
) -> list[FormattedSFTExample]:
    """Read Epic 105 JSONL, format SFT examples, and write an output JSONL."""
    records = list(read_jsonl(input_jsonl))
    examples = format_training_records(
        records,
        prompt_version=prompt_version,
        repo_root=repo_root,
        check_image=check_image,
    )
    write_sft_jsonl(output_jsonl, examples)
    return examples
