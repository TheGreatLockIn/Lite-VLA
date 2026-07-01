"""PyTorch dataset loader for Lite-VLA training JSONL (Epic 105 / VLA-46)."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from litevla.data.schema import REPO_ROOT, TrainingRecord, read_jsonl

try:
    from torch.utils.data import Dataset
except ImportError:  # pragma: no cover - optional at import time in minimal envs
    Dataset = object  # type: ignore[misc, assignment]


ImageTransform = Callable[[Any], Any]


class LiteVLADataset(Dataset):
    """Load image-instruction-action rows from processed JSONL."""

    def __init__(
        self,
        jsonl_path: str | Path,
        *,
        repo_root: Path | None = None,
        transform: ImageTransform | None = None,
    ) -> None:
        self.jsonl_path = Path(jsonl_path)
        self.repo_root = repo_root or REPO_ROOT
        self.transform = transform
        self.records: list[TrainingRecord] = list(read_jsonl(self.jsonl_path))

    def __len__(self) -> int:
        return len(self.records)

    def resolve_image_path(self, record: TrainingRecord) -> Path:
        path = Path(record.image_path)
        if path.is_absolute():
            return path
        return self.repo_root / path

    def __getitem__(self, index: int) -> dict[str, Any]:
        record = self.records[index]
        from PIL import Image

        image_path = self.resolve_image_path(record)
        if not image_path.is_file():
            raise FileNotFoundError(f"Training image not found: {image_path}")

        image = Image.open(image_path).convert("RGB")
        if self.transform is not None:
            image = self.transform(image)

        return {
            "id": record.id,
            "image": image,
            "instruction": record.instruction,
            "action": record.action,
            "source": record.source,
            "episode_id": record.episode_id,
            "metadata": dict(record.metadata),
        }
