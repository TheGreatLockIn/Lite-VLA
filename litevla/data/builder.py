"""Build processed training datasets from raw episodes and reference frames (VLA-43)."""

from __future__ import annotations

import hashlib
import json
import random
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator, Sequence

import numpy as np
from PIL import Image, ImageEnhance, ImageFilter

from litevla.data.episode import read_episode_json
from litevla.data.schema import TrainingRecord, training_record_to_dict, validate_record_dict, write_jsonl

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REFERENCE_MANIFEST = REPO_ROOT / "data" / "reference_images" / "manifest.json"
DEFAULT_RAW_EPISODES_DIR = REPO_ROOT / "data" / "raw" / "episodes"
DEFAULT_PROCESSED_ROOT = REPO_ROOT / "data" / "processed"
DEFAULT_MAX_VARIANTS_PER_IMAGE = 25
FRAME_STAMP_RE = re.compile(r"^(\d+)_(\d{9})\.png$")

# Map raw episode source → training record source.
_EPISODE_SOURCE_MAP = {
    "teleop": "teleop",
    "dummy": "synthetic",
    "reference_script": "reference",
    "scripted": "synthetic",
}


@dataclass(frozen=True)
class ReferenceEntry:
    filename: str
    instruction: str
    action: str


@dataclass(frozen=True)
class ReferenceManifest:
    episode_id: str
    world: str
    entries: tuple[ReferenceEntry, ...]


@dataclass
class BuildStats:
    reference_base: int = 0
    synthetic_augmented: int = 0
    raw_episode: int = 0
    skipped_missing_image: int = 0


@dataclass
class BuildResult:
    version: str
    train_path: Path
    val_path: Path
    train_count: int
    val_count: int
    stats: BuildStats = field(default_factory=BuildStats)


class DatasetBuildError(ValueError):
    """Raised when dataset construction fails validation."""


def repo_relative(path: Path, *, repo_root: Path = REPO_ROOT) -> str:
    """Return a POSIX repo-relative path string."""
    resolved = path.resolve()
    return resolved.relative_to(repo_root.resolve()).as_posix()


def parse_frame_stamp(filename: str) -> tuple[int, int] | None:
    """Parse sim stamp from a frame filename like ``12_340000000.png``."""
    match = FRAME_STAMP_RE.match(filename)
    if not match:
        return None
    return int(match.group(1)), int(match.group(2))


def sim_stamp_to_ns(sim_sec: int, sim_nanosec: int) -> int:
    return sim_sec * 1_000_000_000 + sim_nanosec


def load_reference_manifest(path: str | Path | None = None) -> ReferenceManifest:
    manifest_path = Path(path) if path is not None else DEFAULT_REFERENCE_MANIFEST
    raw = json.loads(manifest_path.read_text(encoding="utf-8"))
    entries = tuple(
        ReferenceEntry(
            filename=str(item["filename"]),
            instruction=str(item["instruction"]),
            action=str(item["action"]),
        )
        for item in raw["entries"]
    )
    return ReferenceManifest(
        episode_id=str(raw.get("episode_id", "ref_capture_v1")),
        world=str(raw.get("world", "mvp_arena.wbt")),
        entries=entries,
    )


def read_raw_commands(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            text = line.strip()
            if text:
                rows.append(json.loads(text))
    rows.sort(
        key=lambda row: sim_stamp_to_ns(
            int(row.get("sim_stamp_sec", 0)),
            int(row.get("sim_stamp_nanosec", 0)),
        )
    )
    return rows


def _training_source_for_episode(episode_source: str) -> str:
    return _EPISODE_SOURCE_MAP.get(episode_source, "teleop")


def _action_at_sim_time(commands: Sequence[dict[str, Any]], sim_ns: int) -> dict[str, Any] | None:
    """Return the latest command at or before ``sim_ns``."""
    chosen: dict[str, Any] | None = None
    chosen_ns = -1
    for row in commands:
        row_ns = sim_stamp_to_ns(
            int(row.get("sim_stamp_sec", 0)),
            int(row.get("sim_stamp_nanosec", 0)),
        )
        if row_ns <= sim_ns and row_ns >= chosen_ns:
            chosen = row
            chosen_ns = row_ns
    return chosen


def records_from_raw_episode(
    episode_dir: Path,
    *,
    repo_root: Path = REPO_ROOT,
) -> tuple[list[TrainingRecord], int]:
    """Label each saved frame using the most recent command at or before its sim stamp."""
    episode_json = episode_dir / "episode.json"
    if not episode_json.is_file():
        return [], 0

    meta = read_episode_json(episode_dir)
    commands = read_raw_commands(episode_dir / "commands.jsonl")
    frames_dir = episode_dir / "frames"
    if not frames_dir.is_dir() or not commands:
        return [], 0

    source = _training_source_for_episode(meta.source)
    records: list[TrainingRecord] = []
    frame_paths = sorted(
        frames_dir.glob("*.png"),
        key=lambda path: parse_frame_stamp(path.name) or (0, 0),
    )

    for index, frame_path in enumerate(frame_paths):
        stamp = parse_frame_stamp(frame_path.name)
        if stamp is None:
            continue
        sim_ns = sim_stamp_to_ns(stamp[0], stamp[1])
        command = _action_at_sim_time(commands, sim_ns)
        if command is None:
            continue

        timestamp = str(command.get("stamp") or meta.started_at)
        record_id = f"raw_{meta.episode_id}_{index:04d}"
        records.append(
            TrainingRecord(
                image_path=repo_relative(frame_path, repo_root=repo_root),
                instruction=meta.instruction,
                action=str(command["action"]),
                timestamp=timestamp,
                source=source,
                id=record_id,
                episode_id=meta.episode_id,
                metadata={
                    "world": meta.world,
                    "sim_stamp_sec": stamp[0],
                    "sim_stamp_nanosec": stamp[1],
                    "linear_x": command.get("linear_x"),
                    "angular_z": command.get("angular_z"),
                },
            )
        )
    return records, len(records)


def records_from_reference_manifest(
    manifest: ReferenceManifest,
    *,
    images_dir: Path,
    repo_root: Path = REPO_ROOT,
    timestamp: str | None = None,
) -> tuple[list[TrainingRecord], int]:
    """One training row per reference PNG that exists on disk."""
    ts = timestamp or datetime.now(timezone.utc).isoformat()
    records: list[TrainingRecord] = []
    skipped = 0

    for index, entry in enumerate(manifest.entries):
        image_path = images_dir / entry.filename
        if not image_path.is_file():
            skipped += 1
            continue
        records.append(
            TrainingRecord(
                image_path=repo_relative(image_path, repo_root=repo_root),
                instruction=entry.instruction,
                action=entry.action,
                timestamp=ts,
                source="reference",
                id=f"ref_{index + 1:03d}",
                episode_id=manifest.episode_id,
                metadata={"world": manifest.world},
            )
        )
    return records, skipped


def _augmentation_rng(seed: int, stem: str, variant: int) -> random.Random:
    """Stable per-(seed, image, variant) RNG for reproducible augmentations."""
    payload = f"{seed}:{stem}:{variant}".encode()
    digest = hashlib.sha256(payload).digest()
    return random.Random(int.from_bytes(digest[:8], "big"))


def _apply_augmentation(image: Image.Image, variant: int, rng: random.Random) -> Image.Image:
    """Label-preserving augmentations for fixed-pose reference frames."""
    del variant  # entropy comes from ``rng``; index only names output files.
    out = image.convert("RGB")
    width, height = out.size

    out = ImageEnhance.Brightness(out).enhance(rng.uniform(0.65, 1.35))
    out = ImageEnhance.Contrast(out).enhance(rng.uniform(0.70, 1.30))
    out = ImageEnhance.Color(out).enhance(rng.uniform(0.75, 1.25))
    out = ImageEnhance.Sharpness(out).enhance(rng.uniform(0.55, 1.65))

    scale = rng.uniform(0.82, 0.97)
    crop_w = max(1, int(width * scale))
    crop_h = max(1, int(height * scale))
    max_left = max(0, width - crop_w)
    max_top = max(0, height - crop_h)
    left = rng.randint(0, max_left)
    top = rng.randint(0, max_top)
    out = out.crop((left, top, left + crop_w, top + crop_h))
    out = out.resize((width, height), Image.Resampling.LANCZOS)

    if rng.random() < 0.75:
        radius = rng.uniform(0.4, 1.6)
        out = out.filter(ImageFilter.GaussianBlur(radius=radius))

    arr = np.asarray(out, dtype=np.int16)
    sigma = rng.uniform(2.0, 14.0)
    noise = np.random.default_rng(rng.randint(0, 2**32 - 1)).normal(0.0, sigma, arr.shape)
    arr = np.clip(arr + noise, 0, 255).astype(np.uint8)
    out = Image.fromarray(arr)

    if rng.random() < 0.35:
        quality = int(rng.uniform(55, 92))
        from io import BytesIO

        buffer = BytesIO()
        out.save(buffer, format="JPEG", quality=quality)
        buffer.seek(0)
        out = Image.open(buffer).convert("RGB")

    return out


def compute_variants_per_image(
    *,
    base_count: int,
    current_total: int,
    min_records: int,
    max_variants_per_image: int,
    explicit_variants: int | None,
) -> int:
    """How many synthetic variants to emit per reference image."""
    if base_count <= 0:
        return 0
    needed = max(0, min_records - current_total)
    if needed == 0:
        return 0
    auto_variants = (needed + base_count - 1) // base_count
    per_image = max(auto_variants, 1)
    if explicit_variants is not None:
        per_image = max(explicit_variants, 0)
    # Hard cap only when a single reference image would dominate the dataset.
    if base_count == 1:
        return min(per_image, max_variants_per_image)
    return min(per_image, max(max_variants_per_image, auto_variants))


def augment_reference_records(
    base_records: Sequence[TrainingRecord],
    *,
    output_images_dir: Path,
    variants_per_image: int,
    seed: int,
    repo_root: Path = REPO_ROOT,
) -> list[TrainingRecord]:
    """Write augmented PNGs and return synthetic training rows."""
    if variants_per_image <= 0:
        return []

    output_images_dir.mkdir(parents=True, exist_ok=True)
    augmented: list[TrainingRecord] = []

    for base in base_records:
        base_image_path = repo_root / base.image_path
        if not base_image_path.is_file():
            continue
        image = Image.open(base_image_path)
        stem = Path(base.image_path).stem

        for variant in range(variants_per_image):
            variant_rng = _augmentation_rng(seed, stem, variant)
            aug_image = _apply_augmentation(image, variant, variant_rng)
            out_name = f"{stem}_aug_{variant:03d}.png"
            out_path = output_images_dir / out_name
            aug_image.save(out_path, format="PNG")

            record_id = f"syn_{stem}_{variant:03d}"
            augmented.append(
                TrainingRecord(
                    image_path=repo_relative(out_path, repo_root=repo_root),
                    instruction=base.instruction,
                    action=base.action,
                    timestamp=base.timestamp,
                    source="synthetic",
                    id=record_id,
                    episode_id=base.episode_id,
                    metadata={
                        **base.metadata,
                        "augmented_from": base.image_path,
                        "augment_variant": variant,
                    },
                )
            )
    return augmented


def split_records(
    records: Sequence[TrainingRecord],
    *,
    val_ratio: float,
    seed: int,
) -> tuple[list[TrainingRecord], list[TrainingRecord]]:
    """Shuffle deterministically and split; every record needs a unique ``id``."""
    if not 0.0 < val_ratio < 1.0:
        raise DatasetBuildError("val_ratio must be between 0 and 1.")

    ids = [record.id for record in records]
    if len(ids) != len(set(ids)):
        raise DatasetBuildError("Duplicate record ids detected before split.")

    shuffled = list(records)
    rng = random.Random(seed)
    rng.shuffle(shuffled)

    val_count = max(1, int(len(shuffled) * val_ratio))
    if len(shuffled) <= 1:
        return shuffled, []

    val_records = shuffled[:val_count]
    train_records = shuffled[val_count:]
    if not train_records:
        raise DatasetBuildError("Split would leave zero training records; reduce val_ratio.")
    return train_records, val_records


def _collect_raw_episode_records(
    raw_episodes_dir: Path,
    *,
    repo_root: Path,
) -> tuple[list[TrainingRecord], int]:
    if not raw_episodes_dir.is_dir():
        return [], 0

    all_records: list[TrainingRecord] = []
    for episode_dir in sorted(path for path in raw_episodes_dir.iterdir() if path.is_dir()):
        episode_records, _ = records_from_raw_episode(episode_dir, repo_root=repo_root)
        all_records.extend(episode_records)
    return all_records, len(all_records)


def build_starter_dataset(
    *,
    version: str = "v0.1.0",
    min_records: int = 200,
    val_ratio: float = 0.1,
    seed: int = 42,
    variants_per_image: int | None = None,
    max_variants_per_image: int = DEFAULT_MAX_VARIANTS_PER_IMAGE,
    reference_manifest_path: str | Path | None = None,
    reference_images_dir: str | Path | None = None,
    raw_episodes_dir: str | Path | None = None,
    processed_root: str | Path | None = None,
    repo_root: Path = REPO_ROOT,
    include_raw_episodes: bool = True,
) -> BuildResult:
    """Build train/val JSONL under ``data/processed/<version>/``."""
    stats = BuildStats()
    manifest = load_reference_manifest(reference_manifest_path)
    images_dir = Path(reference_images_dir) if reference_images_dir else repo_root / "data" / "reference_images"
    raw_dir = Path(raw_episodes_dir) if raw_episodes_dir else DEFAULT_RAW_EPISODES_DIR
    processed = Path(processed_root) if processed_root else DEFAULT_PROCESSED_ROOT
    version_dir = processed / version
    images_out = version_dir / "images"

    reference_records, skipped = records_from_reference_manifest(
        manifest,
        images_dir=images_dir,
        repo_root=repo_root,
    )
    stats.reference_base = len(reference_records)
    stats.skipped_missing_image = skipped

    all_records: list[TrainingRecord] = list(reference_records)

    if include_raw_episodes:
        raw_records, raw_count = _collect_raw_episode_records(raw_dir, repo_root=repo_root)
        all_records.extend(raw_records)
        stats.raw_episode = raw_count

    if len(all_records) < min_records:
        per_image = compute_variants_per_image(
            base_count=max(stats.reference_base, 1),
            current_total=len(all_records),
            min_records=min_records,
            max_variants_per_image=max_variants_per_image,
            explicit_variants=variants_per_image,
        )
        synthetic = augment_reference_records(
            reference_records,
            output_images_dir=images_out,
            variants_per_image=per_image,
            seed=seed,
            repo_root=repo_root,
        )
        all_records.extend(synthetic)
        stats.synthetic_augmented = len(synthetic)

    if len(all_records) < min_records:
        missing = [
            entry.filename
            for entry in manifest.entries
            if not (images_dir / entry.filename).is_file()
        ]
        hint = (
            f" Missing reference PNGs: {', '.join(missing)}."
            if missing
            else ""
        )
        raise DatasetBuildError(
            f"Only {len(all_records)} records produced; need at least {min_records}."
            f"{hint} "
            f"Augmentation is capped at {max_variants_per_image} variants/image — "
            "capture all reference frames (data/reference_images/) or raw episodes (VLA-42)."
        )

    for record in all_records:
        validate_record_dict(training_record_to_dict(record))

    train_records, val_records = split_records(all_records, val_ratio=val_ratio, seed=seed)
    train_path = version_dir / "train.jsonl"
    val_path = version_dir / "val.jsonl"
    train_count = write_jsonl(train_path, iter(train_records))
    val_count = write_jsonl(val_path, iter(val_records))

    return BuildResult(
        version=version,
        train_path=train_path,
        val_path=val_path,
        train_count=train_count,
        val_count=val_count,
        stats=stats,
    )


def iter_raw_episode_dirs(raw_episodes_dir: str | Path | None = None) -> Iterator[Path]:
    root = Path(raw_episodes_dir) if raw_episodes_dir else DEFAULT_RAW_EPISODES_DIR
    if not root.is_dir():
        return
    yield from sorted(path for path in root.iterdir() if path.is_dir())
