"""Tests for per-axis command smoothing (Story 1022)."""

from __future__ import annotations

import pytest

from litevla.actions import DiscreteAction, safe_command_from_action, safe_command_from_text
from litevla.actions.smoothing import (
    CommandSmoother,
    SmoothingConfig,
    is_stop_bypass,
    step_toward,
)


def test_step_toward_reaches_target_within_delta() -> None:
    assert step_toward(0.0, 0.2, 0.05) == pytest.approx(0.05)
    assert step_toward(0.18, 0.2, 0.05) == pytest.approx(0.2)


def test_step_toward_negative_direction() -> None:
    assert step_toward(0.0, -0.6, 0.1) == pytest.approx(-0.1)


def test_rate_limiter_respects_max_delta_per_tick() -> None:
    smoother = CommandSmoother(
        SmoothingConfig(max_linear_rate=0.5, max_angular_rate=1.5),
    )
    target = safe_command_from_action(
        DiscreteAction.MOVE_FORWARD,
        max_linear_vel=0.2,
        max_angular_vel=0.6,
    )

    command = smoother.step(target, dt=0.1)
    assert command.linear_x == pytest.approx(0.05)
    assert command.angular_z == pytest.approx(0.0)


def test_rate_limiter_reaches_target_after_enough_steps() -> None:
    smoother = CommandSmoother(
        SmoothingConfig(max_linear_rate=0.5, max_angular_rate=1.5),
    )
    target = safe_command_from_action(
        DiscreteAction.TURN_LEFT,
        max_linear_vel=0.2,
        max_angular_vel=0.6,
    )

    command = target
    for _ in range(20):
        command = smoother.step(target, dt=0.1)

    assert command.linear_x == pytest.approx(0.0)
    assert command.angular_z == pytest.approx(0.6)


def test_stop_bypass_is_immediate() -> None:
    smoother = CommandSmoother(SmoothingConfig())
    forward = safe_command_from_action(
        DiscreteAction.MOVE_FORWARD,
        max_linear_vel=0.2,
        max_angular_vel=0.6,
    )
    smoother.step(forward, dt=0.1)
    assert smoother.linear_x == pytest.approx(0.05)

    stop = safe_command_from_action(
        DiscreteAction.STOP,
        max_linear_vel=0.2,
        max_angular_vel=0.6,
    )
    command = smoother.step(stop, dt=0.1)
    assert command.linear_x == pytest.approx(0.0)
    assert command.angular_z == pytest.approx(0.0)
    assert smoother.linear_x == pytest.approx(0.0)
    assert smoother.angular_z == pytest.approx(0.0)


def test_parse_failure_stop_bypasses_smoothing() -> None:
    smoother = CommandSmoother(SmoothingConfig())
    forward = safe_command_from_action(
        DiscreteAction.MOVE_FORWARD,
        max_linear_vel=0.2,
        max_angular_vel=0.6,
    )
    smoother.step(forward, dt=0.1)

    stop = safe_command_from_text(
        "invalid model output",
        max_linear_vel=0.2,
        max_angular_vel=0.6,
    )
    assert stop.action is DiscreteAction.STOP

    command = smoother.step(stop, dt=0.1)
    assert command.linear_x == pytest.approx(0.0)
    assert command.angular_z == pytest.approx(0.0)


def test_disabled_smoothing_passes_target_through() -> None:
    smoother = CommandSmoother(SmoothingConfig(enabled=False))
    target = safe_command_from_action(
        DiscreteAction.MOVE_FORWARD,
        max_linear_vel=0.2,
        max_angular_vel=0.6,
    )

    command = smoother.step(target, dt=0.1)
    assert command.linear_x == pytest.approx(0.2)
    assert command.angular_z == pytest.approx(0.0)


def test_retargeting_mid_ramp() -> None:
    smoother = CommandSmoother(SmoothingConfig(max_linear_rate=0.5, max_angular_rate=1.5))
    forward = safe_command_from_action(
        DiscreteAction.MOVE_FORWARD,
        max_linear_vel=0.2,
        max_angular_vel=0.6,
    )
    turn = safe_command_from_action(
        DiscreteAction.TURN_LEFT,
        max_linear_vel=0.2,
        max_angular_vel=0.6,
    )

    smoother.step(forward, dt=0.1)
    command = smoother.step(turn, dt=0.1)

    assert command.linear_x == pytest.approx(0.0)
    assert command.angular_z == pytest.approx(0.15)


@pytest.mark.parametrize(
    ("action", "expected"),
    [
        (DiscreteAction.STOP, True),
        ("STOP", True),
        (DiscreteAction.MOVE_FORWARD, False),
        ("FORWARD", False),
    ],
)
def test_is_stop_bypass(action: DiscreteAction | str, expected: bool) -> None:
    assert is_stop_bypass(action) is expected


def test_step_velocities_wrapper() -> None:
    smoother = CommandSmoother(SmoothingConfig(max_linear_rate=0.5, max_angular_rate=1.5))
    linear, angular = smoother.step_velocities(
        target_linear=0.2,
        target_angular=0.0,
        action=DiscreteAction.MOVE_FORWARD,
        dt=0.1,
    )
    assert linear == pytest.approx(0.05)
    assert angular == pytest.approx(0.0)
