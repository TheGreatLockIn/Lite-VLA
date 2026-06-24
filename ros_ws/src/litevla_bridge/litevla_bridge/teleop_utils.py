"""Keyboard key → discrete action mapping for teleop (VLA-28)."""

from __future__ import annotations

from litevla_bridge.action_schema import DiscreteAction

KEY_TO_ACTION: dict[str, str] = {
    "w": DiscreteAction.MOVE_FORWARD.value,
    "W": DiscreteAction.MOVE_FORWARD.value,
    "\x1b[A": DiscreteAction.MOVE_FORWARD.value,  # up arrow
    "a": DiscreteAction.TURN_LEFT.value,
    "A": DiscreteAction.TURN_LEFT.value,
    "\x1b[D": DiscreteAction.TURN_LEFT.value,  # left arrow
    "d": DiscreteAction.TURN_RIGHT.value,
    "D": DiscreteAction.TURN_RIGHT.value,
    "\x1b[C": DiscreteAction.TURN_RIGHT.value,  # right arrow
    "s": DiscreteAction.SLOW_DOWN.value,
    "S": DiscreteAction.SLOW_DOWN.value,
    "x": DiscreteAction.STOP.value,
    "X": DiscreteAction.STOP.value,
    " ": DiscreteAction.STOP.value,
    "\x03": DiscreteAction.STOP.value,  # Ctrl+C handled as stop before exit
}

TELEOP_HELP = """
Lite-VLA keyboard teleop
  w / ↑  MOVE_FORWARD
  a / ←  TURN_LEFT
  d / →  TURN_RIGHT
  s      SLOW_DOWN
  x/space STOP
  q      quit
"""


def key_to_action(key: str) -> str | None:
    if key == "q" or key == "Q":
        return None
    return KEY_TO_ACTION.get(key)
