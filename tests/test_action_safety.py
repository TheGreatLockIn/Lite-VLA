"""Tests for the discrete action safety gate."""

from __future__ import annotations

import logging

import pytest

from litevla.actions import DiscreteAction, safe_command_from_action, safe_command_from_text
from litevla.actions.safety import SafetyEventKind, clamp_twist_velocities


def test_clamp_twist_velocities_within_limits() -> None:
    linear, angular, was_clamped = clamp_twist_velocities(
        0.15,
        -0.4,
        max_linear_vel=0.2,
        max_angular_vel=0.6,
    )
    assert linear == pytest.approx(0.15)
    assert angular == pytest.approx(-0.4)
    assert was_clamped is False


def test_clamp_twist_velocities_exceeds_limits() -> None:
    linear, angular, was_clamped = clamp_twist_velocities(
        0.5,
        -1.2,
        max_linear_vel=0.2,
        max_angular_vel=0.6,
    )
    assert linear == pytest.approx(0.2)
    assert angular == pytest.approx(-0.6)
    assert was_clamped is True


@pytest.mark.parametrize(
    ("action", "expected"),
    [
        (DiscreteAction.MOVE_FORWARD, (0.2, 0.0)),
        (DiscreteAction.TURN_LEFT, (0.0, 0.6)),
        (DiscreteAction.STOP, (0.0, 0.0)),
    ],
)
def test_safe_command_from_action_at_mvp_limits(
    action: DiscreteAction,
    expected: tuple[float, float],
) -> None:
    command = safe_command_from_action(
        action,
        max_linear_vel=0.2,
        max_angular_vel=0.6,
    )
    assert (command.linear_x, command.angular_z) == expected
    assert command.action is action
    assert command.events[0].kind is SafetyEventKind.OK


def test_safe_command_from_action_clamps_to_config_limits() -> None:
    command = safe_command_from_action(
        DiscreteAction.MOVE_FORWARD,
        max_linear_vel=0.1,
        max_angular_vel=0.3,
    )
    assert command.linear_x == pytest.approx(0.1)
    assert command.angular_z == pytest.approx(0.0)
    assert command.events[0].kind is SafetyEventKind.VELOCITY_CLAMPED


@pytest.mark.parametrize(
    ("text", "expected_action", "expected_vel"),
    [
        ("MOVE_FORWARD", DiscreteAction.MOVE_FORWARD, (0.2, 0.0)),
        (" move_forward. ", DiscreteAction.MOVE_FORWARD, (0.2, 0.0)),
        ("STOP", DiscreteAction.STOP, (0.0, 0.0)),
    ],
)
def test_safe_command_from_text_valid_outputs(
    text: str,
    expected_action: DiscreteAction,
    expected_vel: tuple[float, float],
) -> None:
    command = safe_command_from_text(
        text,
        max_linear_vel=0.2,
        max_angular_vel=0.6,
    )
    assert command.action is expected_action
    assert (command.linear_x, command.angular_z) == expected_vel
    assert command.original_text == text
    assert command.events[0].kind is SafetyEventKind.OK


@pytest.mark.parametrize(
    "text",
    ["", "   ", "FORWARD", "I think we should go left", "not a command"],
)
def test_safe_command_from_text_invalid_outputs_stop(text: str) -> None:
    command = safe_command_from_text(
        text,
        max_linear_vel=0.2,
        max_angular_vel=0.6,
    )
    assert command.action is DiscreteAction.STOP
    assert command.linear_x == pytest.approx(0.0)
    assert command.angular_z == pytest.approx(0.0)
    assert command.original_text == text
    assert command.events[0].kind is SafetyEventKind.PARSE_FAILURE


def test_safe_command_from_text_logs_parse_failure(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.WARNING):
        safe_command_from_text(
            "invalid output",
            max_linear_vel=0.2,
            max_angular_vel=0.6,
        )
    assert any("Parse failure" in record.message for record in caplog.records)
    assert any("invalid output" in record.message for record in caplog.records)


def test_safe_command_from_action_logs_clamp_event(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.WARNING):
        safe_command_from_action(
            DiscreteAction.TURN_LEFT,
            max_linear_vel=0.2,
            max_angular_vel=0.3,
        )
    assert any("Velocity clamped" in record.message for record in caplog.records)
    assert any("TURN_LEFT" in record.message for record in caplog.records)
