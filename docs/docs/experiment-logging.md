# Experiment logging convention

**Human-readable version (browser):** [`experiment-logging.html`](html/experiment-logging.html)

This document defines how Lite-VLA saves training, inference, benchmark, and deployment experiment outputs so runs stay traceable and comparable.

## Goals

- Every experiment run records the **exact config** that produced it.
- Run directories are **timestamped** and grouped by experiment kind.
- **Metrics** are written in a consistent JSON file for later comparison.
- Large artifacts stay **gitignored** under `runs/` and `outputs/`.

## Directory layout

### Experiment runs (`runs/`)

All scripted experiments use the shared helper in `litevla.experiment`:

```
runs/
├── inference/          # offline inference and dummy pipeline runs
│   └── <run_id>/
├── finetune/           # LoRA / supervised training runs
│   └── <run_id>/
├── benchmark/          # latency and throughput measurements
│   └── <run_id>/
└── deploy/             # quantization and export experiments
    └── <run_id>/
```

Each run directory contains:

| File / folder | Purpose |
|---------------|---------|
| `config.yaml` | Resolved configuration after defaults merge and validation |
| `metadata.json` | Timestamp, Lite-VLA version, Python/platform, git commit, optional torch info |
| `metrics.json` | Run-specific measurements and status |
| `artifacts/` | Checkpoints, exported models, plots (created empty at run start) |

### Incidental outputs (`outputs/`)

Use `outputs/` for non-run artifacts that are not full experiments, for example camera frame dumps configured via `ros.frame_save_dir` in config. These paths are gitignored but are not managed by `litevla.experiment`.

## Run ID naming

Run IDs are UTC timestamps: `YYYYMMDDTHHMMSS` (example: `20250617T143022`).

When a label is provided, it is slugified and prepended:

```
dummy-pipeline_20250617T143022
```

Rules:

- Labels are lowercased; spaces and punctuation become `-`.
- Labels must contain at least one alphanumeric character.
- Do not put secrets or absolute home paths in labels.

## Metadata schema (`metadata.json`)

Required fields written by `collect_metadata()`:

| Field | Type | Description |
|-------|------|-------------|
| `run_id` | string | Directory name for this run |
| `kind` | string | One of `inference`, `training`, `benchmark`, `deploy` |
| `created_at` | string | ISO-8601 UTC timestamp |
| `litevla_version` | string | Package version from `litevla.__version__` |
| `python_version` | string | Interpreter version |
| `platform` | string | `platform.platform()` string |
| `hostname` | string | Machine hostname |
| `git` | object | `commit`, `branch`, `dirty` (null when git is unavailable) |
| `torch` | object or null | `version`, `cuda_available`, `cuda_version` when torch is installed |
| `config_path` | string or null | Source config file path, when known |

Scripts may add top-level keys via `metadata_extra` when creating an `ExperimentRun`.

## Metrics schema (`metrics.json`)

`metrics.json` is a single JSON object. Always include:

| Field | Type | Description |
|-------|------|-------------|
| `status` | string | `success` or `failed` |
| `duration_ms` | number | Wall-clock duration when applicable |

Add kind-specific keys under the same object. Recommended fields:

| Kind | Suggested keys |
|------|----------------|
| `inference` | `actions`, `mode`, `model_path` |
| `training` | `epoch`, `step`, `loss`, `val_loss`, `seed` |
| `benchmark` | `iterations`, `warmup`, `latency_ms_mean`, `latency_ms_p95`, `device` |
| `deploy` | `quantization`, `model_size_mb`, `export_format` |

## Python API

```python
from litevla.config import load_config
from litevla.experiment import ExperimentRun

config = load_config("configs/default.example.yaml")

with ExperimentRun(
    "inference",
    config,
    label="baseline",
    config_path="configs/default.example.yaml",
) as run:
    # ... do work ...
    run.write_metrics(
        {
            "status": "success",
            "duration_ms": 42,
            "mode": config["runtime"]["mode"],
        }
    )
    checkpoint = run.artifacts_dir() / "adapter.safetensors"
```

Lower-level helpers are also available: `run_directory`, `make_run_id`, `save_config_snapshot`, `save_metadata`, `save_metrics`, and `collect_metadata`.

## Script conventions

1. Accept an optional `--log-run` flag (or always log for long-running jobs).
2. Pass the resolved config and source config path into `ExperimentRun`.
3. Write `metrics.json` on both success and failure (`status: failed` plus an `error` string).
4. Document the torch wheel/CUDA build in metadata when GPU results matter (see `requirements.md`).
5. Never commit `runs/`, `outputs/`, or local config overrides.

## Example: dummy pipeline

```bash
python scripts/run_dummy_pipeline.py --log-run --run-label dummy-pipeline
```

This creates `runs/inference/<run_id>/` with config, metadata, and metrics for the scripted actions.

## Comparing runs

To compare two benchmark runs:

1. Open each run's `metadata.json` to confirm git commit, torch version, and config path.
2. Diff the `config.yaml` files for parameter changes.
3. Compare numeric fields in `metrics.json` (latency, loss, and so on).

For tabular summaries, load metrics with pandas or a small script that walks `runs/benchmark/*/metrics.json`.
