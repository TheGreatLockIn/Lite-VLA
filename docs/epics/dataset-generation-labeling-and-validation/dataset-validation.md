# Dataset validation checks

**Epic:** Dataset Generation, Labeling, and Validation (105) · **Jira epic:** VLA-6 · **Story:** VLA-45 / 1033 · **Subtasks:** 10099 (schema), 10100 (images), 10101 (distribution)

**Human-readable version (browser):** [`dataset-validation.html`](dataset-validation.html)

## Executive summary

VLA-45 owns the **automated quality gate** on processed JSONL before fine-tuning and after human review (VLA-44). Unlike `read_jsonl()` which fails on the first bad row, `validate_dataset()` scans the entire file, collects every schema/filesystem problem with line numbers, and emits action/source distribution summaries with imbalance warnings. Output feeds CI, the CLI, and VLA-47 `validation_report.json` artifacts.

## API contract and data flow

```text
train.jsonl ──> validate_dataset()
                  ├── per-line: JSON parse
                  ├── parse_training_record()  (VLA-41 schema + Epic 103 action)
                  ├── resolve_image_path() + is_file()   [optional]
                  ├── duplicate id tracking
                  └── Counter: action + source
              ──> DatasetValidationReport
                      ├── valid (error_count == 0)
                      ├── action_counts / source_counts
                      └── issues[] with code + line + record_id
              ──> validation_report.json  (via write_validation_report)
              ──> CLI summary            (via format_report_summary)
```

| Check | Severity | Code | When |
|-------|----------|------|------|
| Blank line | warning | `empty_line` | Skipped; counted in issues |
| Invalid JSON | error | `invalid_json` | Malformed line |
| Schema / action | error | `schema_invalid` | Fails `record.schema.json` or `parse_action()` |
| Missing PNG | error | `missing_image` | `check_images=True` and file absent |
| Duplicate `id` | error | `duplicate_id` | Same id on two valid rows |
| Empty file | error | `empty_dataset` | Zero valid records |
| Missing `id` | warning | `missing_id` | `require_unique_ids=True` |
| One action > 50% | warning | `action_imbalance` | `warn_on_imbalance=True` |
| Missing action token | warning | `missing_action_coverage` | Dataset ≥ 5 rows but action absent |

**Trade-off:** Collect-all-errors scanning (non-throwing) vs fail-fast `read_jsonl()` — validator is for QA reports; loader/builder still fail-fast on first bad row.

## Implementation breakdown

### Report types (`litevla/data/validator.py`)

```python
@dataclass(frozen=True)
class ValidationIssue:
    severity: str  # error | warning
    code: str
    message: str
    line: int | None = None
    record_id: str | None = None

@dataclass
class DatasetValidationReport:
    jsonl_path: str
    record_count: int
    error_count: int
    warning_count: int
    action_counts: dict[str, int]
    source_counts: dict[str, int]
    ...
    @property
    def valid(self) -> bool:
        return self.error_count == 0
```

- **Design note:** `valid` ignores warnings — imbalance and missing-id are informational, not blockers.
- **Gotcha:** Warnings still appear in `issues[]` and increment `warning_count`; read both counts in CI.

### Schema validation (10099)

Reuses VLA-41 stack per line:

```python
record = parse_training_record(raw, schema=schema)
```

Defends: required fields, enum `source`, Epic 103 `action`, `additionalProperties: false`.

### Image path validation (10100)

```python
def resolve_image_path(image_path: str, *, repo_root: Path) -> Path:
    path = Path(image_path)
    if path.is_absolute():
        return path
    return repo_root / path
```

- **Design note:** Same resolution rule as `LiteVLADataset` (VLA-46) — one contract for validate and train.
- **Gotcha:** CI on fixtures-only checkouts uses `--skip-image-check`; PNGs are gitignored.

### Label distribution report (10101)

After scan, `action_counts` and `source_counts` populate the report. Warnings fire when:

- Top action exceeds `IMBALANCE_WARNING_RATIO` (0.5)
- Any of the five `ACTION_NAMES` missing when `record_count >= 5`

### CLI (`scripts/validate_dataset.py`)

```bash
# Single file
python scripts/validate_dataset.py --jsonl data/processed/v0.1.0/train.jsonl

# Fixtures without PNGs on disk
python scripts/validate_dataset.py --jsonl data/fixtures/sample_train.jsonl --skip-image-check

# JSON report
python scripts/validate_dataset.py --jsonl data/processed/v0.1.0/train.jsonl \
  --output data/processed/v0.1.0/validation_report.json

# Full version artifacts (VLA-47)
python scripts/validate_dataset.py --version v0.1.0 --write-artifacts
```

Exit code: `0` if `report.valid`, else `1`.

## Engineering decisions

**ADR: Collect-all-errors validator (10099)**  
Status: Accepted  
Context: `read_jsonl()` stops at first `RecordSchemaError`; QA needs a full issue list.  
Decision: `validate_dataset()` never raises on row errors; aggregates into `DatasetValidationReport`.  
Alternatives rejected: Wrap `read_jsonl` in try/except loop (loses line context on some paths).

**ADR: Image check optional (10100)**  
Status: Accepted  
Context: Fixture JSONL commits without PNGs; CI must validate schema without local images.  
Decision: `check_images` flag; default `True` for release builds, `False` for schema-only CI.  
Consequences: `run_ci_checks` / pytest use `check_images=False` on fixtures.

**ADR: Imbalance as warning not error (10101)**  
Status: Accepted  
Context: Starter dataset (VLA-43) is augmentation-heavy by design.  
Decision: `action_imbalance` is warning at 50% threshold; does not set `valid=False`.  
Consequences: Epic 106 training can proceed; team reviews warnings in `validation_report.json`.

## Verification patterns

```bash
pytest tests/test_dataset_validator.py -q
python scripts/validate_dataset.py --jsonl data/fixtures/sample_train.jsonl --skip-image-check
```

| Test | Contract defended |
|------|-------------------|
| `test_validate_fixtures_schema_only` | Six fixture rows pass schema |
| `test_validate_missing_image_is_error` | `missing_image` code |
| `test_validate_duplicate_id` | Duplicate detection |
| `test_validate_action_imbalance_warning` | Warning without invalid |
| `test_write_validation_report` | JSON round-trip |

## Related

- [dataset-schema.md](dataset-schema.md) (VLA-41 schema under test)
- [labeling-workflow.md](labeling-workflow.md) (VLA-44 — run validator after import)
- [dataset-versioning.md](dataset-versioning.md) (VLA-47 — consumes reports)
- [dataset-loader.md](dataset-loader.md) (VLA-46 — fail-fast load after validate in CI)

## Open questions

- **Pending review rows:** Pass `--review-csv` to `validate_dataset()` / CLI to fail release when any row is still `pending` (implemented 2026-07-02).
- **Val split in CI:** Validate `val.jsonl` separately in release pipeline (supported via `build_version_artifacts`).
