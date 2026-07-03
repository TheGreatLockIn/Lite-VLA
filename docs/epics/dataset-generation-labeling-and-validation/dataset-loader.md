# Dataset loader for training

**Epic:** Dataset Generation, Labeling, and Validation (105) · **Jira epic:** VLA-6 · **Story:** VLA-46 / 1034 · **Subtasks:** 10102 (Dataset class), 10103 (transforms), 10104 (smoke test)

**Human-readable version (browser):** [`dataset-loader.html`](dataset-loader.html)

## Executive summary

VLA-46 bridges processed JSONL (VLA-41) into Epic 106 fine-tuning: **`LiteVLADataset`** is a `torch.utils.data.Dataset` that loads repo-relative RGB images with Pillow, returns instruction + Epic 103 action labels, and accepts an optional `transform` for torchvision/VLM preprocessing. The loader intentionally does not embed model-specific normalization — training scripts own the collator/transform pipeline.

## Mental model

Think of the loader as a **typed iterator over validated rows**, not a training loop.

It exists because PyTorch expects `__getitem__` dicts with tensors/images, while the dataset epic standardized on JSONL + schema validation upstream.

The key engineering tension is **eager validation vs lazy I/O**: parsing all JSONL at init catches corrupt files before epoch 0, but loads metadata into RAM.

A beginner mistake is batching PIL images without a `transform`, or assuming the loader tokenizes actions for the VLM.

A senior engineer watches for **path resolution parity** — loader and validator must resolve `image_path` identically.

## Backstory: why this exists

Training scripts could open JSONL and PIL images ad hoc. The naive approach duplicates schema checks and path logic in every experiment script.

That breaks when one script uses cwd-relative paths and another uses repo-root joins — flaky `FileNotFoundError` mid-epoch.

So this design chooses a small `Dataset` wrapper: `read_jsonl()` at init, shared `resolve_image_path()`, optional `transform` hook for Epic 106.

## Prerequisites

- VLA-41 JSONL contract: [dataset-schema.md](dataset-schema.md)
- PyTorch `Dataset` / `DataLoader` basics
- Run VLA-45 before training: [dataset-validation.md](dataset-validation.md)

## Vocabulary

| Term | Meaning in this project |
|------|-------------------------|
| **`LiteVLADataset`** | `torch.utils.data.Dataset` over one JSONL file |
| **`transform`** | Callable `(PIL.Image) -> tensor \| PIL.Image` |
| **`repo_root`** | Repository root for repo-relative `image_path` |
| **`__getitem__` output** | Dict with `image`, `instruction`, `action`, metadata fields |

## Guided code reading

1. `litevla/data/loader.py` — full file is short; read top to bottom.
2. `tests/test_dataset_loader.py` — image load + DataLoader batch test.
3. `scripts/smoke_dataset_loader.py` — manual smoke on processed JSONL.
4. Epic 106 training script (when wired) — who supplies `transform` and collator.

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
| `metadata` | `dict` | Review flags, sim stamps, etc. |

### Naive approach vs chosen approach

| Approach | Why it seems attractive | Why we did or did not choose it |
|----------|-------------------------|----------------------------------|
| Lazy per-row parse in `__getitem__` | Lower init RAM | Corrupt JSONL fails mid-epoch |
| Built-in ImageNet normalize | Convenient | Wrong for arbitrary VLM backbones |
| Eager `read_jsonl()` at init | Fail before training | Predictable errors; fine for MVP scale |
| Optional `transform` hook | Caller must configure | Keeps loader model-agnostic |

## Implementation breakdown

### Dataset class (10102)

**Snippet** (`litevla/data/loader.py`):

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

**Risks and gotchas:** `__getitem__` raises `FileNotFoundError` if PNG missing — run VLA-45 first.

---

### Transform pipeline (10103)

```python
from torchvision import transforms

preprocess = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
])
dataset = LiteVLADataset("data/processed/v0.1.0/train.jsonl", transform=preprocess)
```

**Risks and gotchas:** Default `DataLoader` collate stacks tensors but not PIL images — set `transform` before batching.

---

### Optional torch import

When torch is absent, `Dataset = object` fallback lets schema/validator tests run without ML dependencies.

## Engineering decisions

```text
ADR: Fail-fast at init via read_jsonl (10102)
Status: Accepted
Decision: Constructor calls read_jsonl() which validates every row immediately.
Alternatives Rejected: Lazy per-row parse in __getitem__.
```

```text
ADR: Transform hook not built-in presets (10103)
Status: Accepted
Decision: Optional transform callable only; Epic 106 owns VLM-specific normalization.
```

## Verification patterns and failure modes

```bash
pytest tests/test_dataset_loader.py -q
python scripts/smoke_dataset_loader.py --jsonl data/processed/v0.1.0/train_reviewed.jsonl
```

| Symptom | Likely cause | Investigation | Fix |
|---------|--------------|---------------|-----|
| `FileNotFoundError` on image | Missing PNG or wrong `repo_root` | Compare path to validator output | Fix paths or add images |
| `RecordSchemaError` at init | Bad JSONL | Run `validate_dataset` | Fix upstream data |
| DataLoader stack error | PIL images without transform | Inspect batch type | Add `ToTensor` transform |
| Test skipped | torch not installed | Check CI env | Install `requirements/base.txt` |

## Engineering principle taught by this task

**Push model-specific preprocessing to the training boundary.** The dataset layer delivers consistent RGB + labels; the fine-tuning script owns tensor dtype, resize, and tokenization policy.

## Active learning checks

1. Why validate all JSONL rows in `__init__` instead of lazily?
2. Who owns action → token id mapping for the VLM?
3. Why does `resolve_image_path` mirror the validator?
4. What breaks if you pass `batch_size>1` without `transform`?

## Open questions

- **Lazy loading:** For >10k rows, consider on-demand parse without full eager list.
- **Action tokenization:** Loader returns string actions; Epic 106 owns integer mapping / prompt formatting.

## Related

- [dataset-validation.md](dataset-validation.md) (VLA-45 — run before training)
- [dataset-schema.md](dataset-schema.md) (VLA-41 record shape)
- [synthetic-starter-dataset.md](synthetic-starter-dataset.md) (VLA-43 produces input paths)
