# Dataset fixtures (VLA-41)

Committed **schema examples** for Epic 105 — not the full 200+ training set.

| File | Purpose |
|------|---------|
| `sample_train.jsonl` | Validates against `data/schema/record.schema.json` in CI |

Image paths point at gitignored PNGs under `data/reference_images/` or future capture dirs. Tests validate **record shape and action tokens**, not that every image file exists on disk.

```bash
pytest tests/test_dataset_schema.py -q
```
