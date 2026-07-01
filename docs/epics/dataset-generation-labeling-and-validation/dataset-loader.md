# Dataset loader for training

**Epic:** Dataset Generation, Labeling, and Validation (105) · **Jira epic:** VLA-6 · **Story:** VLA-46 / 1034 · **Subtasks:** 10102 (Dataset class), 10103 (transforms), 10104 (smoke test)

**Human-readable version (browser):** [`dataset-loader.html`](dataset-loader.html)

## Executive summary

VLA-46 bridges processed JSONL (VLA-41) into Epic 106 fine-tuning: **`LiteVLADataset`** is a `torch.utils.data.Dataset` that loads repo-relative RGB images with Pillow, returns instruction + Epic 103 action labels, and accepts an optional `transform` for torchvision/VLM preprocessing. The loader intentionally does not embed model-specific normalization — training scripts own the collator/transform pipeline.

## API contract and data flow

```text
train.jsonl ──> read_jsonl()  (fail-fast schema validation at init)
        │
        ▼
LiteVLADataset.__getitem__(i)
        │
        ├── resolve_image_path(record) ──> repo_root / image_path
        ├── PIL.Image.open().convert("RGB")
        ├── optional transform(image)
        └── dict { id, image, instruction, action, source, episode_id, metadata }
        │
        ▼
torch.utils.data.DataLoader  ──>  batch  ──>  Epic 106 training loop
```

| Output key | Type | Notes |
|------------|------|-------|
| `image` | `PIL.Image` or tensor | RGB before/after `transform` |
| `instruction` | `str` | Prompt text for VLA |
| `action` | `str` | One of five Epic 103 tokens |
| `id` | `str \| None` | Traceability / logging |
| `source` | `str` | `teleop`, `reference`, `synthetic`, `manual_review` |
| `episode_id` | `str \| None` | Groups capture session |
| `metadata` | `dict` | Review flags, sim stamps, etc. |

**Trade-off:** Eager `list(read_jsonl())` at init loads all metadata into RAM (fine for MVP ≤ few thousand rows); lazy indexing deferred until dataset size grows.

## Implementation breakdown

### Dataset class (10102) — `litevla/data/loader.py`

```python
class LiteVLADataset(Dataset):
    def __init__(self, jsonl_path, *, repo_root=None, transform=None):
        self.records = list(read_jsonl(self.jsonl_path))

    def __getitem__(self, index: int) -> dict[str, Any]:
        record = self.records[index]
        image = Image.open(self.resolve_image_path(record)).convert("RGB")
        if self.transform is not None:
            image = self.transform(image)
        return {"image": image, "instruction": record.instruction, "action": record.action, ...}
```

- **Design note:** `resolve_image_path()` mirrors `validator.resolve_image_path()` — same repo-relative contract.
- **Gotcha:** `__getitem__` raises `FileNotFoundError` if PNG missing; run VLA-45 validator before training to catch this earlier.

### Transform pipeline (10103)

Pass any callable `transform: (PIL.Image) -> tensor | PIL.Image`:

```python
from torchvision import transforms

preprocess = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
])
dataset = LiteVLADataset("data/processed/v0.1.0/train.jsonl", transform=preprocess)
```

- **Design note:** Loader stays model-agnostic; Epic 106 picks resize/normalize matching the VLM backbone.
- **Gotcha:** `DataLoader` default collate stacks tensors but not PIL images — always set `transform` before batching for training.

### Smoke test (10104)

```python
from torch.utils.data import DataLoader
loader = DataLoader(dataset, batch_size=2)
batch = next(iter(loader))
assert len(batch["action"]) == 2
```

Covered in `tests/test_dataset_loader.py` (DataLoader test skipped when torch not installed).

## Engineering decisions

**ADR: Fail-fast at init via read_jsonl (10102)**  
Status: Accepted  
Context: Corrupt JSONL should not surface mid-epoch.  
Decision: Constructor calls `read_jsonl()` which validates every row immediately.  
Alternatives rejected: Lazy per-row parse in `__getitem__` (harder to debug, uneven failure timing).

**ADR: Transform hook not built-in presets (10103)**  
Status: Accepted  
Context: VLM preprocessing varies by model (SmolVLM, LLaVA, etc.).  
Decision: Optional `transform` callable only; no hard-coded ImageNet norm in loader.  
Consequences: Epic 106 training script documents chosen transforms.

**ADR: torch import optional at module level**  
Status: Accepted  
Decision: `Dataset = object` fallback when torch absent so schema/validator tests run without torch.  
Consequences: `LiteVLADataset` only used in ML environments with `requirements/base.txt`.

## Verification patterns

```bash
pytest tests/test_dataset_loader.py -q
```

| Test | Contract defended |
|------|-------------------|
| `test_loader_reads_image_and_labels` | PIL RGB + action/instruction keys |
| `test_loader_batch_via_dataloader` | Batched `action` list (requires torch) |

## Related

- [dataset-validation.md](dataset-validation.md) (VLA-45 — run before training)
- [dataset-schema.md](dataset-schema.md) (VLA-41 record shape)
- [synthetic-starter-dataset.md](synthetic-starter-dataset.md) (VLA-43 produces input paths)

## Open questions

- **Lazy loading:** For >10k rows, consider LMDB or on-demand `__getitem__` parse without full eager list.
- **Action tokenization:** Loader returns string actions; Epic 106 owns integer mapping / prompt formatting.
