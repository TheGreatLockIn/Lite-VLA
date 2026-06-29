# Lite-VLA data layout (Epic 105 / VLA-6)

## Training format (VLA-41)

**Processed SFT data** uses **JSONL** — one JSON object per line:

```text
data/processed/<version>/train.jsonl
data/processed/<version>/val.jsonl
```

Schema: [`schema/record.schema.json`](schema/record.schema.json)  
Python API: `litevla.data.TrainingRecord`

## Directory roles

| Path | Git | Purpose |
|------|-----|---------|
| `schema/` | tracked | JSON Schema for training records |
| `fixtures/` | tracked | Sample JSONL for tests and docs |
| `reference_images/` | PNGs ignored | Webots reference frames (see README there) |
| `raw/episodes/` | ignored | Raw capture from sim (VLA-42) — see below |
| `processed/` | ignored | Built train/val JSONL + stats (VLA-43, VLA-47) |
| `downloads/` | ignored | External dataset caches |
| `cache/` | ignored | Local tooling cache |

## Raw vs training JSONL

| Layer | Example path | Contents |
|-------|--------------|----------|
| Raw teleop log | `outputs/teleop/<ts>/commands.jsonl` or `raw/episodes/.../commands.jsonl` | High-frequency commands; may include teleop-only labels |
| Training record | `processed/v0.1.0/train.jsonl` | `image_path`, `instruction`, `action` (Epic 103 enum only) |

See task doc: [`docs/epics/dataset-generation-labeling-and-validation/dataset-schema.md`](../docs/epics/dataset-generation-labeling-and-validation/dataset-schema.md).

## Raw episode capture (VLA-42)

Run from an interactive terminal:

```bash
./ros_ws/scripts/run_episode_capture.sh --instruction "Move toward the red cube."
```

Each session writes:

```text
data/raw/episodes/<episode_id>/
├── episode.json       # instruction, world, source, record_frames_hz
├── commands.jsonl     # sim-stamped action + twist rows
└── frames/*.png       # {sim_sec}_{sim_nanosec}.png at ~5 Hz
```

Task doc: [`simulation-data-capture.md`](../docs/epics/dataset-generation-labeling-and-validation/simulation-data-capture.md).

## Processed starter dataset (VLA-43)

Build train/val JSONL locally (requires reference PNGs or raw episodes):

```bash
python scripts/build_starter_dataset.py
```

Output:

```text
data/processed/v0.1.0/
├── train.jsonl
├── val.jsonl
└── images/          # synthetic augmentations
```

Reference labels: [`reference_images/manifest.json`](reference_images/manifest.json)

Task doc: [`synthetic-starter-dataset.md`](../docs/epics/dataset-generation-labeling-and-validation/synthetic-starter-dataset.md).
