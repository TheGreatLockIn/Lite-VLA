# Discrete action parser

**Epic:** Action Interface, Parser, and Safety Layer (103) · **Jira:** Story 1019

**Human-readable version (browser):** [`discrete-action-parser.html`](discrete-action-parser.html)

## Executive summary

`litevla.actions.parser` extracts a **`DiscreteAction`** from noisy VLA model text before velocity mapping. It owns normalization (whitespace, case, trailing punctuation) and token discovery in longer strings. It does **not** map failures to `STOP` — Story 1021's safety gate handles that.

Subtasks covered: **10057** (parser function), **10058** (normalization), **10059** (unit tests).

## API contract and data flow

### Task-local flow

```text
VLA raw text
        │
        ├──> normalize_action_text (strip, uppercase)
        │
        ├──> exact token match (after trailing-punctuation trim)
        │         or regex search for ACTION_NAMES token
        │
        └──> DiscreteAction | None  ──> action_to_twist (1017) / safety gate (1021)
```

### Contract

| Surface | Rule |
|---------|------|
| **Input** | Raw model string (may include whitespace, punctuation, prose) |
| **Output** | `DiscreteAction` when a known token is found; `None` otherwise |
| **Vocabulary** | Exact tokens from Story 1017 — no aliases (`FORWARD`, `GO`) |
| **Multi-token text** | First embedded token wins (left-to-right search) |
| **Error behavior** | Returns `None` on empty, whitespace-only, or unrecognized text |

### Trade-offs

- **`None` vs raising** — `None` lets callers (especially the safety gate) decide fail-safe policy without catching exceptions in the hot path.
- **Exact match first, then regex** — clean outputs avoid regex work; embedded tokens still parse from conversational wrappers.
- **No alias table** — keeps parser aligned with `is_valid_action` and dataset labels; ambiguous shorthand stays invalid.
- **Deferred STOP** — parser reports failure; Story 1021 publishes zero velocity.

## Implementation breakdown

### Normalization (Subtask 10058)

**Snippet** (`litevla/actions/parser.py`):

```python
def normalize_action_text(text: str) -> str:
    return text.strip().upper()

def _strip_trailing_punctuation(token: str) -> str:
    return _TRAILING_PUNCTUATION.sub("", token)
```

**Design notes:** Outer whitespace and case are normalized before comparison. Trailing `.`, `!`, etc. are stripped from the whole-string candidate so `" move_forward. "` becomes `MOVE_FORWARD`.

**Risks and gotchas:** Leading punctuation on the full string is not stripped — regex search still finds embedded tokens. `normalize_action_text` is public for tests and debugging; production callers should use `parse_discrete_action`.

---

### Parser function (Subtask 10057)

**Snippet:**

```python
def parse_discrete_action(text: str) -> DiscreteAction | None:
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
```

**Design notes:** Two-phase parse — fast path for token-only outputs, regex with word boundaries for prose-wrapped tokens. Pattern is built from `ACTION_NAMES` so new enum members automatically join the parser vocabulary.

**Risks and gotchas:** Multiple tokens in one string return the **first** match only. Substring false positives are avoided via `\b` word boundaries (e.g. `FORWARD` alone stays invalid).

---

### Public API surface

**Snippet** (`litevla/actions/__init__.py`):

```python
from litevla.actions.parser import normalize_action_text, parse_discrete_action
```

**Design notes:** Import from `litevla.actions` alongside schema helpers so inference and ROS nodes have one package entry point.

---

## Engineering decisions

```text
ADR: Return None on parse failure
Status: Accepted
Context: MVP requires deterministic handling of malformed VLA text (RSK-02).
Decision: Parser returns None; Story 1021 maps None/invalid to STOP at publish time.
Alternatives Rejected: Raising ValueError (forces try/except at every call site); returning STOP directly (blurs parser vs safety boundaries).
Consequences: Callers must check for None before action_to_twist or delegate to safety gate.
```

## Verification patterns

| Contract defended | Where |
|-------------------|-------|
| All five tokens parse exactly | `test_parse_exact_valid_actions` |
| Whitespace, case, punctuation tolerated | `test_parse_normalized_and_noisy_outputs` |
| Aliases and prose without tokens → None | `test_parse_invalid_outputs_return_none` |
| First embedded token wins | `test_parse_returns_first_embedded_token` |
| Normalization helper behavior | `test_normalize_action_text_strips_and_uppercases` |

**Run:**

```bash
pytest tests/test_action_parser.py -q
```

## Open questions

- Should Story 1028 prefer last token when the model revises its answer mid-string?
- Should `parse_discrete_action` log parse failures for baseline evaluation (Story 1027)?

## Related docs

- Vocabulary contract: [`action-schema.md`](action-schema.md)
- Epic walkthrough: [`index.html`](index.html)
