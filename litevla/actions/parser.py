"""Parse noisy VLA text into discrete action tokens."""

from __future__ import annotations

import re

from litevla.actions.schema import ACTION_NAMES, DiscreteAction, is_valid_action

_TRAILING_PUNCTUATION = re.compile(r"[^\w_]+$")
_ACTION_TOKEN_PATTERN = re.compile(
    r"\b(" + "|".join(re.escape(name) for name in ACTION_NAMES) + r")\b",
    re.IGNORECASE,
)


def normalize_action_text(text: str) -> str:
    """Strip outer whitespace and uppercase text for token comparison."""
    return text.strip().upper()


def _strip_trailing_punctuation(token: str) -> str:
    return _TRAILING_PUNCTUATION.sub("", token)


def parse_discrete_action(text: str) -> DiscreteAction | None:
    """Extract a discrete action from model text, or None when no valid token is found."""
    if not text or not text.strip():
        return None

    normalized = normalize_action_text(text)
    exact_candidate = _strip_trailing_punctuation(normalized)
    if is_valid_action(exact_candidate):
        return DiscreteAction(exact_candidate)

    match = _ACTION_TOKEN_PATTERN.search(text)
    if match is None:
        return None

    return DiscreteAction(match.group(1).upper())
