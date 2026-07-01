"""Tests for Lite-VLA configuration loading."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from litevla.config import ConfigError, example_config_path, load_config


def test_example_config_loads() -> None:
    config = load_config(example_config_path())
    assert config["runtime"]["mode"] == "dummy"
    assert config["ros"]["image_topic"] == "/image_raw"
    assert config["ros"]["cmd_vel_topic"] == "/cmd_vel"
    assert config["smoothing"]["enabled"] is True
    assert config["smoothing"]["max_linear_rate"] == 0.5


def test_default_config_loads_when_path_omitted() -> None:
    config = load_config()
    assert config["benchmark"]["iterations"] == 100


def test_partial_config_receives_defaults(tmp_path: Path) -> None:
    config_file = tmp_path / "partial.yaml"
    config_file.write_text(
        yaml.safe_dump({"runtime": {"mode": "model"}, "model": {"path": "hf/demo"}}),
        encoding="utf-8",
    )

    config = load_config(config_file)
    assert config["runtime"]["mode"] == "model"
    assert config["model"]["path"] == "hf/demo"
    assert config["ros"]["cmd_vel_topic"] == "/cmd_vel"
    assert config["safety"]["max_linear_vel"] == 0.5


def test_missing_required_section_fails_with_clear_error(tmp_path: Path) -> None:
    config_file = tmp_path / "invalid.yaml"
    config_file.write_text("runtime:\n  mode: dummy\n", encoding="utf-8")

    with pytest.raises(ConfigError, match="Configuration validation failed"):
        load_config(config_file, apply_defaults=False)


def test_missing_required_key_fails_with_clear_error(tmp_path: Path) -> None:
    config_file = tmp_path / "invalid.yaml"
    payload = {
        "runtime": {"mode": "dummy", "heartbeat_hz": 10, "default_instruction": "go"},
        "model": {"path": "models/demo", "device": "cpu", "max_tokens": 32},
        "ros": {
            "image_topic": "/image_raw",
            "cmd_vel_topic": "/cmd_vel",
            "diagnostics_topic": "/litevla/diagnostics",
            "record_frames": False,
            "frame_save_dir": "outputs/frames",
        },
        "safety": {"max_linear_vel": 0.5, "max_angular_vel": 1.0},
        "benchmark": {"iterations": 100, "warmup": 5},
    }
    config_file.write_text(yaml.safe_dump(payload), encoding="utf-8")

    with pytest.raises(ConfigError, match="context_length"):
        load_config(config_file, apply_defaults=False)


def test_invalid_topic_name_fails_validation(tmp_path: Path) -> None:
    config_file = tmp_path / "invalid.yaml"
    config_file.write_text(
        yaml.safe_dump({"ros": {"image_topic": "image_raw"}}),
        encoding="utf-8",
    )

    with pytest.raises(ConfigError, match="image_topic"):
        load_config(config_file)


def test_missing_file_raises_config_error(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="Config file not found"):
        load_config(tmp_path / "missing.yaml")


def test_json_config_loads(tmp_path: Path) -> None:
    config_file = tmp_path / "config.json"
    config_file.write_text(
        '{"runtime": {"mode": "dummy", "heartbeat_hz": 5, "default_instruction": "stop"}}',
        encoding="utf-8",
    )

    config = load_config(config_file)
    assert config["runtime"]["heartbeat_hz"] == 5
    assert config["model"]["device"] == "cpu"
