"""Pure helpers for raw dataset capture records (VLA-42)."""

from __future__ import annotations

from typing import Any


def build_command_record(
    *,
    stamp: str,
    sim_stamp_sec: int,
    sim_stamp_nanosec: int,
    source: str,
    action: str,
    linear_x: float,
    angular_z: float,
) -> dict[str, Any]:
    """Build one raw commands.jsonl row with sim-time alignment fields."""
    return {
        "stamp": stamp,
        "sim_stamp_sec": sim_stamp_sec,
        "sim_stamp_nanosec": sim_stamp_nanosec,
        "source": source,
        "action": action,
        "linear_x": linear_x,
        "angular_z": angular_z,
    }
