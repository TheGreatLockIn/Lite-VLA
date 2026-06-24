"""Tests for heartbeat_utils (no ROS runtime)."""

from litevla_bridge.heartbeat_utils import (
    build_diagnostics,
    format_age_ms,
    is_timed_out,
    select_velocities,
)


def test_select_velocities_stop_on_timeout() -> None:
    linear, angular = select_velocities(0.2, 0.6, timed_out=True)
    assert linear == 0.0
    assert angular == 0.0


def test_is_timed_out_when_action_stale() -> None:
    assert is_timed_out(
        now=10.0,
        last_action_time=9.0,
        last_frame_time=9.9,
        action_timeout_sec=0.5,
        frame_timeout_sec=2.0,
    )


def test_is_not_timed_out_when_fresh() -> None:
    assert not is_timed_out(
        now=10.0,
        last_action_time=9.8,
        last_frame_time=9.5,
        action_timeout_sec=0.5,
        frame_timeout_sec=2.0,
    )


def test_format_age_ms_handles_none() -> None:
    assert format_age_ms(None) == "n/a"
    assert format_age_ms(0.0123) == "12.3"


def test_build_diagnostics_payload() -> None:
    payload = build_diagnostics(
        heartbeat_hz=10.0,
        last_cmd="MOVE_FORWARD",
        last_publish_stamp="1.0",
        action_age_ms=12.3,
        frame_age_ms=45.0,
        timed_out=False,
    )
    assert payload["last_cmd"] == "MOVE_FORWARD"
    assert payload["timed_out"] is False
