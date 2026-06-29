"""Training record schema for Lite-VLA JSONL datasets (VLA-41)."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterator

import jsonschema
from jsonschema import Draft202012Validator

from litevla.actions import parse_action

REPO_ROOT = Path(__file__).resolve().parents[2]
RECORD_SCHEMA_PATH = REPO_ROOT / "data" / "schema" / "record.schema.json"
FIXTURES_PATH = REPO_ROOT / "data" / "fixtures" / "sample_train.jsonl"


@dataclass(frozen=True)
class TrainingRecord:
    """One image-instruction-action row for supervised fine-tuning."""

    image_path: str
    instruction: str
    action: str
    timestamp: str
    source: str
    id: str | None = None
    episode_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class RecordSchemaError(ValueError):
    """Raised when a dataset record fails JSON Schema or action validation."""


def record_schema_path() -> Path:
    """Return the committed JSON Schema for training records."""
    return RECORD_SCHEMA_PATH


def load_record_schema() -> dict[str, Any]:
    """Load ``data/schema/record.schema.json``."""
    path = record_schema_path()
    if not path.is_file():
        raise FileNotFoundError(f"Dataset record schema not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _format_validation_error(error: jsonschema.ValidationError) -> str:
    path = " -> ".join(str(part) for part in error.absolute_path) or "<root>"
    return f"{path}: {error.message}"


def validate_record_dict(raw: dict[str, Any], *, schema: dict[str, Any] | None = None) -> None:
    """Validate a record mapping against the JSON Schema."""
    if not isinstance(raw, dict):
        raise RecordSchemaError(f"Record must be a mapping, got {type(raw).__name__}.")
    schema = schema or load_record_schema()
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(raw), key=lambda err: list(err.absolute_path))
    if errors:
        details = "; ".join(_format_validation_error(err) for err in errors)
        raise RecordSchemaError(details)


def parse_training_record(raw: dict[str, Any], *, schema: dict[str, Any] | None = None) -> TrainingRecord:
    """Validate and parse one training record."""
    validate_record_dict(raw, schema=schema)
    try:
        action = parse_action(str(raw["action"]))
    except ValueError as exc:
        raise RecordSchemaError(str(exc)) from exc

    metadata = raw.get("metadata")
    if metadata is None:
        meta: dict[str, Any] = {}
    elif isinstance(metadata, dict):
        meta = metadata
    else:
        raise RecordSchemaError("metadata must be an object when present.")

    return TrainingRecord(
        image_path=str(raw["image_path"]),
        instruction=str(raw["instruction"]),
        action=action,
        timestamp=str(raw["timestamp"]),
        source=str(raw["source"]),
        id=str(raw["id"]) if raw.get("id") is not None else None,
        episode_id=str(raw["episode_id"]) if raw.get("episode_id") is not None else None,
        metadata=meta,
    )


def training_record_to_dict(record: TrainingRecord) -> dict[str, Any]:
    """Serialize a :class:`TrainingRecord` for JSONL output."""
    out: dict[str, Any] = {
        "image_path": record.image_path,
        "instruction": record.instruction,
        "action": record.action,
        "timestamp": record.timestamp,
        "source": record.source,
    }
    if record.id is not None:
        out["id"] = record.id
    if record.episode_id is not None:
        out["episode_id"] = record.episode_id
    if record.metadata:
        out["metadata"] = record.metadata
    return out


def read_jsonl(path: str | Path, *, schema: dict[str, Any] | None = None) -> Iterator[TrainingRecord]:
    """Yield validated training records from a JSONL file."""
    file_path = Path(path)
    if not file_path.is_file():
        raise FileNotFoundError(f"JSONL dataset not found: {file_path}")
    loaded_schema = schema or load_record_schema()
    with file_path.open(encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            text = line.strip()
            if not text:
                continue
            try:
                raw = json.loads(text)
            except json.JSONDecodeError as exc:
                raise RecordSchemaError(f"{file_path}:{line_no}: invalid JSON: {exc}") from exc
            try:
                yield parse_training_record(raw, schema=loaded_schema)
            except RecordSchemaError as exc:
                raise RecordSchemaError(f"{file_path}:{line_no}: {exc}") from exc


def write_jsonl(path: str | Path, records: Iterator[TrainingRecord]) -> int:
    """Write training records as JSONL (one compact object per line). Returns row count."""
    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with file_path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(training_record_to_dict(record), separators=(",", ":")))
            handle.write("\n")
            count += 1
    return count
