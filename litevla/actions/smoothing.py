"""Per-axis rate-limited command smoothing with immediate STOP bypass."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Mapping

from litevla.actions.safety import SafeCommand
from litevla.actions.schema import DiscreteAction

# Default slew rates reach MVP nominal speeds from rest in ~400 ms (RSK-05).
DEFAULT_MAX_LINEAR_RATE: float = 0.5  # m/s per second
DEFAULT_MAX_ANGULAR_RATE: float = 1.5  # rad/s per second


def step_toward(current: float, target: float, max_delta: float) -> float:
    """Move *current* toward *target* by at most *max_delta*."""
    if max_delta <= 0.0:
        return target

    delta = target - current
    if abs(delta) <= max_delta:
        return target
    return current + math.copysign(max_delta, delta)


def is_stop_bypass(action: DiscreteAction | str) -> bool:
    """Return True when smoothing must snap immediately to zero velocity."""
    if isinstance(action, str):
        try:
            action = DiscreteAction(action)
        except ValueError:
            return False
    return action is DiscreteAction.STOP


@dataclass(frozen=True)
class SmoothingConfig:
    """Configurable per-axis slew-rate limits for command smoothing."""

    enabled: bool = True
    max_linear_rate: float = DEFAULT_MAX_LINEAR_RATE
    max_angular_rate: float = DEFAULT_MAX_ANGULAR_RATE


def smoothing_config_from_mapping(data: Mapping[str, Any] | None) -> SmoothingConfig:
    """Build ``SmoothingConfig`` from a config ``smoothing`` mapping."""
    if not data:
        return SmoothingConfig()

    return SmoothingConfig(
        enabled=bool(data.get("enabled", True)),
        max_linear_rate=float(data.get("max_linear_rate", DEFAULT_MAX_LINEAR_RATE)),
        max_angular_rate=float(data.get("max_angular_rate", DEFAULT_MAX_ANGULAR_RATE)),
    )


@dataclass
class CommandSmoother:
    """Stateful per-axis rate limiter between safe targets and published velocities."""

    config: SmoothingConfig
    linear_x: float = 0.0
    angular_z: float = 0.0

    def reset(self) -> None:
        """Clear internal state to zero velocity."""
        self.linear_x = 0.0
        self.angular_z = 0.0

    def step(self, target: SafeCommand, dt: float) -> SafeCommand:
        """Rate-limit toward *target*, bypassing smoothing for ``STOP``."""
        if is_stop_bypass(target.action):
            self.reset()
            return target

        if not self.config.enabled or dt <= 0.0:
            self.linear_x = target.linear_x
            self.angular_z = target.angular_z
            return target

        max_linear_delta = self.config.max_linear_rate * dt
        max_angular_delta = self.config.max_angular_rate * dt
        self.linear_x = step_toward(self.linear_x, target.linear_x, max_linear_delta)
        self.angular_z = step_toward(self.angular_z, target.angular_z, max_angular_delta)

        return SafeCommand(
            linear_x=self.linear_x,
            angular_z=self.angular_z,
            action=target.action,
            original_text=target.original_text,
            events=target.events,
        )

    def step_velocities(
        self,
        *,
        target_linear: float,
        target_angular: float,
        action: DiscreteAction | str,
        dt: float,
        original_text: str | None = None,
    ) -> tuple[float, float]:
        """Convenience wrapper for ROS nodes that track desired twist + action label."""
        target = SafeCommand(
            linear_x=target_linear,
            angular_z=target_angular,
            action=action if isinstance(action, DiscreteAction) else DiscreteAction(action),
            original_text=original_text,
            events=(),
        )
        smoothed = self.step(target, dt)
        return smoothed.linear_x, smoothed.angular_z
