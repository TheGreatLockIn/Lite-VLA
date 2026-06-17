"""Create timestamped experiment run directories with config and metrics snapshots."""

from __future__ import annotations

import json
import platform
import re
import socket
import subprocess
from contextlib import AbstractContextManager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

import yaml

from litevla import __version__

ExperimentKind = Literal["inference", "training", "benchmark", "deploy"]

KIND_SUBDIRS: dict[ExperimentKind, str] = {
    "inference": "inference",
    "training": "finetune",
    "benchmark": "benchmark",
    "deploy": "deploy",
}

RUNS_ROOT = Path("runs")
CONFIG_FILENAME = "config.yaml"
METADATA_FILENAME = "metadata.json"
METRICS_FILENAME = "metrics.json"
ARTIFACTS_DIRNAME = "artifacts"

_LABEL_RE = re.compile(r"[^a-z0-9]+")


def slugify_label(label: str) -> str:
    """Convert a human label into a filesystem-safe run-id prefix."""
    slug = _LABEL_RE.sub("-", label.strip().lower()).strip("-")
    if not slug:
        raise ValueError("label must contain at least one alphanumeric character")
    return slug


def make_run_id(label: str | None = None, *, now: datetime | None = None) -> str:
    """Return a timestamped run id, optionally prefixed with a slugified label."""
    moment = now or datetime.now(UTC)
    timestamp = moment.strftime("%Y%m%dT%H%M%S")
    if label is None:
        return timestamp
    return f"{slugify_label(label)}_{timestamp}"


def run_directory(
    kind: ExperimentKind,
    *,
    run_id: str | None = None,
    label: str | None = None,
    base_dir: Path | str = RUNS_ROOT,
    create: bool = True,
) -> Path:
    """Return (and optionally create) the directory for an experiment run."""
    resolved_id = run_id or make_run_id(label)
    path = Path(base_dir) / KIND_SUBDIRS[kind] / resolved_id
    if create:
        path.mkdir(parents=True, exist_ok=True)
        (path / ARTIFACTS_DIRNAME).mkdir(exist_ok=True)
    return path


def _git_metadata(repo_root: Path | None = None) -> dict[str, Any]:
    root = repo_root or Path.cwd()
    try:
        commit = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=root,
            capture_output=True,
            text=True,
            check=True,
            timeout=2,
        ).stdout.strip()
        branch = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=root,
            capture_output=True,
            text=True,
            check=True,
            timeout=2,
        ).stdout.strip()
        dirty = (
            subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=root,
                capture_output=True,
                text=True,
                check=True,
                timeout=2,
            ).stdout.strip()
            != ""
        )
    except (OSError, subprocess.SubprocessError):
        return {"commit": None, "branch": None, "dirty": None}

    return {"commit": commit, "branch": branch, "dirty": dirty}


def _torch_metadata() -> dict[str, Any] | None:
    try:
        import torch
    except ImportError:
        return None

    cuda_available = bool(torch.cuda.is_available())
    cuda_version = torch.version.cuda if cuda_available else None
    return {
        "version": torch.__version__,
        "cuda_available": cuda_available,
        "cuda_version": cuda_version,
    }


def collect_metadata(
    *,
    kind: ExperimentKind,
    run_id: str,
    config_path: str | Path | None = None,
    repo_root: Path | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the standard metadata payload for a run."""
    created_at = datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    metadata: dict[str, Any] = {
        "run_id": run_id,
        "kind": kind,
        "created_at": created_at,
        "litevla_version": __version__,
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "hostname": socket.gethostname(),
        "git": _git_metadata(repo_root),
        "torch": _torch_metadata(),
        "config_path": str(config_path) if config_path is not None else None,
    }
    if extra:
        metadata.update(extra)
    return metadata


def save_config_snapshot(run_dir: Path, config: dict[str, Any]) -> Path:
    """Write the resolved configuration used for this run."""
    path = run_dir / CONFIG_FILENAME
    path.write_text(
        yaml.safe_dump(config, sort_keys=False, default_flow_style=False),
        encoding="utf-8",
    )
    return path


def save_metadata(run_dir: Path, metadata: dict[str, Any]) -> Path:
    """Write run metadata as JSON."""
    path = run_dir / METADATA_FILENAME
    path.write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def save_metrics(run_dir: Path, metrics: dict[str, Any]) -> Path:
    """Write run metrics as JSON."""
    path = run_dir / METRICS_FILENAME
    path.write_text(json.dumps(metrics, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


class ExperimentRun(AbstractContextManager["ExperimentRun"]):
    """Context manager that creates a run directory and writes config + metadata."""

    def __init__(
        self,
        kind: ExperimentKind,
        config: dict[str, Any],
        *,
        label: str | None = None,
        run_id: str | None = None,
        base_dir: Path | str = RUNS_ROOT,
        config_path: str | Path | None = None,
        metadata_extra: dict[str, Any] | None = None,
        repo_root: Path | None = None,
    ) -> None:
        self.kind = kind
        self.config = config
        self.label = label
        self.run_id = run_id or make_run_id(label)
        self.base_dir = Path(base_dir)
        self.config_path = config_path
        self.metadata_extra = metadata_extra
        self.repo_root = repo_root
        self.directory = run_directory(
            kind,
            run_id=self.run_id,
            base_dir=self.base_dir,
            create=True,
        )

    def write_metrics(self, metrics: dict[str, Any]) -> Path:
        """Persist metrics for this run."""
        return save_metrics(self.directory, metrics)

    def artifacts_dir(self) -> Path:
        """Return the artifacts subdirectory for checkpoints and exports."""
        return self.directory / ARTIFACTS_DIRNAME

    def __enter__(self) -> ExperimentRun:
        save_config_snapshot(self.directory, self.config)
        save_metadata(
            self.directory,
            collect_metadata(
                kind=self.kind,
                run_id=self.run_id,
                config_path=self.config_path,
                repo_root=self.repo_root,
                extra=self.metadata_extra,
            ),
        )
        return self

    def __exit__(self, *exc_info: object) -> None:
        return None
