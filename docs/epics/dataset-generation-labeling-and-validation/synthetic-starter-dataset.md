# Synthetic starter dataset

**Epic:** Dataset Generation, Labeling, and Validation (105) · **Jira epic:** VLA-6 · **Story:** VLA-43 / 1031 · **Subtasks:** 10093 (frames), 10094 (labels), 10095 (train/val split)

**Human-readable version (browser):** [`synthetic-starter-dataset.html`](synthetic-starter-dataset.html)

## Executive summary

VLA-43 implements the **Layer A → Layer B compiler**: it ingests reference Webots frames, optional VLA-42 raw episodes, and Pillow augmentations to produce ≥200 validated `TrainingRecord` rows under `data/processed/<version>/train.jsonl` and `val.jsonl`. Every row passes VLA-41 schema validation before write. The CLI is `scripts/build_starter_dataset.py`.

## API contract and data flow

```text
reference_images/manifest.json ──> records_from_reference_manifest (source=reference)
data/raw/episodes/*/             ──> records_from_raw_episode (forward-fill labels)
        │                                    │
        └──────────────┬─────────────────────┘
                       ▼
         augment_reference_records()  (if count < min_records)
                       │
                       ▼
              validate_record_dict × N
                       │
                       ▼
              split_records(seed, val_ratio)
                       │
                       ▼
         processed/v0.1.0/train.jsonl + val.jsonl
```

| Contract | Rule |
|----------|------|
| Minimum size | Default `--min-records 200` (Jira 1031) |
| Label join | Latest command at or before frame sim time (forward-fill) |
| Split | Deterministic shuffle by seed; unique `id` required; disjoint train/val |
| Output paths | Gitignored under `data/processed/`; rebuild locally |
| Augmentation | Only from reference base images — not raw teleop frames |

## Implementation breakdown

### Reference ingest (`records_from_reference_manifest`)

Reads committed `data/reference_images/manifest.json`; skips missing PNGs (gitignored images) and counts them in `BuildStats.skipped_missing_image`.

### Raw episode join (`records_from_raw_episode`)

```python
def _action_at_sim_time(commands, sim_ns):
    # Return latest command row where sim_stamp <= frame sim_ns
```

- **Design note:** Frames at 11.5s inherit `MOVE_FORWARD` if that was the last command at 10s — matches “what was the robot trying to do when this frame was taken?”
- **Gotcha:** Exact timestamp matches are rare; forward-fill is intentional, not nearest-neighbor.

### Augmentation (`augment_reference_records`)

Deterministic Pillow transforms (brightness, contrast, crop, occasional blur) keyed by variant index + seed. Writes PNGs to `processed/<version>/images/` with `source: synthetic`.

- **ADR (10093):** Augment curated reference frames, not teleop trajectories, to hit 200 rows before large-scale collection.

### Orchestrator (`build_starter_dataset`)

Auto-computes `variants_per_image` when reference + raw count is below `min_records`:

```python
auto_variants = (needed + base_count - 1) // base_count
```

### CLI (`scripts/build_starter_dataset.py`)

```bash
python scripts/build_starter_dataset.py \
  --version v0.1.0 \
  --min-records 200 \
  --val-ratio 0.1 \
  --seed 42
```

## Engineering decisions

**ADR: Forward-fill labels (10094)**  
Status: Accepted  
Context: Commands log on action transitions; frames arrive at ~5 Hz.  
Decision: Each frame gets the most recent command at or before its sim stamp.  
Alternatives rejected: Nearest-neighbor (can label a frame with a future action).

**ADR: Seed split (10095)**  
Status: Accepted  
Decision: `random.Random(seed).shuffle` then slice; reject duplicate ids before split.  
Consequences: Reproducible train/val across machines with same inputs.

## Verification patterns

```bash
pytest tests/test_dataset_builder.py -q
python scripts/build_starter_dataset.py   # requires reference PNGs locally
```

Defends: forward-fill logic, min record count, unique ids across split, schema validation on build.

## Related

- [dataset-schema.md](dataset-schema.md) (VLA-41 output contract)
- [simulation-data-capture.md](simulation-data-capture.md) (VLA-42 input)
- [dataset-validation.md](dataset-validation.md) (VLA-45 — validate builder output)
- [dataset-versioning.md](dataset-versioning.md) (VLA-47 — `--write-artifacts` after build)
- [`data/reference_images/manifest.json`](../../../../data/reference_images/manifest.json)

## Open questions

- **Real vs synthetic ratio:** Starter set is augmentation-heavy by design; rebalance when teleop volume grows.
