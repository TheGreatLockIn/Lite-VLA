# Dataset validation checks

**Epic:** Dataset Generation, Labeling, and Validation (105) · **Jira epic:** VLA-6 · **Story:** VLA-45 / 1033 · **Subtasks:** 10099 (schema), 10100 (images), 10101 (distribution)

**Human-readable version (browser):** [`dataset-validation.html`](dataset-validation.html)

## Executive summary

VLA-45 owns the **automated quality gate** on processed JSONL before fine-tuning and after human review (VLA-44). Unlike `read_jsonl()` which fails on the first bad row, `validate_dataset()` scans the entire file, collects every schema/filesystem problem with line numbers, and emits action/source distribution summaries with imbalance warnings. Output feeds CI, the CLI, and VLA-47 `validation_report.json` artifacts.

## Mental model

Think of the validator as a **pre-flight checklist with a printed diagnostic report**.

It exists because dataset bugs are expensive — a missing PNG or duplicate `id` discovered mid-epoch wastes GPU time and produces confusing loss curves.

The key engineering tension is **fail-fast loading vs collect-all-errors QA**: training wants to stop immediately; release review wants every issue in one pass.

A beginner mistake is running training without validation, or treating imbalance **warnings** as hard failures.

A senior engineer watches for **`report.valid` vs `warning_count`** — warnings inform release notes; only errors block `valid`.

## Backstory: why this exists

Wrapping `read_jsonl()` in a try/except loop seems enough for QA. The naive approach stops at the first bad line.

That breaks because a spreadsheet import may introduce dozens of bad actions — you need line numbers for *all* of them before sending work back to reviewers.

So this design chooses a non-throwing scanner that aggregates `ValidationIssue` objects into `DatasetValidationReport`, with optional image and review-CSV gates.

## Prerequisites

- VLA-41 schema: [dataset-schema.md](dataset-schema.md)
- Optional VLA-44 review CSV: [labeling-workflow.md](labeling-workflow.md)

## Vocabulary

| Term | Meaning in this project |
|------|-------------------------|
| **`DatasetValidationReport`** | Aggregated scan result for one JSONL file |
| **`ValidationIssue`** | One error or warning with `code`, `line`, `record_id` |
| **`report.valid`** | True when `error_count == 0` (warnings allowed) |
| **`resolve_image_path`** | Repo-root join rule shared with VLA-46 loader |
| **`action_imbalance`** | Warning when one action exceeds 50% of rows |

## Guided code reading

1. `litevla/data/validator.py` — `validate_dataset`, issue codes, `IMBALANCE_WARNING_RATIO`.
2. `scripts/validate_dataset.py` — CLI flags (`--skip-image-check`, `--review-csv`, `--write-artifacts`).
3. `tests/test_dataset_validator.py` — contracts per issue type.
4. `litevla/data/versioning.py` — consumes reports for release artifacts.

## API contract and data flow

```text
train.jsonl ──> validate_dataset()
                  ├── per-line: JSON parse
                  ├── parse_training_record()  (VLA-41 + Epic 103)
                  ├── resolve_image_path() + is_file()   [optional]
                  ├── duplicate id tracking
                  └── Counter: action + source
              ──> DatasetValidationReport
                      ├── valid (error_count == 0)
                      └── issues[] with code + line + record_id
              ──> validation_report.json  (VLA-47)
```

| Check | Severity | Code |
|-------|----------|------|
| Invalid JSON | error | `invalid_json` |
| Schema / action | error | `schema_invalid` |
| Missing PNG | error | `missing_image` |
| Duplicate `id` | error | `duplicate_id` |
| One action > 50% | warning | `action_imbalance` |
| Missing action token | warning | `missing_action_coverage` |
| Pending review row | error | via `--review-csv` gate |

### Naive approach vs chosen approach

| Approach | Why it seems attractive | Why we did or did not choose it |
|----------|-------------------------|----------------------------------|
| Fail on first error (`read_jsonl`) | Simple | Poor QA feedback for batch imports |
| Collect-all-errors report | More code | Enables CI artifacts and reviewer loops |
| Imbalance as hard error | Strict balance | Blocks MVP starter set; warning only |
| Optional image check | Complexity | Fixtures CI lacks gitignored PNGs |

## Implementation breakdown

### Report types

**Snippet** (`litevla/data/validator.py`):

```python
@dataclass
class DatasetValidationReport:
    jsonl_path: str
    record_count: int = 0
    error_count: int = 0
    warning_count: int = 0
    action_counts: dict[str, int] = field(default_factory=dict)
    ...

    @property
    def valid(self) -> bool:
        return self.error_count == 0
```

**Risks and gotchas:** Warnings increment `warning_count` but do not flip `valid` to False.

---

### Shared image path resolution

```python
def resolve_image_path(image_path: str, *, repo_root: Path) -> Path:
    path = Path(image_path)
    if path.is_absolute():
        return path
    return repo_root / path
```

Same rule as `LiteVLADataset.resolve_image_path()` — validate and train must agree.

### CLI

```bash
python scripts/validate_dataset.py --jsonl data/processed/v0.1.0/train.jsonl
python scripts/validate_dataset.py --jsonl data/fixtures/sample_train.jsonl --skip-image-check
python scripts/validate_dataset.py --version v0.1.0 --write-artifacts
```

Exit code: `0` if `report.valid`, else `1`.

## Engineering decisions

```text
ADR: Collect-all-errors validator (10099)
Status: Accepted
Decision: validate_dataset() never raises on row errors; aggregates into report.
Alternatives Rejected: try/except around read_jsonl only (loses full scan).
```

```text
ADR: Imbalance as warning not error (10101)
Status: Accepted
Decision: action_imbalance warns at 50% threshold; does not set valid=False.
Consequences: Epic 106 can proceed; team reviews warnings in validation_report.json.
```

## Verification patterns and failure modes

```bash
pytest tests/test_dataset_validator.py -q
python scripts/validate_dataset.py --jsonl data/fixtures/sample_train.jsonl --skip-image-check
```

| Symptom | Likely cause | Investigation | Fix |
|---------|--------------|---------------|-----|
| `missing_image` errors | PNG not on disk | Open `image_path` from report | Build/copy images or fix paths |
| `duplicate_id` | Re-import or builder bug | Grep ids in JSONL | Regenerate unique ids |
| `schema_invalid` line N | Bad action or extra key | Read issue message | Fix row or re-import CSV |
| CI passes but train fails images | `--skip-image-check` in CI | Run full validate locally | Add PNGs before training |
| `pending` review blocks release | `--review-csv` gate | Open label_review.csv | Approve or reject rows |

## Engineering principle taught by this task

**Separate transport validation from policy warnings.** Schema and filesystem errors are blockers; distribution skew is signal for humans, not always a build failure.

## Active learning checks

1. When should you use `read_jsonl()` vs `validate_dataset()`?
2. Why does CI use `--skip-image-check` on fixtures?
3. Does `action_imbalance` make `report.valid` false?
4. Which issue codes are errors vs warnings?

## Open questions

- **Val split in CI:** Validate `val.jsonl` separately in release pipeline (supported via `build_version_artifacts`).

## Related

- [dataset-schema.md](dataset-schema.md) (VLA-41 schema under test)
- [labeling-workflow.md](labeling-workflow.md) (VLA-44 — run validator after import)
- [dataset-versioning.md](dataset-versioning.md) (VLA-47 — consumes reports)
- [dataset-loader.md](dataset-loader.md) (VLA-46 — fail-fast load after validate in CI)
