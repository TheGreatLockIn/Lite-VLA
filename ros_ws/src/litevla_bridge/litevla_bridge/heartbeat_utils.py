"""Pure helpers for heartbeat timeout and diagnostics (VLA-27)."""

from __future__ import annotations

from typing import Any


def seconds_since(last_time: float | None, now: float) -> float | None:
    if last_time is None:
        return None
    return max(0.0, now - last_time)


def is_timed_out(
    now: float,
    last_action_time: float | None,
    last_frame_time: float | None,
    *,
    action_timeout_sec: float,
    frame_timeout_sec: float,
    require_frame: bool = True,
) -> bool:
    """Return True when action or camera freshness limits are exceeded."""
    action_age = seconds_since(last_action_time, now)
    frame_age = seconds_since(last_frame_time, now)

    if action_age is None or action_age > action_timeout_sec:
        return True
    if require_frame and (frame_age is None or frame_age > frame_timeout_sec):
        return True
    return False


def select_velocities(
    desired_linear: float,
    desired_angular: float,
    *,
    timed_out: bool,
) -> tuple[float, float]:
    if timed_out:
        return 0.0, 0.0
    return desired_linear, desired_angular


def build_diagnostics(
    *,
    heartbeat_hz: float,
    last_cmd: str,
    last_publish_stamp: str,
    action_age_ms: float | None,
    frame_age_ms: float | None,
    timed_out: bool,
) -> dict[str, Any]:
    return {
        "heartbeat_hz": heartbeat_hz,
        "last_cmd": last_cmd,
        "last_publish_stamp": last_publish_stamp,
        "action_age_ms": action_age_ms,
        "frame_age_ms": frame_age_ms,
        "timed_out": timed_out,
    }
