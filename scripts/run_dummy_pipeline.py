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

from litevla.actions import (
    ACTION_NAMES,
    CommandSmoother,
    SmoothingConfig,
    safe_command_from_action,
    safe_command_from_text,
    smoothing_config_from_mapping,
)
from litevla.config import ConfigError, example_config_path, load_config
from litevla.experiment import ExperimentRun

DEFAULT_ACTION_SEQUENCE: tuple[str, ...] = (
    "MOVE_FORWARD",
    "MOVE_FORWARD",
    "TURN_LEFT",
    "STOP",
)


def run_dummy_pipeline(
    config: dict,
    *,
    log_run: bool = False,
    run_label: str | None = None,
    config_path: Path | None = None,
) -> int:
    runtime = config["runtime"]
    ros_cfg = config["ros"]
    safety = config["safety"]

    if runtime["mode"] != "dummy":
        print(
            "Runtime mode is not 'dummy'. Set runtime.mode: dummy in your config for this script.",
            file=sys.stderr,
        )
        return 1

    sequence = runtime.get("action_sequence") or list(DEFAULT_ACTION_SEQUENCE)
    if not sequence:
        sequence = list(ACTION_NAMES)

    def _execute(experiment: ExperimentRun | None) -> int:
        if experiment is not None:
            print(f"  run dir:     {experiment.directory}")
            print()

        print("Lite-VLA dummy pipeline")
        print(f"  instruction: {runtime['default_instruction']}")
        print(f"  heartbeat:   {runtime['heartbeat_hz']} Hz")
        print(f"  subscribe:   {ros_cfg['image_topic']}")
        print(f"  publish:     {ros_cfg['cmd_vel_topic']}")
        print(f"  sequence:    {list(sequence)}")
        print()

        safety = config["safety"]
        actions: list[dict[str, float | str]] = []
        for action in ACTION_NAMES:
            command = safe_command_from_action(
                action,
                max_linear_vel=safety["max_linear_vel"],
                max_angular_vel=safety["max_angular_vel"],
            )
            linear, angular = command.linear_x, command.angular_z
            actions.append({"action": action, "linear": linear, "angular": angular})
            print(f"action={action:13s}  linear={linear:.3f} m/s  angular={angular:.3f} rad/s")

        fallback = safe_command_from_text(
            "invalid model output",
            max_linear_vel=safety["max_linear_vel"],
            max_angular_vel=safety["max_angular_vel"],
        )
        print()
        print(
            f"fallback demo: invalid text -> {fallback.action.value} "
            f"(linear={fallback.linear_x:.3f}, angular={fallback.angular_z:.3f})"
        )

        smoothing_cfg = smoothing_config_from_mapping(config.get("smoothing"))
        heartbeat_hz = float(runtime["heartbeat_hz"])
        dt = 1.0 / heartbeat_hz if heartbeat_hz > 0 else 0.1
        smoother = CommandSmoother(smoothing_cfg)
        print()
        print(
            f"smoothing demo: enabled={smoothing_cfg.enabled} "
            f"heartbeat={heartbeat_hz:.1f} Hz dt={dt:.3f}s "
            f"rates=({smoothing_cfg.max_linear_rate}, {smoothing_cfg.max_angular_rate})"
        )
        for action_name in sequence:
            target = safe_command_from_action(
                action_name,
                max_linear_vel=safety["max_linear_vel"],
                max_angular_vel=safety["max_angular_vel"],
            )
            steps = 1 if target.action.value == "STOP" else 5
            for step in range(steps):
                command = smoother.step(target, dt=dt)
                print(
                    f"  step {step + 1}/{steps} action={action_name:13s} "
                    f"linear={command.linear_x:.3f} m/s  angular={command.angular_z:.3f} rad/s"
                )

        if experiment is not None:
            experiment.write_metrics(
                {
                    "status": "success",
                    "mode": runtime["mode"],
                    "actions": actions,
                    "action_count": len(actions),
                }
            )

        print()
        print("Dummy pipeline completed successfully.")
        return 0

    if not log_run:
        return _execute(None)

    with ExperimentRun(
        "inference",
        config,
        label=run_label or "dummy-pipeline",
        config_path=config_path,
        repo_root=ROOT,
    ) as experiment:
        return _execute(experiment)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        type=Path,
        default=example_config_path(),
        help="Path to YAML or JSON config (default: configs/default.example.yaml)",
    )
    parser.add_argument(
        "--log-run",
        action="store_true",
        help="Save config, metadata, and metrics under runs/inference/",
    )
    parser.add_argument(
        "--run-label",
        default=None,
        help="Optional label prefix for the run directory (used with --log-run)",
    )
    args = parser.parse_args(argv)

    try:
        config = load_config(args.config)
    except ConfigError as exc:
        print(f"Config error: {exc}", file=sys.stderr)
        return 1

    return run_dummy_pipeline(
        config,
        log_run=args.log_run,
        run_label=args.run_label,
        config_path=args.config,
    )


if __name__ == "__main__":
    raise SystemExit(main())
