"""Safety gate: clamp velocities and fail-safe STOP on invalid discrete input."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum

from litevla.actions.parser import parse_discrete_action
from litevla.actions.schema import (
    ACTION_VELOCITIES,
    DiscreteAction,
    action_to_twist,
    clamp_velocity,
)

_LOG = logging.getLogger(__name__)


class SafetyEventKind(str, Enum):
    """Reason a command was accepted, clamped, or replaced with STOP."""

    OK = "ok"
    PARSE_FAILURE = "parse_failure"
    VELOCITY_CLAMPED = "velocity_clamped"


@dataclass(frozen=True)
class SafetyEvent:
    """Structured record of a safety gate decision."""

    kind: SafetyEventKind
    message: str
    original_text: str | None = None


@dataclass(frozen=True)
class SafeCommand:
    """Bounded velocity command ready for ``/cmd_vel`` publishing."""

    linear_x: float
    angular_z: float
    action: DiscreteAction
    original_text: str | None
    events: tuple[SafetyEvent, ...]


def clamp_twist_velocities(
    linear_x: float,
    angular_z: float,
    *,
    max_linear_vel: float,
    max_angular_vel: float,
) -> tuple[float, float, bool]:
    """Clamp twist components to configured limits.

    Returns ``(linear_x, angular_z, was_clamped)``.
    """
    clamped_linear = clamp_velocity(linear_x, max_linear_vel)
    clamped_angular = clamp_velocity(angular_z, max_angular_vel)
    was_clamped = clamped_linear != linear_x or clamped_angular != angular_z
    return clamped_linear, clamped_angular, was_clamped


def _log_event(event: SafetyEvent, *, logger: logging.Logger) -> None:
    if event.kind is SafetyEventKind.OK:
        logger.debug(event.message)
        return
    detail = event.message
    if event.original_text is not None:
        detail = f"{detail} (original_text={event.original_text!r})"
    logger.warning(detail)


def safe_command_from_action(
    action: DiscreteAction | str,
    *,
    max_linear_vel: float,
    max_angular_vel: float,
    original_text: str | None = None,
    logger: logging.Logger | None = None,
) -> SafeCommand:
    """Map a known discrete action to a clamped safe command."""
    if isinstance(action, str):
        action = DiscreteAction(action)

    log = logger or _LOG
    nominal_linear, nominal_angular = ACTION_VELOCITIES[action]
    linear, angular = action_to_twist(
        action,
        max_linear_vel=max_linear_vel,
        max_angular_vel=max_angular_vel,
    )

    if linear != nominal_linear or angular != nominal_angular:
        message = (
            f"Velocity clamped for {action.value}: "
            f"({nominal_linear}, {nominal_angular}) -> ({linear}, {angular})"
        )
        event = SafetyEvent(
            kind=SafetyEventKind.VELOCITY_CLAMPED,
            message=message,
            original_text=original_text,
        )
    else:
        event = SafetyEvent(
            kind=SafetyEventKind.OK,
            message=f"Action {action.value} within limits",
            original_text=original_text,
        )

    _log_event(event, logger=log)
    return SafeCommand(
        linear_x=linear,
        angular_z=angular,
        action=action,
        original_text=original_text,
        events=(event,),
    )


def safe_command_from_text(
    text: str,
    *,
    max_linear_vel: float,
    max_angular_vel: float,
    logger: logging.Logger | None = None,
) -> SafeCommand:
    """Parse VLA text, fallback to STOP on failure, and clamp velocities."""
    log = logger or _LOG
    parsed = parse_discrete_action(text)
    if parsed is None:
        message = "Parse failure; falling back to STOP"
        event = SafetyEvent(
            kind=SafetyEventKind.PARSE_FAILURE,
            message=message,
            original_text=text,
        )
        _log_event(event, logger=log)
        return SafeCommand(
            linear_x=0.0,
            angular_z=0.0,
            action=DiscreteAction.STOP,
            original_text=text,
            events=(event,),
        )

    return safe_command_from_action(
        parsed,
        max_linear_vel=max_linear_vel,
        max_angular_vel=max_angular_vel,
        original_text=text,
        logger=log,
    )
