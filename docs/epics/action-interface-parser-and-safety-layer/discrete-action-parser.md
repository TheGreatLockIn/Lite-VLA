# Discrete action parser

**Epic:** Action Interface, Parser, and Safety Layer (103) · **Jira:** Story 1019

**Human-readable version (browser):** [`discrete-action-parser.html`](discrete-action-parser.html)

## Executive summary

`litevla.actions.parser` extracts a **`DiscreteAction`** from noisy VLA model text before velocity mapping. It owns normalization (whitespace, case, trailing punctuation) and token discovery in longer strings. It does **not** map failures to `STOP` — [`safety-clamp-and-fallback.md`](safety-clamp-and-fallback.md) handles that at the publish boundary.

Subtasks covered: **10057** (parser function), **10058** (normalization), **10059** (unit tests).

## Mental model

Think of this module as a **customs inspector** at the border between free-form language model output and the rigid five-token contract.

It exists because VLMs rarely emit perfectly formatted `MOVE_FORWARD` — they add whitespace, lowercase, trailing periods, or wrap tokens in conversational prose. Something must translate that noise into a known `DiscreteAction` or honestly report “no valid token found.”

The key engineering tension is **tolerance for benign formatting vs. rejection of ambiguous shorthand** — the parser should accept `" move_forward. "` but must not invent aliases like `FORWARD` that would desync training labels.

A beginner mistake is returning `STOP` directly from the parser on failure — that blurs “could not parse” with “explicit stop command” and hides parse-failure metrics from the safety gate.

A senior engineer watches for **regex drift**: `_ACTION_TOKEN_PATTERN` is built from `ACTION_NAMES`, so new enum members auto-join the parser, but multi-token strings still return only the first match.

## Backstory: why this exists

Before this module existed, callers would either require exact model outputs (brittle in practice) or hand-roll string cleaning in every ROS node and test script.

The naive solution would be a large alias table (`FORWARD` → `MOVE_FORWARD`, `GO` → `MOVE_FORWARD`) or fuzzy matching against token substrings.

That breaks because aliases create a second vocabulary that datasets and `is_valid_action` do not recognize. Fuzzy matching turns `FORWARD` into a false positive and makes evaluation non-deterministic.

So this design chooses **normalize → exact match → bounded regex search** with vocabulary driven entirely by Story 1017’s `ACTION_NAMES`, returning `None` on failure so the safety gate owns fail-safe policy.

This pattern appears in real systems as **structured extraction from LLM output** — log parsers, intent classifiers, and command DSL extractors all separate “parse” from “act.”

## Prerequisites

Before reading this module, you should understand:

- **Discrete action vocabulary** — [`action-schema.md`](action-schema.md) defines the five tokens and `is_valid_action`.
- **Python `re` basics** — word-boundary regex finds embedded tokens without matching substrings inside other words.
- **Optional vs. exception** — parser returns `None` instead of raising; understand why before reading the safety gate.
- **Downstream fail-safe** — [`safety-clamp-and-fallback.md`](safety-clamp-and-fallback.md) converts `None` to zero-velocity `STOP`.

## Concept primer / vocabulary

| Term | Meaning in this project |
|------|-------------------------|
| `parse_discrete_action` | Main entry: raw VLA string → `DiscreteAction` or `None`. |
| `normalize_action_text` | Strip outer whitespace and uppercase; public for tests/debug. |
| `_strip_trailing_punctuation` | Remove trailing `.`, `!`, etc. from whole-string candidate. |
| `_ACTION_TOKEN_PATTERN` | Regex with `\b` word boundaries built from `ACTION_NAMES`. |
| `None` return | Parse failure signal — not an error exception; safety gate interprets it. |
| First embedded token | In multi-token strings, left-to-right regex search wins. |
| VLA text | Raw string from vision-language model inference (may include prose). |

## Guided code reading

Read these in order:

1. **`litevla/actions/schema.py`** (briefly)
   - Confirm `ACTION_NAMES` and `is_valid_action` — parser imports these, never duplicates the list.

2. **`litevla/actions/parser.py`**
   - Read `normalize_action_text` and `_strip_trailing_punctuation`.
   - Then `parse_discrete_action` two-phase logic: exact path, then regex.
   - Inspect how `_ACTION_TOKEN_PATTERN` is constructed at module load.

3. **`tests/test_action_parser.py`**
   - Parametrized cases show accepted noise and rejected aliases.

While reading, ask:

- Where does data enter? — Raw `text: str` at `parse_discrete_action`.
- Where is it validated? — `is_valid_action` on exact candidate; regex match must be a known token name.
- Where can it fail? — Returns `None` for empty, whitespace-only, or unrecognized text.
- Who owns the final side effect? — Not this module; safety gate converts `None` to `STOP`.

## File and artifact index

| File or artifact | What it is | Why it matters | First thing to inspect |
|------------------|------------|----------------|------------------------|
| `litevla/actions/parser.py` | VLA text → `DiscreteAction` extraction | Only module that understands noisy model output | `parse_discrete_action` |
| `litevla/actions/schema.py` | Vocabulary source | Parser regex is derived from `ACTION_NAMES` | `ACTION_NAMES` tuple |
| `tests/test_action_parser.py` | Parser contract tests | Shows exact vs. embedded vs. invalid cases | `test_parse_invalid_outputs_return_none` |
| `litevla/actions/safety.py` | Downstream consumer | Calls `parse_discrete_action` in `safe_command_from_text` | Parse-failure branch |

## API contract and data flow

### What “contract” means here

For this module, **contract** means: given any string (including empty or prose-wrapped), the parser either returns a valid `DiscreteAction` from the Story 1017 vocabulary or returns `None`. It never raises, never clamps velocities, and never publishes `STOP` — it only reports whether a known token was found.

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

### Contract table

| Surface | Rule |
|---------|------|
| **Input** | Raw model string (may include whitespace, punctuation, prose) |
| **Output** | `DiscreteAction` when a known token is found; `None` otherwise |
| **Vocabulary** | Exact tokens from Story 1017 — no aliases (`FORWARD`, `GO`) |
| **Multi-token text** | First embedded token wins (left-to-right search) |
| **Error behavior** | Returns `None` on empty, whitespace-only, or unrecognized text |

### Naive approach vs chosen approach

| Approach | Why it seems attractive | Why we did or did not choose it |
|----------|-------------------------|---------------------------------|
| Alias table (`FORWARD` → `MOVE_FORWARD`) | Handles common model mistakes | Second vocabulary; breaks dataset strictness |
| Raise `ValueError` on failure | Forces explicit handling | Clutters hot path with try/except in ROS nodes |
| Return `STOP` from parser | Simple “always get an action” | Blurs parse failure with explicit stop intent |
| Fuzzy / substring match | Catches more outputs | `FORWARD` false positives; non-deterministic eval |
| **`None` + two-phase parse** | Slightly more caller logic | Clean boundary: parser reports, safety gate acts |
| Regex from `ACTION_NAMES` | Rebuild pattern on enum change | Auto-syncs vocabulary; first-match semantics stay documented |

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

**What to notice:** Outer whitespace and case are normalized before comparison. Trailing `.`, `!`, etc. are stripped from the whole-string candidate.

**Why it is written this way:** `" move_forward. "` becomes `MOVE_FORWARD` on the fast exact path without regex.

**Risks and gotchas:** Leading punctuation on the full string is not stripped — regex search still finds embedded tokens. `normalize_action_text` is public for tests; production callers should use `parse_discrete_action`.

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

**What to notice:** Regex runs on **original** `text` (case-insensitive pattern), not only normalized form — embedded tokens in mixed-case prose still match.

**Why it is written this way:** Two-phase parse — fast path for token-only outputs, regex with word boundaries for prose-wrapped tokens. Pattern is built from `ACTION_NAMES` so new enum members automatically join the parser vocabulary.

**Risks and gotchas:** Multiple tokens in one string return the **first** match only. Substring false positives are avoided via `\b` word boundaries (e.g. `FORWARD` alone stays invalid).

---

### Public API surface

**Snippet** (`litevla/actions/__init__.py`):

```python
from litevla.actions.parser import normalize_action_text, parse_discrete_action
```

**What to notice:** Parser exports sit alongside schema and safety symbols at package level.

**Why it is written this way:** Inference and ROS nodes import one package entry point.

**Risks and gotchas:** Direct `action_to_twist` on raw model text bypasses this module — always route through safety gate in production.

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

## Failure modes and debugging path

| Symptom | Likely cause | How to investigate | Fix |
|---------|--------------|--------------------|-----|
| Valid-looking output returns `None` | Alias (`FORWARD`) or typo | Print raw model string; test `parse_discrete_action` in REPL | Fix prompt to emit exact tokens; do not add aliases here |
| Wrong action from prose | Multiple tokens; first match wins | Inspect full model string for earlier token | Adjust prompt; consider last-token policy (open question) |
| `MOVE_FORWARD.` fails exact path | Leading punctuation not stripped | Test `_strip_trailing_punctuation` vs. regex path | Usually regex still finds token; check edge case |
| Parser OK but robot stops | Downstream safety gate, not parser | Trace `safe_command_from_text` | See [`safety-clamp-and-fallback.md`](safety-clamp-and-fallback.md) |
| New enum token not parsed | Forgot parser uses `ACTION_NAMES` at import | Restart process after enum change; verify pattern | Add enum member in schema only — pattern rebuilds automatically |

## Engineering principle taught by this task

This task teaches **parse vs. act separation**: extraction modules report structured facts (`DiscreteAction` or `None`); policy modules (safety gate) decide what the robot does with that report. Keeping parsing pure makes tests deterministic and concentrates fail-safe behavior in one place.

## Active learning checks

Before modifying this module, answer:

1. Why does the parser return `None` instead of raising or returning `STOP`?
2. Why does regex search use the original `text` rather than only the normalized string?
3. What happens when the model outputs `"TURN_LEFT then MOVE_FORWARD"`?
4. How would you test that `FORWARD` alone is rejected without breaking `MOVE_FORWARD`?

## Small modification exercise

Add a unit test case to `tests/test_action_parser.py` for the input `"Okay, I will MOVE_FORWARD now."` and verify `parse_discrete_action` returns `DiscreteAction.MOVE_FORWARD`. Run `pytest tests/test_action_parser.py -q` to confirm the embedded-token regex path works as documented.

## Open questions

- Should Story 1028 prefer last token when the model revises its answer mid-string?
- Should `parse_discrete_action` log parse failures for baseline evaluation (Story 1027)?

## Related docs

- Vocabulary contract: [`action-schema.md`](action-schema.md)
- Safety gate (downstream): [`safety-clamp-and-fallback.md`](safety-clamp-and-fallback.md)
- Epic walkthrough: [`index.html`](index.html)
