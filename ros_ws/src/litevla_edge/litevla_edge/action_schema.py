from dataclasses import dataclass
import json
import re
from typing import Any


DISCRETE_ACTIONS = {
    "MOVE_FORWARD": (0.15, 0.0),
    "TURN_LEFT": (0.0, 0.4),
    "TURN_RIGHT": (0.0, -0.4),
    "STOP": (0.0, 0.0),
    "SLOW_DOWN": (0.05, 0.0),
}


@dataclass(frozen=True)
class ActionCommand:
    action: str
    linear_x: float
    angular_z: float
    valid: bool
    source: str


def clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, value))


def parse_model_output(
    text: str,
    max_linear_x: float = 0.2,
    max_angular_z: float = 0.6,
) -> ActionCommand:
    """Parse either a discrete action token or a small JSON velocity object."""
    raw = (text or "").strip()
    if not raw:
        return stop("empty")

    json_command = _parse_json_command(raw, max_linear_x, max_angular_z)
    if json_command is not None:
        return json_command

    normalized = re.sub(r"[^A-Za-z_]", " ", raw).upper()
    tokens = normalized.split()
    for token in tokens:
        if token in DISCRETE_ACTIONS:
            linear_x, angular_z = DISCRETE_ACTIONS[token]
            return ActionCommand(token, linear_x, angular_z, True, "discrete")

    return stop("invalid")


def stop(source: str = "stop") -> ActionCommand:
    return ActionCommand("STOP", 0.0, 0.0, False, source)


def _parse_json_command(
    raw: str,
    max_linear_x: float,
    max_angular_z: float,
) -> ActionCommand | None:
    try:
        payload: dict[str, Any] = json.loads(raw)
    except json.JSONDecodeError:
        return None

    if bool(payload.get("stop", False)) or payload.get("action") == "STOP":
        return ActionCommand("STOP", 0.0, 0.0, True, "json")

    try:
        linear_x = float(payload["linear_x"])
        angular_z = float(payload["angular_z"])
    except (KeyError, TypeError, ValueError):
        return stop("invalid_json")

    return ActionCommand(
        "CONTINUOUS",
        clamp(linear_x, -max_linear_x, max_linear_x),
        clamp(angular_z, -max_angular_z, max_angular_z),
        True,
        "json",
    )
