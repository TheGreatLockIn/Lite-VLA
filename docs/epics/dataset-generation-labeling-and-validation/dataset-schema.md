# Dataset schema and file layout

**Epic:** Dataset Generation, Labeling, and Validation (105) · **Jira epic:** VLA-6 · **Story:** VLA-41 / 1029 · **Subtasks:** VLA-169 (format), VLA-170 (fields), VLA-171 (fixtures)

**Human-readable version (browser):** [`dataset-schema.html`](dataset-schema.html)

## Executive summary

VLA-41 owns the **processed training record contract** for supervised fine-tuning: one UTF-8 JSONL row per image-instruction-action example under `data/processed/<version>/`. Raw simulation logs (VLA-42) use a different on-disk shape; only rows validated against `record.schema.json` enter training. Action tokens are locked to Epic 103 `DiscreteAction` so labels, dummy controller, parser, and prompts stay aligned.

## API contract and data flow

```text
Raw capture (VLA-42)                    Processed SFT (VLA-41)
─────────────────────                   ────────────────────────
raw/episodes/<id>/commands.jsonl   ──>  processed/v0.1.0/train.jsonl
raw/episodes/<id>/frames/*.png     ──>       (image_path + instruction + action)
reference_images/manifest.json     ──>  (via VLA-43 builder)
```

| Contract | Rule |
|----------|------|
| Format | JSONL — one JSON object per line, UTF-8 |
| `action` | Exactly one of `MOVE_FORWARD`, `TURN_LEFT`, `TURN_RIGHT`, `SLOW_DOWN`, `STOP` |
| `source` | `teleop`, `reference`, `synthetic`, or `manual_review` |
| `image_path` | Repo-relative POSIX path; no backslashes |
| Validation | JSON Schema + `parse_action()` before any row is written to processed files |

**Trade-off:** CSV is reserved for human label review (VLA-44), not canonical training storage — nested `metadata` in JSONL matches the ROS `command_recorder` pattern.

## Implementation breakdown

### JSON Schema (`data/schema/record.schema.json`)

Machine-readable contract with `additionalProperties: false` on the top-level record so typos fail CI instead of silently entering training data.

- **Design note:** `metadata` is an open object for sim stamps, velocities, and review flags without schema churn per capture field.
- **Gotcha:** Raw episode `source` enums (`dummy`, `scripted`) differ from training `source` — the builder maps them (VLA-43).

### Python API (`litevla/data/schema.py`)

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
```

- **`parse_training_record`** — Draft 202012 JSON Schema validation, then `parse_action()` from `litevla.actions`.
- **`read_jsonl` / `write_jsonl`** — streaming I/O for builder (VLA-43) and validator (VLA-45); compact JSON (no extra whitespace) on write.
- **Design note:** `RecordSchemaError` wraps schema and action errors with line numbers for JSONL files.

### Fixtures (`data/fixtures/sample_train.jsonl`)

Six committed rows covering all five actions and three `source` values. CI validates schema **without** requiring PNG files on disk.

### Config wiring (`configs/default.example.yaml`)

```yaml
data:
  schema_path: data/schema/record.schema.json
  processed_version: v0.1.0
  train_path: data/processed/v0.1.0/train.jsonl
  val_path: data/processed/v0.1.0/val.jsonl
  raw_episodes_dir: data/raw/episodes
training:
  dataset_path: data/processed/v0.1.0/train.jsonl
```

## Engineering decisions

**ADR: JSONL for training (VLA-169)**  
Status: Accepted  
Context: Need nested metadata and streaming for large datasets.  
Decision: JSONL only for processed training; CSV only for label review spreadsheets.  
Alternatives rejected: Parquet (heavier dependency for MVP), single JSON array (not stream-friendly).

**ADR: Epic 103 action enum in schema (VLA-170)**  
Status: Accepted  
Context: Model output, dummy controller, and dataset must share one vocabulary.  
Decision: Hard-code the five `DiscreteAction` tokens in JSON Schema `enum`.  
Consequences: Teleop-only labels like `MOVE_BACKWARD` stay in raw logs, not training rows.

## Verification patterns

```bash
pytest tests/test_dataset_schema.py -q
python -c "
from litevla.data.schema import read_jsonl, FIXTURES_PATH
print(sum(1 for _ in read_jsonl(FIXTURES_PATH)))
"
```

Defends: required fields, invalid action rejection, extra-key rejection, JSONL round-trip.

## Related

- [action-schema.md](../action-interface-parser-and-safety-layer/action-schema.md) (Epic 103 labels)
- [simulation-data-capture.md](simulation-data-capture.md) (VLA-42 raw layer)
- [synthetic-starter-dataset.md](synthetic-starter-dataset.md) (VLA-43 builder output)
- [`data/README.md`](../../../../data/README.md) (folder layout)

## Open questions

- **Image path convention:** Processed augmentations live under `data/processed/<version>/images/`; confirm loader resolves repo-relative paths the same way (VLA-46).
