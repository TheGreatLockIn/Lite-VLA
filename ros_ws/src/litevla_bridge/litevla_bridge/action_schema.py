"""Monorepo import helper for litevla.actions inside ros_ws nodes."""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[4]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from litevla.actions import (  # noqa: E402
    ACTION_NAMES,
    DiscreteAction,
    action_to_twist,
    is_valid_action,
    parse_discrete_action,
)
from litevla.actions.smoothing import CommandSmoother, SmoothingConfig, is_stop_bypass  # noqa: E402

DEFAULT_ACTION_SEQUENCE: tuple[str, ...] = (
    "MOVE_FORWARD",
    "MOVE_FORWARD",
    "TURN_LEFT",
    "STOP",
)


def parse_action(name: str) -> str:
    """Return a validated action token or ``STOP`` when *name* is invalid."""
    parsed = parse_discrete_action(name)
    if parsed is None:
        return DiscreteAction.STOP.value
    return parsed.value


__all__ = [
    "ACTION_NAMES",
    "DEFAULT_ACTION_SEQUENCE",
    "CommandSmoother",
    "DiscreteAction",
    "SmoothingConfig",
    "action_to_twist",
    "is_stop_bypass",
    "is_valid_action",
    "parse_action",
    "parse_discrete_action",
]
