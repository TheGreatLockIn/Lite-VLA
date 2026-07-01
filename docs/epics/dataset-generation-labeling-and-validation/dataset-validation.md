# Dataset validation checks

**Epic:** Dataset Generation, Labeling, and Validation (105) · **Jira epic:** VLA-6 · **Story:** VLA-45 / 1033 · **Subtasks:** 10099 (schema), 10100 (images), 10101 (distribution)

**Human-readable version (browser):** [`dataset-validation.html`](dataset-validation.html)

## Executive summary

VLA-45 owns the **quality gate** on processed JSONL before fine-tuning: collect schema errors per line, verify image files exist on disk, detect duplicate ids, and emit action/source distribution summaries with imbalance warnings. Output is a machine-readable `validation_report.json` plus a human CLI summary.

## API contract and data flow

```text
train.jsonl ──> validate_dataset()
                  ├── per-line JSON + schema + parse_action
                  ├── image_path exists under repo_root
                  ├── duplicate id detection
                  └── action/source counters + imbalance warnings
              ──> DatasetValidationReport ──> validation_report.json
```

| Check | Severity | Code |
|-------|----------|------|
| Invalid JSON line | error | `invalid_json` |
| Schema / action enum | error | `schema_invalid` |
| Missing PNG | error | `missing_image` |
| Duplicate `id` | error | `duplicate_id` |
| Empty dataset | error | `empty_dataset` |
| Missing `id` | warning | `missing_id` |
| One action > 50% of rows | warning | `action_imbalance` |
| Missing action coverage | warning | `missing_action_coverage` |

## Implementation breakdown

### Core (`litevla/data/validator.py`)

- **`validate_dataset`** — non-throwing collector; scans entire file before reporting
- **`write_validation_report`** — JSON artifact for VLA-47 stats
- **`format_report_summary`** — CLI-friendly text

### CLI (`scripts/validate_dataset.py`)

```bash
python scripts/validate_dataset.py --jsonl data/processed/v0.1.0/train.jsonl
python scripts/validate_dataset.py --jsonl data/fixtures/sample_train.jsonl --skip-image-check
python scripts/validate_dataset.py --version v0.1.0 --write-artifacts
```

## Verification patterns

```bash
pytest tests/test_dataset_validator.py -q
```

## Related

- [dataset-schema.md](dataset-schema.md) (VLA-41)
- [labeling-workflow.md](labeling-workflow.md) (VLA-44)
- [dataset-versioning.md](dataset-versioning.md) (VLA-47 stats output)
