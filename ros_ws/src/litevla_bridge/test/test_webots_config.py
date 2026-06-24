"""Tests for Webots simulation configuration (no Webots runtime required)."""

from pathlib import Path

import yaml


def _webots_config_path() -> Path:
    return Path(__file__).resolve().parent.parent / "config" / "webots_sim.yaml"


def _world_path() -> Path:
    return Path(__file__).resolve().parent.parent / "worlds" / "mvp_arena.wbt"


def test_webots_sim_yaml_exists() -> None:
    assert _webots_config_path().is_file()


def test_mvp_arena_world_exists() -> None:
    text = _world_path().read_text(encoding="utf-8")
    assert "litevla_robot" in text
    assert "red_cube" in text
    assert "PositionSensor" in text


def _urdf_path() -> Path:
    return Path(__file__).resolve().parent.parent / "resource" / "litevla_robot.urdf"


def test_litevla_robot_urdf_enables_ros2_control() -> None:
    text = _urdf_path().read_text(encoding="utf-8")
    assert 'plugin type="webots_ros2_control::Ros2Control"' in text
    assert "<ros2_control" in text
    assert "left wheel motor" in text
    assert "right wheel motor" in text
    assert "<link name=\"base_link\"/>" in text


def test_webots_topics_match_project_defaults() -> None:
    with _webots_config_path().open(encoding="utf-8") as handle:
        cfg = yaml.safe_load(handle)["webots_sim"]
    assert cfg["image_topic"] == "/image_raw"
    assert cfg["cmd_vel_topic"] == "/cmd_vel"
    assert cfg["world_file"] == "mvp_arena.wbt"
