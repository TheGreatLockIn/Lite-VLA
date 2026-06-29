"""Tests for the discrete action parser."""

from __future__ import annotations

import pytest
from litevla.actions import (
    ACTION_NAMES,
    DiscreteAction,
    normalize_action_text,
    parse_discrete_action,
)


@pytest.mark.parametrize("token", ACTION_NAMES)
def test_parse_exact_valid_actions(token: str) -> None:
    assert parse_discrete_action(token) == DiscreteAction(token)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (" move_forward. ", DiscreteAction.MOVE_FORWARD),
        ("turn_left!", DiscreteAction.TURN_LEFT),
        ("  slow_down\n", DiscreteAction.SLOW_DOWN),
        ("(TURN_RIGHT)", DiscreteAction.TURN_RIGHT),
        ("Action: STOP", DiscreteAction.STOP),
        ("The robot should MOVE_FORWARD now.", DiscreteAction.MOVE_FORWARD),
    ],
)
def test_parse_normalized_and_noisy_outputs(
    raw: str,
    expected: DiscreteAction,
) -> None:
    assert parse_discrete_action(raw) == expected


@pytest.mark.parametrize(
    "raw",
    [
        "",
        "   ",
        "FORWARD",
        "GO",
        "I think we should keep going.",
        "move sideways",
    ],
)
def test_parse_invalid_outputs_return_none(raw: str) -> None:
    assert parse_discrete_action(raw) is None


def test_parse_returns_first_embedded_token() -> None:
    assert parse_discrete_action("MOVE_FORWARD then STOP") == DiscreteAction.MOVE_FORWARD


def test_normalize_action_text_strips_and_uppercases() -> None:
    assert normalize_action_text("  turn_left. ") == "TURN_LEFT."
