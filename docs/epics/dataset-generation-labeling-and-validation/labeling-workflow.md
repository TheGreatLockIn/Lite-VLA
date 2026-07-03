# Labeling workflow

**Epic:** Dataset Generation, Labeling, and Validation (105) · **Jira epic:** VLA-6 · **Story:** VLA-44 / 1032 · **Subtasks:** 10096 (guidelines), 10097 (template), 10098 (checklist)

**Human-readable version (browser):** [`labeling-workflow.html`](labeling-workflow.html)

## Executive summary

VLA-44 owns the **human review path** between VLA-43 processed JSONL and training-ready data. Reviewers work in a spreadsheet-friendly CSV (`data/templates/label_review.csv`), not in JSONL directly. Export → edit → import preserves traceability via `id`, `review_status`, and `metadata.review` on merged rows. Approved and corrected rows become `source: manual_review`; rejected rows are dropped from the import output.

## Mental model

Think of labeling as a **code review for robot demonstrations**.

It exists because automated builders and teleop logs produce *proposed* actions that can be wrong — humans must confirm “what should the robot do next?” before fine-tuning memorizes mistakes.

The key engineering tension is **reviewer ergonomics vs machine contracts**: spreadsheets are easy for people; JSONL + schema are easy for pipelines.

A beginner mistake is editing `train.jsonl` by hand, using synonym actions (`FORWARD`), or leaving rows `pending` then importing for training.

A senior engineer watches for **id stability** — export/import matches on `id` only; renamed rows silently become orphans.

## Backstory: why this exists

Spreadsheet-first labeling is tempting for a small team. The naive path is “everyone edits the training file.”

That breaks because one stray comma corrupts JSONL, nested review metadata does not fit columns cleanly, and invalid actions slip in without `parse_action()`.

So this design chooses **CSV round-trip through validated import**, with guidelines locking labels to Epic 103 tokens only.

## Prerequisites

- Epic 103 action meanings: [action-schema.md](../action-interface-parser-and-safety-layer/action-schema.md)
- VLA-41 record shape: [dataset-schema.md](dataset-schema.md)

## Vocabulary

| Term | Meaning in this project |
|------|-------------------------|
| **`action_proposed`** | Builder or teleop label — do not edit unless wrong |
| **`action_reviewed`** | Human correction; required when `review_status=corrected` |
| **`review_status`** | `pending`, `approved`, `corrected`, or `rejected` |
| **`manual_review`** | Training `source` after successful human merge |
| **`metadata.review`** | Nested audit trail on imported JSONL rows |

## Guided code reading

1. `data/templates/label_review.csv` — column headers (`REVIEW_COLUMNS`).
2. `data/templates/label_review_checklist.md` — printable QA steps.
3. `litevla/data/label_review.py` — `export_jsonl_to_review_csv`, `import_review_csv_to_jsonl`.
4. `scripts/label_review.py` — CLI (`export`, `import`, `bulk-approve`).
5. `tests/test_label_review.py` — merge semantics.

## API contract and data flow

```text
processed/v0.1.0/train.jsonl
        │
        ▼
  label_review.py export  ──>  label_review.csv  (spreadsheet)
        │
        ▼  human sets review_status, action_reviewed, reviewer, notes
        │
  label_review.py import  ──>  train_reviewed.jsonl  (validated JSONL)
```

| Contract | Rule |
|----------|------|
| Review format | CSV with fixed columns in `REVIEW_COLUMNS` |
| Training format | JSONL only — CSV never enters training directly |
| `review_status` | `pending` \| `approved` \| `corrected` \| `rejected` |
| Final action | `corrected` → `action_reviewed`; else `action_reviewed` or `action_proposed` |
| Rejected rows | Omitted from import output |

### Labeling guidelines (10096)

Answer: **“What should the robot do next?”** given the image and instruction — not the full plan to the goal.

| Action | When to use |
|--------|-------------|
| `MOVE_FORWARD` | Clear path toward the instruction target; target visible ahead |
| `TURN_LEFT` / `TURN_RIGHT` | Target off-center or not visible; reorient before driving |
| `SLOW_DOWN` | Target nearby or approach phase; still moving but cautiously |
| `STOP` | Goal reached, obstacle blocks path, or safe halt required |

**Do not use in training labels:** teleop-only tokens, synonyms (`FORWARD`, `LEFT`, `GO`).

### Naive approach vs chosen approach

| Approach | Why it seems attractive | Why we did or did not choose it |
|----------|-------------------------|----------------------------------|
| Edit JSONL in VS Code | Direct | Easy to break schema; no spreadsheet UX |
| Custom labeling GUI | Nice UX | Out of MVP scope |
| CSV export/import round-trip | Extra scripts | Familiar tools + schema validation on import |
| Keep rejected rows in training | Preserve counts | Poison examples; reject drops row |

## Implementation breakdown

### CSV template and columns

| Column | Purpose |
|--------|---------|
| `id` | Matches JSONL `id` (export generates `anon_NNNNN` if missing) |
| `action_proposed` | Auto label — do not edit unless wrong |
| `action_reviewed` | Required when `review_status=corrected` |
| `review_status` | Workflow gate |
| `reviewer` | Who approved/corrected/rejected |

### Python API

**Snippet** (`litevla/data/label_review.py`):

```python
export_jsonl_to_review_csv(jsonl_path, csv_path) -> int
import_review_csv_to_jsonl(jsonl_path=..., csv_path=..., output_path=...) -> ImportReviewStats
```

**Risks and gotchas:** `read_review_csv` validates headers and actions at parse time. Import matches on `id` only.

### CLI

```bash
python scripts/label_review.py export \
  --jsonl data/processed/v0.1.0/train.jsonl \
  --output data/processed/v0.1.0/label_review.csv

python scripts/label_review.py import \
  --jsonl data/processed/v0.1.0/train.jsonl \
  --csv data/processed/v0.1.0/label_review.csv \
  --output data/processed/v0.1.0/train_reviewed.jsonl
```

## Engineering decisions

```text
ADR: CSV for review, JSONL for training (10097)
Status: Accepted
Decision: Round-trip CSV via export/import; merged rows use source: manual_review.
Alternatives Rejected: Hand-edited JSONL; custom GUI for MVP.
```

```text
ADR: Reject drops row on import (10098)
Status: Accepted
Decision: review_status=rejected excludes row from output JSONL.
Consequences: Keep rejection reasons in review_notes for audit.
```

## Verification patterns and failure modes

```bash
pytest tests/test_label_review.py -q
python scripts/label_review.py export --jsonl data/fixtures/sample_train.jsonl --output /tmp/review.csv
python scripts/label_review.py import --jsonl data/fixtures/sample_train.jsonl --csv /tmp/review.csv --output /tmp/out.jsonl
```

| Symptom | Likely cause | Investigation | Fix |
|---------|--------------|---------------|-----|
| Import fails on action | Synonym in `action_reviewed` | Read `LabelReviewError` | Use Epic 103 token |
| Rows missing after import | `rejected` or `pending` | Check `review_status` column | Approve or correct rows |
| Duplicate merge confusion | Changed `id` in CSV | Diff ids export vs import | Never rename ids between steps |
| Release blocked on pending | VLA-45 `--review-csv` gate | Run validator with review CSV | Clear pending or exclude rows |

## Engineering principle taught by this task

**Human interfaces and machine contracts should differ deliberately.** Optimize the review surface for people (CSV), then re-validate aggressively when re-entering the typed pipeline (JSONL).

## Active learning checks

1. Why is CSV never the canonical training format?
2. What happens to a `rejected` row during import?
3. When must `action_reviewed` be filled?
4. How does `metadata.review` help post-hoc auditing?

## Open questions

- **Val split review:** Export/import `val.jsonl` separately or review train only for MVP (current default: train).
- **Pending-row gate:** Use `validate_dataset(..., review_csv_path=...)` or CLI `--review-csv` before release.

## Related

- [dataset-schema.md](dataset-schema.md) (VLA-41 output contract)
- [synthetic-starter-dataset.md](synthetic-starter-dataset.md) (VLA-43 builder input)
- [dataset-validation.md](dataset-validation.md) (VLA-45 — run after import)
- [dataset-versioning.md](dataset-versioning.md) (VLA-47 — release reviewed JSONL)
- [`data/templates/README.md`](../../../../data/templates/README.md)
