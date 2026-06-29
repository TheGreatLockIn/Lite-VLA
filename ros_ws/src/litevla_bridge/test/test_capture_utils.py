"""Tests for raw capture record builders (VLA-42)."""

from litevla_bridge.capture_utils import build_command_record


def test_build_command_record_includes_sim_stamps() -> None:
    record = build_command_record(
        stamp="2026-06-24T12:00:01+00:00",
        sim_stamp_sec=42,
        sim_stamp_nanosec=123456789,
        source="teleop",
        action="MOVE_FORWARD",
        linear_x=0.3,
        angular_z=0.0,
    )
    assert record["sim_stamp_sec"] == 42
    assert record["sim_stamp_nanosec"] == 123456789
    assert record["action"] == "MOVE_FORWARD"
    assert record["linear_x"] == 0.3
