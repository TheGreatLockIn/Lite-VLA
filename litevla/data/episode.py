"""Raw simulation episode layout helpers (VLA-42)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import jsonschema
from jsonschema import Draft202012Validator
REPO_ROOT = Path(__file__).resolve().parents[2]
EPISODE_SCHEMA_PATH = REPO_ROOT / "data" / "schema" / "episode.schema.json"
DEFAULT_RAW_EPISODES_DIR = REPO_ROOT / "data" / "raw" / "episodes"


@dataclass(frozen=True)
class EpisodeMetadata:
    """Metadata for one raw capture under data/raw/episodes/<episode_id>/."""

    episode_id: str
    instruction: str
    source: str
    world: str
    started_at: str
    record_frames_hz: float
    schema_version: str = "1"
    notes: str | None = None


class EpisodeSchemaError(ValueError):
    """Raised when episode metadata fails validation."""


def episode_schema_path() -> Path:
    return EPISODE_SCHEMA_PATH


def load_episode_schema() -> dict[str, Any]:
    path = episode_schema_path()
    if not path.is_file():
        raise FileNotFoundError(f"Episode schema not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def new_episode_id(when: datetime | None = None) -> str:
    """UTC directory-safe episode id (matches command_recorder legacy stamp format)."""
    moment = when or datetime.now(timezone.utc)
    return moment.strftime("%Y%m%dT%H%M%SZ")


def validate_episode_dict(raw: dict[str, Any], *, schema: dict[str, Any] | None = None) -> None:
    schema = schema or load_episode_schema()
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(raw), key=lambda err: list(err.absolute_path))
    if errors:
        detail = errors[0].message
        raise EpisodeSchemaError(detail)


def episode_metadata_to_dict(meta: EpisodeMetadata) -> dict[str, Any]:
    out: dict[str, Any] = {
        "episode_id": meta.episode_id,
        "instruction": meta.instruction,
        "source": meta.source,
        "world": meta.world,
        "started_at": meta.started_at,
        "record_frames_hz": meta.record_frames_hz,
        "schema_version": meta.schema_version,
    }
    if meta.notes:
        out["notes"] = meta.notes
    return out


def write_episode_json(episode_dir: Path, meta: EpisodeMetadata) -> Path:
    """Write validated episode.json into an episode directory."""
    episode_dir.mkdir(parents=True, exist_ok=True)
    payload = episode_metadata_to_dict(meta)
    validate_episode_dict(payload)
    path = episode_dir / "episode.json"
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path


def init_raw_episode(
    *,
    base_dir: str | Path | None = None,
    instruction: str = "Move toward the red cube.",
    source: str = "teleop",
    world: str = "mvp_arena.wbt",
    record_frames_hz: float = 5.0,
    episode_id: str | None = None,
    notes: str | None = None,
) -> Path:
    """Create data/raw/episodes/<id>/ with episode.json and frames/ subdirectory."""
    root = Path(base_dir) if base_dir is not None else DEFAULT_RAW_EPISODES_DIR
    eid = episode_id or new_episode_id()
    started_at = datetime.now(timezone.utc).isoformat()
    episode_dir = root / eid
    frames_dir = episode_dir / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)

    meta = EpisodeMetadata(
        episode_id=eid,
        instruction=instruction,
        source=source,
        world=world,
        started_at=started_at,
        record_frames_hz=record_frames_hz,
        notes=notes,
    )
    write_episode_json(episode_dir, meta)
    return episode_dir


def frame_filename(sim_stamp_sec: int, sim_stamp_nanosec: int) -> str:
    """PNG filename aligned with camera_subscriber recording."""
    return f"{sim_stamp_sec}_{sim_stamp_nanosec:09d}.png"


def read_episode_json(episode_dir: str | Path) -> EpisodeMetadata:
    path = Path(episode_dir) / "episode.json"
    raw = json.loads(path.read_text(encoding="utf-8"))
    validate_episode_dict(raw)
    return EpisodeMetadata(
        episode_id=str(raw["episode_id"]),
        instruction=str(raw["instruction"]),
        source=str(raw["source"]),
        world=str(raw["world"]),
        started_at=str(raw["started_at"]),
        record_frames_hz=float(raw["record_frames_hz"]),
        schema_version=str(raw.get("schema_version", "1")),
        notes=str(raw["notes"]) if raw.get("notes") else None,
    )
