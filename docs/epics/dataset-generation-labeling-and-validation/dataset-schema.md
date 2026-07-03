# Dataset schema and file layout

**Epic:** Dataset Generation, Labeling, and Validation (105) · **Jira epic:** VLA-6 · **Story:** VLA-41 / 1029 · **Subtasks:** VLA-169 (format), VLA-170 (fields), VLA-171 (fixtures)

**Human-readable version (browser):** [`dataset-schema.html`](dataset-schema.html)

## Executive summary

VLA-41 owns the **processed training record contract** for supervised fine-tuning: one UTF-8 JSONL row per image-instruction-action example under `data/processed/<version>/`. Raw simulation logs (VLA-42) use a different on-disk shape; only rows validated against `record.schema.json` and Epic 103 `parse_action()` enter training. This story is the schema gate every downstream builder, reviewer, validator, and loader depends on.

## Mental model

Think of this module as a **passport office for training rows**.

It exists because ML pipelines fail silently when bad examples slip in — a typo in `action`, a Windows path, or a synonym like `FORWARD` poisons gradients long before anyone notices.

The key engineering tension is **strictness vs flexibility**: the top-level record is rigid (`additionalProperties: false`), but `metadata` stays open so capture and review can attach context without schema churn.

A beginner mistake is treating raw `commands.jsonl` as training data, or editing JSONL by hand instead of going through validated write paths.

A senior engineer watches for **vocabulary drift** — any new action token must land in Epic 103, `record.schema.json`, and dataset tests in the same change.

## Backstory: why this exists

Before VLA-41, the repo had teleop logs and reference images but no single contract for “one SFT example.” The naive solution would be a folder of PNGs plus a spreadsheet of labels.

That breaks because spreadsheets hide nested provenance, stream poorly into PyTorch, and cannot share validation logic with ROS capture. Training would also diverge from the five-token action vocabulary the parser and safety gate already enforce.

So this design chooses **JSONL + JSON Schema + a frozen `TrainingRecord` dataclass**, with `parse_training_record()` as the only front door. The pattern appears in real robotics ML stacks as “processed manifest” layers sitting between messy logs and the trainer.

## Prerequisites

- Epic 103 discrete actions: [`action-schema.md`](../action-interface-parser-and-safety-layer/action-schema.md)
- JSONL basics: one JSON object per line, UTF-8, append-friendly

## Vocabulary

| Term | Meaning in this project |
|------|-------------------------|
| **Training record** | One row: image + instruction + discrete action + provenance |
| **JSONL** | Newline-delimited JSON; streaming read/write for large corpora |
| **JSON Schema** | Machine-checkable field contract in `data/schema/record.schema.json` |
| **Processed layer** | `data/processed/<version>/` — training-ready rows only |
| **Raw layer** | `data/raw/episodes/` — high-frequency capture logs (VLA-42) |
| **`source`** | How the row was produced: `teleop`, `reference`, `synthetic`, `manual_review` |
| **`parse_action()`** | Epic 103 strict token validator used after JSON Schema passes |

## Guided code reading

Read these in order:

1. `data/schema/record.schema.json`
   - Inspect `required`, `action.enum`, and `additionalProperties: false`.
   - Ignore optional fields on first pass.

2. `litevla/data/schema.py`
   - Start at `TrainingRecord` and `parse_training_record()`.
   - Then `read_jsonl()` / `write_jsonl()` for I/O boundaries.

3. `data/fixtures/sample_train.jsonl`
   - Six committed rows covering all five actions and three sources.

4. `configs/default.example.yaml` (`data:` section)
   - See how training scripts discover schema and processed paths.

While reading, ask: Where does validation happen? Who raises on bad rows? What is allowed in `metadata`?

## API contract and data flow

```text
Raw capture (VLA-42)                    Processed SFT (VLA-41)
─────────────────────                   ────────────────────────
raw/episodes/<id>/commands.jsonl   ──>  processed/v0.1.0/train.jsonl
raw/episodes/<id>/frames/*.png     ──>       (image_path + instruction + action)
reference_images/manifest.json     ──>  (via VLA-43 builder)
```

| Contract surface | Rule |
|------------------|------|
| **Format** | JSONL — one JSON object per line, UTF-8 |
| **`action`** | Exactly one of `MOVE_FORWARD`, `TURN_LEFT`, `TURN_RIGHT`, `SLOW_DOWN`, `STOP` |
| **`source`** | `teleop`, `reference`, `synthetic`, or `manual_review` |
| **`image_path`** | Repo-relative POSIX path; no backslashes |
| **Validation** | JSON Schema + `parse_action()` before any row is written to processed files |
| **Error behavior** | `RecordSchemaError` with file:line context on read; builder/import fail fast |

### Naive approach vs chosen approach

| Approach | Why it seems attractive | Why we did or did not choose it |
|----------|-------------------------|----------------------------------|
| CSV for training storage | Easy for humans to edit | Poor nested metadata; not the canonical training format |
| Single giant JSON array | Simple to parse | Not stream-friendly; reloads entire file |
| Parquet | Efficient columnar storage | Heavier dependency for MVP edge targets |
| JSONL + Schema + dataclass | Slightly more setup | Streaming, shared validation, matches ROS log patterns |

## Implementation breakdown

### JSON Schema — machine-readable contract

**Snippet** (`data/schema/record.schema.json`):

```json
"action": {
  "type": "string",
  "enum": ["MOVE_FORWARD", "TURN_LEFT", "TURN_RIGHT", "SLOW_DOWN", "STOP"]
},
"additionalProperties": false
```

**What to notice:** Action enum duplicates Epic 103 on purpose — schema failures catch bad labels before Python imports.

**Why it is written this way:** `additionalProperties: false` at the top level turns typos into CI failures instead of silent extra fields in training.

**Risks and gotchas:** Raw episode `source` values (`dummy`, `scripted`) differ from training `source`; VLA-43 maps them during build.

---

### Python API — parse, validate, stream

**Snippet** (`litevla/data/schema.py`):

```python
@dataclass(frozen=True)
class TrainingRecord:
    image_path: str
    instruction: str
    action: str
    timestamp: str
    source: str
    id: str | None = None
    episode_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

def parse_training_record(raw: dict[str, Any], *, schema: dict[str, Any] | None = None) -> TrainingRecord:
    validate_record_dict(raw, schema=schema)
    action = parse_action(str(raw["action"]))
    ...
```

**What to notice:** Schema validation runs before action parsing; both must pass.

**Why it is written this way:** Single parse path for builder, label import, validator, and loader — one source of truth.

**Risks and gotchas:** `read_jsonl()` fails on the **first** bad row (fail-fast). Use VLA-45 `validate_dataset()` when you need a full error report.

---

### Fixtures and config wiring

**Fixtures:** `data/fixtures/sample_train.jsonl` — six rows for CI without requiring PNG files on disk.

**Config** (`configs/default.example.yaml`):

```yaml
data:
  schema_path: data/schema/record.schema.json
  processed_version: v0.1.0
  train_path: data/processed/v0.1.0/train.jsonl
```

## Engineering decisions

```text
ADR: JSONL for training (VLA-169)
Status: Accepted
Context: Need nested metadata and streaming for large datasets.
Decision: JSONL only for processed training; CSV only for label review spreadsheets (VLA-44).
Alternatives Rejected: Parquet (heavier dependency), single JSON array (not stream-friendly).
Consequences: All writers must use write_jsonl() or re-validate on import.
```

```text
ADR: Epic 103 action enum in schema (VLA-170)
Status: Accepted
Context: Model output, dummy controller, and dataset must share one vocabulary.
Decision: Hard-code the five DiscreteAction tokens in JSON Schema enum.
Consequences: Teleop-only labels like MOVE_BACKWARD stay in raw logs, not training rows.
```

## Verification patterns and failure modes

**Commands:**

```bash
pytest tests/test_dataset_schema.py -q
python -c "
from litevla.data.schema import read_jsonl, FIXTURES_PATH
print(sum(1 for _ in read_jsonl(FIXTURES_PATH)))
"
```

| Contract defended | Test / command |
|-------------------|----------------|
| Required fields present | `test_dataset_schema.py` |
| Invalid action rejected | `parse_training_record` + `parse_action` |
| Extra top-level keys rejected | `additionalProperties: false` |
| JSONL round-trip | `write_jsonl` / `read_jsonl` |

| Symptom | Likely cause | How to investigate | Fix |
|---------|--------------|--------------------|-----|
| `RecordSchemaError` on line N | Bad action, missing field, or typo key | Read message path (`action`, `source`, …) | Fix row or re-export from label CSV |
| `FORWARD` rejected | Alias not in Epic 103 | Check `action` column | Use exact token from action schema doc |
| Training can't find images | `image_path` wrong or PNG missing | Compare path to repo root | Run VLA-45 with image check |
| Raw log won't load as training | Wrong layer | Check file is under `processed/` | Run VLA-43 builder |

## Engineering principle taught by this task

**Validate at the boundary, not inside the trainer.** Schema and action checks belong where data enters the processed layer; the training loop should assume rows are already trustworthy.

## Active learning checks

Before changing this module, answer:

1. Why is raw `commands.jsonl` a different contract than `train.jsonl`?
2. What happens if you add a field without updating `record.schema.json`?
3. Why does `parse_training_record` call both JSON Schema and `parse_action()`?
4. When should you use `read_jsonl()` vs `validate_dataset()`?

**Small modification exercise:** Add an optional `metadata.review` object via the label import path (VLA-44), run `pytest tests/test_dataset_schema.py`, and confirm top-level shape is unchanged.

## Open questions

- **Lazy JSONL for large corpora:** `read_jsonl` streams, but `LiteVLADataset` eagerly lists all rows — streaming index may be needed beyond ~10k examples (VLA-46 follow-up).

## Related

- [action-schema.md](../action-interface-parser-and-safety-layer/action-schema.md) (Epic 103 labels)
- [simulation-data-capture.md](simulation-data-capture.md) (VLA-42 raw layer)
- [synthetic-starter-dataset.md](synthetic-starter-dataset.md) (VLA-43 builder output)
- [labeling-workflow.md](labeling-workflow.md) (VLA-44 human review)
- [dataset-validation.md](dataset-validation.md) (VLA-45 schema gate)
- [dataset-loader.md](dataset-loader.md) (VLA-46 training consumer)
- [dataset-versioning.md](dataset-versioning.md) (VLA-47 release packaging)
- [`data/README.md`](../../../../data/README.md) (folder layout)
