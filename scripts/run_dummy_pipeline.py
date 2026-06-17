#!/usr/bin/env python3
"""Run the Lite-VLA dummy control pipeline using configuration settings.

This script does not require ROS or model weights. It loads config, validates
settings, and prints the velocity commands that would be published in dummy mode.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from litevla.config import ConfigError, example_config_path, load_config

DUMMY_ACTIONS = ("FORWARD", "STOP")


def _clamp(value: float, limit: float) -> float:
    return max(-limit, min(limit, value))


def _dummy_twist(action: str, config: dict) -> tuple[float, float]:
    max_linear = config["safety"]["max_linear_vel"]
    max_angular = config["safety"]["max_angular_vel"]

    if action == "FORWARD":
        return _clamp(0.2, max_linear), 0.0
    return 0.0, _clamp(0.0, max_angular)


def run_dummy_pipeline(config: dict) -> int:
    runtime = config["runtime"]
    ros_cfg = config["ros"]

    if runtime["mode"] != "dummy":
        print(
            "Runtime mode is not 'dummy'. "
            "Set runtime.mode: dummy in your config for this script.",
            file=sys.stderr,
        )
        return 1

    print("Lite-VLA dummy pipeline")
    print(f"  instruction: {runtime['default_instruction']}")
    print(f"  heartbeat:   {runtime['heartbeat_hz']} Hz")
    print(f"  subscribe:   {ros_cfg['image_topic']}")
    print(f"  publish:     {ros_cfg['cmd_vel_topic']}")
    print()

    for action in DUMMY_ACTIONS:
        linear, angular = _dummy_twist(action, config)
        print(f"action={action:7s}  linear={linear:.3f} m/s  angular={angular:.3f} rad/s")

    print()
    print("Dummy pipeline completed successfully.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        type=Path,
        default=example_config_path(),
        help="Path to YAML or JSON config (default: configs/default.example.yaml)",
    )
    args = parser.parse_args(argv)

    try:
        config = load_config(args.config)
    except ConfigError as exc:
        print(f"Config error: {exc}", file=sys.stderr)
        return 1

    return run_dummy_pipeline(config)


if __name__ == "__main__":
    raise SystemExit(main())
