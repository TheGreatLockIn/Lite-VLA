"""Monorepo import helper for litevla.actions inside ros_ws nodes."""

from __future__ import annotations

import sys
from pathlib import Path


def _find_repo_root() -> Path:
    """Locate monorepo root whether running from source, build, or install."""
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "litevla" / "actions" / "schema.py").is_file():
            return parent
    raise ImportError(
        "Cannot locate monorepo root containing litevla.actions "
        f"(searched upward from {here})"
    )


_REPO_ROOT = _find_repo_root()
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from litevla.actions import (  # noqa: E402
    ACTION_NAMES,
    DEFAULT_ACTION_SEQUENCE,
    DiscreteAction,
    action_to_twist,
    is_valid_action,
    parse_action,
)

__all__ = [
    "ACTION_NAMES",
    "DEFAULT_ACTION_SEQUENCE",
    "DiscreteAction",
    "action_to_twist",
    "is_valid_action",
    "parse_action",
]
