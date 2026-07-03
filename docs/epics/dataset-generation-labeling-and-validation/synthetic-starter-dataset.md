# Synthetic starter dataset

**Epic:** Dataset Generation, Labeling, and Validation (105) · **Jira epic:** VLA-6 · **Story:** VLA-43 / 1031 · **Subtasks:** 10093 (frames), 10094 (labels), 10095 (train/val split)

**Human-readable version (browser):** [`synthetic-starter-dataset.html`](synthetic-starter-dataset.html)

## Executive summary

VLA-43 implements the **Layer A → Layer B compiler**: it ingests reference Webots frames, optional VLA-42 raw episodes, and Pillow augmentations to produce ≥200 validated `TrainingRecord` rows under `data/processed/<version>/train.jsonl` and `val.jsonl`. Every row passes VLA-41 schema validation before write. The CLI is `scripts/build_starter_dataset.py`.

## Mental model

Think of the builder as a **compiler from messy logs to training rows**.

It exists because raw capture and reference poses are not yet image-instruction-action tuples — someone must align timestamps, copy paths into repo-relative form, and reject bad rows before Epic 106 touches them.

The key engineering tension is **quantity vs diversity**: the MVP needs ≥200 rows to unblock training, but augmentation must not pretend one PNG is an entire dataset.

A beginner mistake is expecting augmentation alone to hit 200 rows from a single missing reference checkout, or using nearest-neighbor label matching across time.

A senior engineer watches for **forward-fill semantics** — labels inherit the last command at or before frame sim time, never a future command.

## Backstory: why this exists

Epic 106 fine-tuning cannot wait for hundreds of teleop hours. The naive solution is hand-labeling 200 PNGs in a spreadsheet.

That breaks at scale (no sim-stamp join for teleop), invites label drift, and duplicates validation logic outside the schema gate.

So this design chooses an automated builder with three ingest paths (reference manifest, raw episodes, capped augmentation), deterministic train/val split, and `validate_record_dict` on every emitted row.

## Prerequisites

- VLA-41 training record contract: [dataset-schema.md](dataset-schema.md)
- VLA-42 raw layout (optional input): [simulation-data-capture.md](simulation-data-capture.md)

## Vocabulary

| Term | Meaning in this project |
|------|-------------------------|
| **Reference manifest** | `data/reference_images/manifest.json` — curated poses with instructions |
| **Forward-fill** | Frame at time T gets latest command with sim_stamp ≤ T |
| **Augmentation variant** | Pillow-transformed copy of a reference image; same action label |
| **`BuildStats`** | Counts reference, synthetic, raw, and skipped-missing-image rows |
| **`min_records`** | Default 200 — Jira success threshold for starter set |

## Guided code reading

1. `data/reference_images/manifest.json` — four pose entries and instructions.
2. `litevla/data/builder.py` — `records_from_reference_manifest`, `records_from_raw_episode`, `augment_reference_records`, `build_starter_dataset`.
3. `scripts/build_starter_dataset.py` — CLI flags (`--min-records`, `--seed`, `--max-variants-per-image`).
4. `tests/test_dataset_builder.py` — forward-fill and split contracts.

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

### Naive approach vs chosen approach

| Approach | Why it seems attractive | Why we did or did not choose it |
|----------|-------------------------|----------------------------------|
| Nearest-neighbor label join | Simple timestamp math | Can assign a **future** action to a past frame |
| Augment teleop trajectories | More “real” diversity | Risk of unrealistic pose/action pairs for MVP |
| Uncapped duplication from one PNG | Fast 200 rows | Collapses diversity; capped at 25 variants/image |
| Forward-fill + reference augment | More code | Matches how operators hold an action between key changes |

## Implementation breakdown

### Raw episode join — forward-fill by sim time

**Snippet** (`litevla/data/builder.py`):

```python
def _action_at_sim_time(commands, sim_ns):
    # Return latest command row where sim_stamp <= frame sim_ns
    ...
```

**What to notice:** Commands arrive on transitions; frames at ~5 Hz inherit the active command.

**Why it is written this way:** Answers “what was the robot trying to do when this frame was taken?”

**Risks and gotchas:** Exact timestamp matches are rare; do not expect 1:1 frame:command rows.

---

### Augmentation — capped, label-preserving variants

Photometric jitter, crop/resize, blur, noise, occasional JPEG compression. RNG seeded per `(seed, image_stem, variant)`.

Default `--max-variants-per-image 25` prevents one reference PNG from dominating 200 rows.

**Risks and gotchas:** Builder fails below `--min-records` if reference PNGs are missing locally (gitignored) — check `BuildStats.skipped_missing_image`.

---

### Orchestrator and CLI

```bash
python scripts/build_starter_dataset.py \
  --version v0.1.0 \
  --min-records 200 \
  --val-ratio 0.1 \
  --seed 42 \
  --max-variants-per-image 25
```

## Engineering decisions

```text
ADR: Forward-fill labels (10094)
Status: Accepted
Context: Commands log on action transitions; frames arrive at ~5 Hz.
Decision: Each frame gets the most recent command at or before its sim stamp.
Alternatives Rejected: Nearest-neighbor (can label with a future action).
```

```text
ADR: Seed split (10095)
Status: Accepted
Decision: random.Random(seed).shuffle then slice; reject duplicate ids before split.
Consequences: Reproducible train/val across machines with same inputs.
```

## Verification patterns and failure modes

```bash
pytest tests/test_dataset_builder.py -q
python scripts/build_starter_dataset.py   # requires reference PNGs locally
```

| Symptom | Likely cause | Investigation | Fix |
|---------|--------------|---------------|-----|
| Build fails below 200 rows | Missing reference PNGs | CLI lists skipped images | Copy/generate four reference frames |
| Duplicate `id` error | Re-run without new ids | Grep train.jsonl | Clear processed dir or fix id generator |
| All rows `synthetic` | No raw episodes | Check `data/raw/episodes/` | Capture teleop or rely on reference+aug |
| Val overlap with train | Split bug or duplicate ids | Run validator duplicate check | Rebuild with clean ids |

## Engineering principle taught by this task

**Treat dataset construction as a typed compiler.** Ingest heterogeneous sources, apply explicit join semantics, validate each output row, and fail the build loudly when inputs cannot satisfy the contract.

## Active learning checks

1. Why forward-fill instead of nearest-neighbor timestamp matching?
2. Why cap augmentation per reference image?
3. What happens to a frame captured 0.3s after the last command transition?
4. Which `source` values appear in output for teleop vs reference vs augmented rows?

## Open questions

- **Real vs synthetic ratio:** Starter set is augmentation-heavy by design; rebalance when teleop volume grows.

## Related

- [dataset-schema.md](dataset-schema.md) (VLA-41 output contract)
- [simulation-data-capture.md](simulation-data-capture.md) (VLA-42 input)
- [dataset-validation.md](dataset-validation.md) (VLA-45 — validate builder output)
- [dataset-versioning.md](dataset-versioning.md) (VLA-47 — `--write-artifacts` after build)
- [`data/reference_images/manifest.json`](../../../../data/reference_images/manifest.json)
