"""Load and validate Lite-VLA YAML/JSON configuration files."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

import jsonschema
import yaml
from jsonschema import Draft202012Validator

PACKAGE_DIR = Path(__file__).resolve().parent
REPO_ROOT = PACKAGE_DIR.parent.parent
SCHEMA_PATH = PACKAGE_DIR / "schema.json"
EXAMPLE_CONFIG_PATH = REPO_ROOT / "configs" / "default.example.yaml"

DEFAULT_CONFIG: dict[str, Any] = {
    "runtime": {
        "mode": "dummy",
        "heartbeat_hz": 10.0,
        "default_instruction": "explore the area",
    },
    "model": {
        "path": "models/demo",
        "device": "cpu",
        "max_tokens": 32,
        "context_length": 2048,
    },
    "ros": {
        "image_topic": "/image_raw",
        "cmd_vel_topic": "/cmd_vel",
        "diagnostics_topic": "/litevla/diagnostics",
        "record_frames": False,
        "frame_save_dir": "outputs/frames",
    },
    "safety": {
        "max_linear_vel": 0.5,
        "max_angular_vel": 1.0,
    },
    "benchmark": {
        "iterations": 100,
        "warmup": 5,
    },
}


class ConfigError(ValueError):
    """Raised when a configuration file cannot be loaded or validated."""


def schema_path() -> Path:
    """Return the path to the JSON Schema file."""
    return SCHEMA_PATH


def example_config_path() -> Path:
    """Return the path to the committed example configuration."""
    return EXAMPLE_CONFIG_PATH


def default_config() -> dict[str, Any]:
    """Return a deep copy of the built-in default configuration."""
    return deepcopy(DEFAULT_CONFIG)


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = deepcopy(value)
    return merged


def _load_raw_config(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise ConfigError(f"Config file not found: {path}")

    text = path.read_text(encoding="utf-8")
    suffix = path.suffix.lower()

    if suffix in {".yaml", ".yml"}:
        data = yaml.safe_load(text)
    elif suffix == ".json":
        data = json.loads(text)
    else:
        raise ConfigError(
            f"Unsupported config format '{path.suffix}'. Use .yaml, .yml, or .json."
        )

    if data is None:
        return {}
    if not isinstance(data, dict):
        raise ConfigError(f"Config root must be a mapping, got {type(data).__name__}.")
    return data


def _load_schema() -> dict[str, Any]:
    try:
        return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ConfigError(f"Invalid JSON schema at {SCHEMA_PATH}: {exc}") from exc


def _format_validation_error(error: jsonschema.ValidationError) -> str:
    path = " -> ".join(str(part) for part in error.absolute_path) or "<root>"
    return f"{path}: {error.message}"


def _validate_config(config: dict[str, Any], schema: dict[str, Any]) -> None:
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(config), key=lambda err: list(err.absolute_path))
    if not errors:
        return

    details = "\n".join(f"  - {_format_validation_error(error)}" for error in errors)
    raise ConfigError(f"Configuration validation failed:\n{details}")


def load_config(
    path: str | Path | None = None,
    *,
    apply_defaults: bool = True,
) -> dict[str, Any]:
    """Load, merge defaults, and validate a Lite-VLA configuration file.

    Args:
        path: Path to a YAML or JSON config. When omitted, loads
            ``configs/default.example.yaml``.
        apply_defaults: When True, missing keys are filled from built-in defaults
            before validation.

    Returns:
        Validated configuration mapping.

    Raises:
        ConfigError: On missing files, parse errors, or schema validation failures.
    """
    config_path = Path(path) if path is not None else EXAMPLE_CONFIG_PATH
    raw = _load_raw_config(config_path)
    config = _deep_merge(DEFAULT_CONFIG, raw) if apply_defaults else raw
    _validate_config(config, _load_schema())
    return config
