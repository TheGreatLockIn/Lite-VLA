# Continuous integration

This document describes Lite-VLA automated checks: what runs in CI, how to run the same steps locally, and what is intentionally out of scope.

**Human-readable version (browser):** [`ci.html`](ci.html)

For dependency installation, see [`requirements.md`](requirements.md) or run `./scripts/setup_python_env.sh`.

## Overview

GitHub Actions runs lightweight checks on every **pull request** and on **pushes to `main`/`master`**. The workflow installs the **dev** profile (`requirements/dev.txt`) and runs [`scripts/run_ci_checks.sh`](../scripts/run_ci_checks.sh).

Goals:

- Fast feedback on syntax, style, and tests
- Same commands locally and in CI
- No GPU, ROS 2, or optional train/deploy profiles required

## What runs in CI

| Step | Command | Purpose |
|------|---------|---------|
| Lint | `ruff check .` | Catch syntax errors, unused imports, and common bugs |
| Format | `ruff format --check .` | Ensure consistent formatting (no auto-fix in CI) |
| Tests | `pytest tests -m "not optional" -v` | Run unit and smoke tests |
| Sanity | `python3 scripts/run_dummy_pipeline.py` | Verify config loading and dummy control path |

Ruff settings live in [`pyproject.toml`](../pyproject.toml). Tests are discovered via [`pytest.ini`](../pytest.ini).

### Optional tests (not run in CI)

Tests marked `@pytest.mark.optional` require **train** or **deploy** profiles (`peft`, `bitsandbytes`, etc.). Run them locally after installing the matching profile:

```bash
pytest tests/smoke -m optional -v
```

## Run checks locally

1. Create the dev environment (once):

```bash
./scripts/setup_python_env.sh
source .venv/bin/activate
```

2. Run the full CI suite:

```bash
./scripts/run_ci_checks.sh
```

Individual steps:

```bash
ruff check .
ruff format --check .
pytest tests -m "not optional" -v
python3 scripts/run_dummy_pipeline.py
```

Auto-fix formatting before a PR:

```bash
ruff format .
```

## GitHub Actions workflow

Workflow file: [`.github/workflows/ci.yml`](../.github/workflows/ci.yml)

| Setting | Value |
|---------|-------|
| Runner | `ubuntu-latest` |
| Python | 3.12 |
| Dependencies | `requirements/dev.txt` |
| Entrypoint | `./scripts/run_ci_checks.sh` |

Failed jobs appear as a red check on the pull request. Fix the reported step and push again.

## Out of scope (for now)

These are **not** part of basic CI:

| Area | Why |
|------|-----|
| ROS 2 workspace build | Installed via apt and `ros_ws/`; separate setup story |
| GPU / CUDA tests | CI runners are CPU-only |
| Train / deploy profiles | Marked `optional`; install only when needed |
| Coverage gates | Not required for initial CI |
| Pre-commit hooks | Optional local convenience; not enforced yet |

## Related docs

- [`requirements.md`](requirements.md) — what `dev.txt` installs (pytest, ruff)
- [`AGENTS.md`](AGENTS.md) — documentation conventions for agents
