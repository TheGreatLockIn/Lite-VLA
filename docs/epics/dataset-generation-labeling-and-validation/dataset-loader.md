# Dataset loader for training

**Epic:** Dataset Generation, Labeling, and Validation (105) · **Jira epic:** VLA-6 · **Story:** VLA-46 / 1034 · **Subtasks:** 10102 (Dataset class), 10103 (transforms), 10104 (smoke test)

**Human-readable version (browser):** [`dataset-loader.html`](dataset-loader.html)

## Executive summary

VLA-46 provides **`LiteVLADataset`** — a `torch.utils.data.Dataset` that reads validated JSONL, loads RGB images from repo-relative paths, and returns image + instruction + action dicts for the Epic 106 fine-tuning pipeline. Optional `transform` hooks accept torchvision/VLM preprocessing.

## API contract and data flow

```text
train.jsonl ──> read_jsonl() ──> LiteVLADataset
                                    │
                    PIL RGB image ◄─┤ repo_root / image_path
                                    │
                                    ▼
              {id, image, instruction, action, source, episode_id, metadata}
                                    │
                                    ▼
                         DataLoader (batch) ──> training loop
```

| Output key | Type | Notes |
|------------|------|-------|
| `image` | PIL or tensor | RGB; `transform` applied when set |
| `instruction` | `str` | Training prompt text |
| `action` | `str` | Epic 103 token |
| `id` | `str \| None` | Traceability |

## Implementation breakdown

### `litevla/data/loader.py`

```python
dataset = LiteVLADataset("data/processed/v0.1.0/train.jsonl", transform=my_transform)
sample = dataset[0]
```

- **Design note:** Constructor calls `read_jsonl` — invalid rows fail at load time (pair with VLA-45 validator in CI).
- **Gotcha:** Images must exist locally; gitignored PNGs require local build or capture first.

### Transform pipeline (10103)

Pass any callable `transform(image) -> tensor` — typically torchvision `Compose([Resize, ToTensor, Normalize])` from the training script, not hard-coded in the loader.

## Verification patterns

```bash
pytest tests/test_dataset_loader.py -q
```

## Related

- [dataset-validation.md](dataset-validation.md) (VLA-45)
- [synthetic-starter-dataset.md](synthetic-starter-dataset.md) (VLA-43 input paths)
