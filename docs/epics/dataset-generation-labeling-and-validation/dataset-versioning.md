# Dataset versioning and documentation

**Epic:** Dataset Generation, Labeling, and Validation (105) · **Jira epic:** VLA-6 · **Story:** VLA-47 / 1035 · **Subtasks:** 10105 (naming), 10106 (stats), 10107 (dataset card)

**Human-readable version (browser):** [`dataset-versioning.html`](dataset-versioning.html)

## Executive summary

VLA-47 packages a **processed dataset release** under `data/processed/vMAJOR.MINOR.PATCH/`: validated JSONL splits, optional augmented images, machine-readable `validation_report.json` (from VLA-45), and human-readable `DATASET_CARD.md`. Version strings are validated before any path is constructed so typos cannot write outside the processed tree.

## API contract and data flow

```text
build_starter_dataset()  or  manual JSONL
        │
        ▼
build_version_artifacts(version="v0.1.0", train_jsonl=..., val_jsonl=...)
        │
        ├── validate_dataset(train) ──> validation_report.json
        ├── validate_dataset(val)   ──> validation_report_val.json  (if present)
        └── render_dataset_card()   ──> DATASET_CARD.md

data/processed/v0.1.0/
├── train.jsonl
├── val.jsonl
├── images/                      # synthetic augmentations (gitignored)
├── validation_report.json       # 10106 stats
├── validation_report_val.json
└── DATASET_CARD.md              # 10107 human summary
```

| Convention | Rule |
|------------|------|
| Version id | `^v\d+\.\d+\.\d+$` — e.g. `v0.1.0`, `v1.0.0` |
| Stats file | `DatasetValidationReport.to_dict()` as JSON |
| Card | Markdown from `render_dataset_card()` |
| Config mirror | `configs/default.example.yaml` → `data.processed_version` |

**Trade-off:** Stats and card are regenerated on each `--write-artifacts` run (overwrite), not append-only changelog — git history owns version diffs for MVP.

## Implementation breakdown

### Version naming (10105) — `litevla/data/versioning.py`

```python
VERSION_PATTERN = re.compile(r"^v\d+\.\d+\.\d+$")

def processed_dir(version: str, *, repo_root=None) -> Path:
    if not is_valid_processed_version(version):
        raise ValueError(...)
    return repo_root / "data" / "processed" / version
```

- **Design note:** `processed_version` in config and builder `--version` must match this pattern.
- **Gotcha:** `v0.1` or `0.1.0` are rejected — include the `v` prefix.

### Stats file (10106)

```python
write_dataset_stats(report, version="v0.1.0")
# writes data/processed/v0.1.0/validation_report.json
```

Report includes: `record_count`, `action_counts`, `source_counts`, `missing_images`, `duplicate_ids`, full `issues[]`.

### Dataset card (10107)

`render_dataset_card()` produces markdown with:

- Scope and limitations (editable parameters)
- Train/val row counts and paths
- Label and source distribution tables
- Validation pass/fail with error/warning counts

### Orchestrator

```python
build_version_artifacts(
    version="v0.1.0",
    train_jsonl="data/processed/v0.1.0/train.jsonl",
    val_jsonl="data/processed/v0.1.0/val.jsonl",
    check_images=True,
)
```

### CLI integration

```bash
# After VLA-43 build
python scripts/build_starter_dataset.py --write-artifacts

# Or validate existing tree
python scripts/validate_dataset.py --version v0.1.0 --write-artifacts

# Skip image check when PNGs not local
python scripts/build_starter_dataset.py --write-artifacts --skip-image-check
```

## Engineering decisions

**ADR: Semver-style folder names (10105)**  
Status: Accepted  
Context: Need stable paths for config, loader, and training scripts.  
Decision: `vMAJOR.MINOR.PATCH` directory under `data/processed/`.  
Alternatives rejected: Date stamps only (harder to reference in configs); unversioned `latest/` (ambiguous).

**ADR: Stats from validator not builder (10106)**  
Status: Accepted  
Decision: `validation_report.json` is output of VLA-45 `validate_dataset`, not ad-hoc builder counters.  
Consequences: Same schema whether artifacts run after build or on reviewed JSONL.

**ADR: DATASET_CARD as generated markdown (10107)**  
Status: Accepted  
Decision: Card is rendered from live validation reports, not hand-maintained.  
Consequences: Edit `scope` / `limitations` params in code or re-run with custom wrapper for releases.

## Verification patterns

```bash
pytest tests/test_dataset_versioning.py -q
python scripts/validate_dataset.py --version v0.1.0 --write-artifacts --skip-image-check
```

| Test | Contract defended |
|------|-------------------|
| `test_version_pattern` | Accept/reject version strings |
| `test_build_version_artifacts` | End-to-end stats + card paths |
| `test_write_dataset_stats_and_card` | JSON + markdown content |

## Related

- [dataset-validation.md](dataset-validation.md) (VLA-45 report source)
- [synthetic-starter-dataset.md](synthetic-starter-dataset.md) (VLA-43 build entry point)
- [`data/README.md`](../../../../data/README.md) (folder layout)
- [`configs/default.example.yaml`](../../../../configs/default.example.yaml) (`data.processed_version`)

## Open questions

- **Changelog file:** Optional `CHANGELOG.md` per version for human release notes (not MVP).
- **DVC / remote storage:** Large processed sets may move to object storage; paths stay repo-relative for local MVP.
