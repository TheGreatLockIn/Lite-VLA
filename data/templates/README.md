# Label review templates (VLA-44)

Human reviewers edit **`label_review.csv`** in a spreadsheet app, then import corrections back into processed JSONL.

| File | Purpose |
|------|---------|
| [`label_review.csv`](label_review.csv) | Column template + two example rows (status `pending`) |
| [`label_review_checklist.md`](label_review_checklist.md) | Pre-training review checklist (10098) |

## Workflow

```bash
# 1. Export processed train split for review
python scripts/label_review.py export \
  --jsonl data/processed/v0.1.0/train.jsonl \
  --output data/processed/v0.1.0/label_review.csv

# 2. Edit CSV: set review_status, action_reviewed (if correcting), reviewer, notes

# 3. Merge approved/corrected rows back (rejected rows are dropped)
python scripts/label_review.py import \
  --jsonl data/processed/v0.1.0/train.jsonl \
  --csv data/processed/v0.1.0/label_review.csv \
  --output data/processed/v0.1.0/train_reviewed.jsonl
```

Guidelines: [`docs/epics/dataset-generation-labeling-and-validation/labeling-workflow.md`](../../docs/epics/dataset-generation-labeling-and-validation/labeling-workflow.md)
