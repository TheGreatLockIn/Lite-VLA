# Labeling workflow

**Epic:** Dataset Generation, Labeling, and Validation (105) · **Jira epic:** VLA-6 · **Story:** VLA-44 / 1032 · **Subtasks:** 10096 (guidelines), 10097 (template), 10098 (checklist)

**Human-readable version (browser):** [`labeling-workflow.html`](labeling-workflow.html)

## Executive summary

VLA-44 owns the **human review path** between VLA-43 processed JSONL and training-ready data. Reviewers work in a spreadsheet-friendly CSV (`data/templates/label_review.csv`), not in JSONL directly. Export → edit → import preserves traceability via `id`, `review_status`, and `metadata.review` on merged rows. Approved and corrected rows become `source: manual_review`; rejected rows are dropped from the import output.

## API contract and data flow

```text
processed/v0.1.0/train.jsonl
        │
        ▼
  label_review.py export  ──>  label_review.csv  (spreadsheet / LibreOffice / Google Sheets)
        │
        ▼  human sets review_status, action_reviewed, reviewer, notes
        │
  label_review.py import  ──>  train_reviewed.jsonl  (validated JSONL, manual_review rows)
```

| Contract | Rule |
|----------|------|
| Review format | CSV with fixed columns in `REVIEW_COLUMNS` |
| Training format | JSONL only (`record.schema.json`) — CSV never enters training directly |
| `review_status` | `pending` \| `approved` \| `corrected` \| `rejected` |
| Final action | `corrected` → `action_reviewed`; else `action_reviewed` or `action_proposed` |
| Traceability | `metadata.review` stores status, reviewer, notes, original action/source |
| Rejected rows | Omitted from import output (document reason in `review_notes`) |

**Trade-off:** CSV lacks nested metadata but is familiar to reviewers; import re-validates every row through VLA-41 schema + `parse_action()` before write.

## Labeling guidelines (10096)

Answer: **“What should the robot do next?”** given the image and instruction — not the full plan to the goal.

| Action | When to use |
|--------|-------------|
| `MOVE_FORWARD` | Clear path toward the instruction target; target visible ahead |
| `TURN_LEFT` / `TURN_RIGHT` | Target off-center or not visible; reorient before driving |
| `SLOW_DOWN` | Target nearby or approach phase; still moving but cautiously |
| `STOP` | Goal reached, obstacle blocks path, or safe halt required |

**Do not use in training labels:**

- Teleop-only tokens (`MOVE_BACKWARD`, `MOVE_FORWARD+TURN_LEFT`, …) — stay in raw logs only
- Synonyms (`FORWARD`, `LEFT`, `GO`) — Epic 103 rejects these at import

**Instruction rules:**

- Imperative, present tense: “Move toward the red cube.”
- One goal per row; match the capture scenario in `episode.json` or manifest
- If instruction and image disagree, reject the row or fix instruction before approving

## Review checklist (10098)

Full printable checklist: [`data/templates/label_review_checklist.md`](../../../../data/templates/label_review_checklist.md)

Minimum before import:

1. No rows left `pending` for rows you intend to train on
2. Every `corrected` row has valid `action_reviewed`
3. Rejected rows have a short `review_notes` reason
4. Spot-check 5–10 rows after import (`pytest tests/test_label_review.py`)

## Implementation breakdown

### CSV template (`data/templates/label_review.csv`)

| Column | Purpose |
|--------|---------|
| `id` | Matches JSONL `id` (export generates `anon_NNNNN` if missing) |
| `action_proposed` | Builder/auto label — do not edit unless wrong |
| `action_reviewed` | Required when `review_status=corrected` |
| `review_status` | Workflow gate |
| `reviewer` | Who approved/corrected/rejected |
| `reviewed_at` | ISO 8601 UTC; import fills if empty |

### Python API (`litevla/data/label_review.py`)

```python
export_jsonl_to_review_csv(jsonl_path, csv_path) -> int
import_review_csv_to_jsonl(jsonl_path=..., csv_path=..., output_path=...) -> ImportReviewStats
```

- **Design note:** `read_review_csv` validates headers and actions at parse time — bad spreadsheet edits fail before JSONL write.
- **Gotcha:** Import matches on `id` only; do not rename ids between export and import.

### CLI (`scripts/label_review.py`)

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

**ADR: CSV for review, JSONL for training (10097)**  
Status: Accepted  
Context: Reviewers need spreadsheet UX; training pipeline needs streaming JSONL + nested metadata.  
Decision: Round-trip CSV via export/import scripts; merged rows use `source: manual_review`.  
Alternatives rejected: Edit JSONL by hand (error-prone); custom GUI (scope for MVP).

**ADR: Reject drops row on import (10098)**  
Status: Accepted  
Decision: `review_status=rejected` excludes the row from output JSONL rather than keeping a poison example.  
Consequences: Keep rejection reasons in CSV for audit; VLA-45 can report rejection counts later.

## Verification patterns

```bash
pytest tests/test_label_review.py -q
python scripts/label_review.py export --jsonl data/fixtures/sample_train.jsonl --output /tmp/review.csv
python scripts/label_review.py import --jsonl data/fixtures/sample_train.jsonl --csv /tmp/review.csv --output /tmp/out.jsonl
```

Defends: CSV column contract, action validation, approved/corrected/rejected merge semantics.

## Related

- [dataset-schema.md](dataset-schema.md) (VLA-41 output contract)
- [synthetic-starter-dataset.md](synthetic-starter-dataset.md) (VLA-43 builder input to review)
- [action-schema.md](../action-interface-parser-and-safety-layer/action-schema.md) (Epic 103 action meanings)
- [`data/templates/README.md`](../../../../data/templates/README.md)

## Open questions

- **Val split review:** Export/import val.jsonl separately or review train only for MVP (current default: train).
- **Post-import validation:** Run `validate_dataset` on `train_reviewed.jsonl` after import (VLA-45).
