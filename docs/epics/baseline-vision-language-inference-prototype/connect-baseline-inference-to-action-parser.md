# Connect baseline inference to action parser

**Epic:** Baseline Vision-Language Inference Prototype (104) · **Jira:** VLA-1028 / Story 1028

**Human-readable version (browser):** [`connect-baseline-inference-to-action-parser.html`](connect-baseline-inference-to-action-parser.html)

## Executive summary

`litevla.actions.InferenceAdapter` bridges Epic 104 (VLM text output) and Epic 103 (discrete parser + safety gate). It calls `InferenceWrapper.infer()`, passes the raw string through `safe_command_from_text()`, and returns bounded `(linear_x, angular_z)` velocities with parse status, observability logs, and preserved timing metadata.

Without this adapter, every script would re-wire "model string → parser → clamp" and drift on safety bounds. The evaluation runner and future ROS bridges should use one path so baseline metrics reflect the same safety behavior as deployment.

## Mental model

Think of this module as a **translator between probabilistic language and deterministic motion**.

It exists because VLMs output unconstrained text while the robot loop consumes clamped SI velocities and enumerated safety events.

The key engineering tension is **trust boundaries**: the wrapper optimistically returns model text; the adapter assumes text is hostile until parsed and clamped.

A beginner mistake is connecting wrapper output directly to `/cmd_vel` because the string sometimes looks like `MOVE_FORWARD`.

A senior engineer watches for **double STOP paths** (wrapper error vs parse failure), **config safety limits**, and **logs that pair raw vs parsed tokens**.

## Backstory: why this exists

Before this adapter, `evaluate_baseline.py` compared raw model strings to labels — useful for syntax metrics but disconnected from the safety layer teammates already built in Epic 103.

The naive solution is calling `parse_action` inline in the eval script.

That breaks because ROS nodes, notebooks, and CI would each duplicate parser imports, max velocity reads, and logging format — and a parser fix might ship to tests but not evaluation.

So this design chooses **`InferenceAdapter.adapt_inference()`** as the single integration point wrapping `safe_command_from_text()`.

This pattern appears in real systems as an **anti-corruption layer** between ML output and actuation APIs.

## Prerequisites

- Epic 103 [`action-schema.md`](../action-interface-parser-and-safety-layer/action-schema.md) — tokens and nominal velocities.
- Epic 103 discrete parser and `safe_command_from_text` (safety gate).
- [`inference-wrapper.md`](inference-wrapper.md) — `infer()` return shape.

## Concept primer / vocabulary

| Term | Meaning in this project |
|------|-------------------------|
| Raw VLM output | Unparsed string from `InferenceWrapper` — may include noise, case drift, or prose. |
| `SafeCommand` | Dataclass from safety gate: action enum, clamped velocities, audit `events`. |
| `parse_status` | First event kind string (e.g. `ok`, `parse_failure`) for metrics and logs. |
| `max_linear_vel` / `max_angular_vel` | Config safety ceilings (m/s, rad/s) applied after nominal mapping. |
| Contract | Adapter promises: image + instruction → dict with `safe_command`, parse metadata, timings; parse failures → STOP velocities, not exceptions. |

## Guided code reading

Read these in order:

1. `litevla/actions/adapter.py` — entire file is short; note config read in `__init__`.
2. `litevla/actions/safety.py` — what `safe_command_from_text` does on garbage input.
3. `scripts/evaluate_baseline.py` — adapter replaces direct wrapper calls for predicted labels.
4. `tests/test_inference_adapter.py` — valid, noisy, invalid, and exception paths.

While reading, ask:
- Does adapter re-raise wrapper failures?
- Where are velocity limits sourced?
- What gets logged for operators?

## File and artifact index

| File or artifact | What it is | Why it matters | First thing to inspect |
|------------------|------------|----------------|------------------------|
| `litevla/actions/adapter.py` | Adapter class | Epic 104 ↔ 103 bridge | `adapt_inference` |
| `litevla/actions/__init__.py` | Public exports | `InferenceAdapter` import path | Re-exports |
| `litevla/actions/safety.py` | Safety gate | Parses text + clamps velocities | `safe_command_from_text` |
| `scripts/evaluate_baseline.py` | Baseline benchmark | Uses adapter in eval loop | `adapter.adapt_inference` call |
| `tests/test_inference_adapter.py` | Integration tests | End-to-end text → SafeCommand | Fallback tests |

## API contract and data flow

### Task-local flow

```text
BGR image + instruction
        │
        ├──> InferenceWrapper.infer() ──> raw_text, timing, success, error
        │
        ├──> safe_command_from_text(raw_text, max_linear_vel, max_angular_vel)
        │         ├──> parser (normalize token)
        │         ├──> action_to_twist (nominal velocities)
        │         └──> clamp per config
        │
        └──> dict: safe_command, action, parse_status, raw_output, timing, ...
```

### Contract

| Surface | Rule |
|---------|------|
| **Input** | Same as wrapper: BGR image, instruction, optional `few_shot` |
| **Config** | Reads `safety.max_linear_vel`, `safety.max_angular_vel` (defaults 0.5, 1.0) |
| **Output** | `safe_command` (`SafeCommand`), string `action`, `parse_status`, `raw_output`, `success`, `timing`, `error` |
| **Invariant** | Parser failure yields `STOP` with zero velocities — never uncaught `ValueError` to caller |
| **Observability** | INFO log line with `raw_output` and `parsed_action` |

## Naive approach vs chosen approach

| Approach | Why it seems attractive | Why we did or did not choose it |
|----------|-------------------------|---------------------------------|
| Eval compares raw strings only | Simpler metrics | Hides safety-layer behavior users will ship |
| Parser inside ROS node | One less class | Duplicates bounds and logging across entrypoints |
| Wrapper returns SafeCommand | Single call site | Couples Hugging Face code to ROS safety types |
| Dedicated InferenceAdapter | Extra indirection | One tested integration; eval matches runtime |
| Re-raise on wrapper error | Surfaces ML failures | Caller might skip STOP; adapter preserves safe_cmd |

## Implementation breakdown

### Construction and safety bounds

**Snippet** (`litevla/actions/adapter.py`):

```python
class InferenceAdapter:
    def __init__(self, wrapper: InferenceWrapper, config: dict):
        self.wrapper = wrapper
        self.config = config
        safety_cfg = config.get("safety", {})
        self.max_linear_vel = safety_cfg.get("max_linear_vel", 0.5)
        self.max_angular_vel = safety_cfg.get("max_angular_vel", 1.0)
```

**What to notice:** Adapter does not own the wrapper lifecycle — inject for tests with mocks.

**Why it is written this way:** Dependency injection keeps unit tests fast (mock wrapper, real parser).

**Risks and gotchas:** Defaults 0.5 / 1.0 differ from MVP nominal 0.2 m/s forward — clamp still applies via gate.

---

### adapt_inference orchestration

**Snippet:**

```python
infer_res = self.wrapper.infer(image, instruction, few_shot=few_shot)
raw_text = infer_res["action"]

safe_cmd = safe_command_from_text(
    raw_text,
    max_linear_vel=self.max_linear_vel,
    max_angular_vel=self.max_angular_vel,
    logger=logger,
)

logger.info(
    f"Adapter run: raw_output='{raw_text}', "
    f"parsed_action='{safe_cmd.action.value}'"
)

return {
    "safe_command": safe_cmd,
    "action": safe_cmd.action.value,
    "parse_status": safe_cmd.events[0].kind.value,
    "raw_output": raw_text,
    "success": infer_res["success"],
    "timing": infer_res["timing"],
    "error": infer_res["error"],
}
```

**What to notice:** `success` reflects inference, not parse quality — semantic wrong token can still be `success=True`.

**Why it is written this way:** Separates ML operational status from navigation correctness.

**Risks and gotchas:** Callers must not use `success` alone as "good driving"; check `parse_status` and label match.

---

### Evaluation integration

**Snippet** (`scripts/evaluate_baseline.py`):

```python
wrapper = InferenceWrapper(config)
adapter = InferenceAdapter(wrapper, config)
# ...
res = adapter.adapt_inference(image, instruction, few_shot=few_shot)
predicted = res["action"]
```

**What to notice:** Metrics compare parsed `action` strings to `expected_action` in metadata.

**Why it is written this way:** Benchmark numbers include parser normalization (case, whitespace).

**Risks and gotchas:** Changing parser rules retroactively changes baseline metrics — document parser version in results if needed.

## Engineering decisions

```text
ADR: Model-to-action adapter wrapper
Status: Accepted
Context: VLM text must pass through Epic 103 safety pipeline before actuation.
Decision: InferenceAdapter delegates parsing/clamping to safe_command_from_text.
Alternatives Rejected: Inline parsing in eval/ROS scripts.
Consequences: All new entrypoints should use adapter; raw wrapper reserved for prompt tuning.
```

## Verification patterns

| Contract defended | Where |
|-------------------|-------|
| Valid token → correct enum + velocities | `test_adapter_valid_prediction` |
| Noisy text normalized (`turn_left. `) | `test_adapter_noisy_text` |
| Invalid token → STOP + parse_failure | `test_adapter_invalid_token_fallback` |
| Wrapper exception still returns SafeCommand | `test_adapter_wrapper_error_safe_stop` |
| Log contains raw and parsed fields | `test_adapter_logs_raw_and_parsed` |

**Run:**

```bash
pytest tests/test_inference_adapter.py -v
pytest
python scripts/evaluate_baseline.py
```

### Failure modes and debugging path

| Symptom | Likely cause | How to investigate | Fix |
|---------|--------------|--------------------|-----|
| `parse_status=parse_failure` always | Model emits prose not tokens | Read adapter logs `raw_output` | Tune prompts; few-shot; fine-tune later |
| `success=False` but robot moves | Downstream ignores `safe_command` | Trace who publishes `/cmd_vel` | Use `safe_command` velocities, not raw text |
| Correct token, zero velocity | STOP fallback from wrapper error | Check `error` field | Fix OOM/path; see inference doc |
| Eval accuracy jumped without model change | Parser normalization changed | Diff `test_inference_adapter` | Re-baseline results.json |
| Velocities at config ceiling always | Limits lower than nominal table | Compare `safety` config to ACTION_VELOCITIES | Adjust config for test intent |

## Engineering principle taught by this task

This task teaches **layered trust**: ML proposes language; deterministic code disposes motion. Never let probabilistic output cross a safety boundary without a named, tested gate.

## Active learning checks

1. Why does `success` stay True when the model picks the wrong direction?
2. Who owns STOP when the wrapper crashes vs when parsing fails?
3. Why log both `raw_output` and `parsed_action`?
4. Should eval report syntax on raw or parsed strings — and why?

## Small modification exercise

Lower `safety.max_linear_vel` to `0.1` in local config, run `pytest tests/test_inference_adapter.py`, then `adapt_inference` with a mocked `MOVE_FORWARD` response. Confirm `safe_command.linear_x` clamps to `0.1` while `action` remains `MOVE_FORWARD`.

## Open questions

- Should eval JSON store both `raw_output` and `parse_status` per row for richer failure analysis?
- When ROS bridge lands, does it import adapter or duplicate safety gate?
- Should adapter downgrade `success` when `parse_status` is not `ok`?

## Related docs

- Inference: [`inference-wrapper.md`](inference-wrapper.md)
- Schema: [`../action-interface-parser-and-safety-layer/action-schema.md`](../action-interface-parser-and-safety-layer/action-schema.md)
- Metrics: [`zero-shot-evaluation.md`](zero-shot-evaluation.md)
