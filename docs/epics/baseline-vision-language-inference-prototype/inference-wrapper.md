# Baseline inference wrapper

**Epic:** Baseline Vision-Language Inference Prototype (104) · **Jira:** VLA-38 / Story 1026

**Human-readable version (browser):** [`inference-wrapper.html`](inference-wrapper.html)

## Executive summary

`litevla.inference.InferenceWrapper` is the **callable VLA boundary** for baseline navigation. It loads SmolVLM-256M-Instruct (or runs in `dummy` mode without weights), chains preprocessing and prompting, runs greedy text generation, and returns a structured dict with predicted text, per-stage timings, and success/error flags.

ROS nodes, evaluation scripts, and the action adapter depend on this wrapper so they never touch Hugging Face `generate()` details, device dtype selection, or few-shot image stacking. The wrapper deliberately returns **raw text**, not safe velocities — Epic 103 parsing happens in `InferenceAdapter`.

## Mental model

Think of this module as a **black-box "what should we do?" API** for vision + language.

It exists because model loading, tokenization, and multimodal tensor placement are fragile, slow, and hardware-specific — robot code should call `infer(image, instruction)` not `model.generate`.

The key engineering tension is **determinism vs capability**: greedy decoding (`do_sample=False`) stabilizes tests and control; sampling might explore better actions but breaks reproducibility.

A beginner mistake is treating the returned string as a validated robot command — it is model text until the parser runs.

A senior engineer watches for **device/dtype mismatches**, **few-shot image order**, **exception → STOP fallback**, and **mock tensor handling in tests**.

## Backstory: why this exists

Before the wrapper, every script would duplicate model init, PIL conversion, and timing boilerplate. Tests could not swap in `dummy` mode without editing import paths.

The naive solution is calling `AutoModelForImageTextToText` directly inside a ROS node.

That breaks because CUDA OOM, missing weights, and tokenizer API changes would crash the control loop; there is no single place to log latencies or return `STOP` on failure.

So this design chooses one **`InferenceWrapper`** with `runtime.mode` switching (`dummy` vs `model`), centralized exception handling, and timing instrumentation.

This pattern appears in real systems as an **inference service facade** — same role as a gRPC model server, but in-process for the MVP.

## Prerequisites

- [`image-preprocessing-pipeline.md`](image-preprocessing-pipeline.md) — BGR in, PIL-bound bytes/array out.
- [`prompting-strategy.md`](prompting-strategy.md) — LLaVA strings and few-shot paths.
- PyTorch device basics: CUDA prefers `bfloat16`; CPU/MPS use `float32`.

## Concept primer / vocabulary

| Term | Meaning in this project |
|------|-------------------------|
| SmolVLM-256M-Instruct | Starter VLM; SigLIP vision + SmolLM2 language (~256M params). |
| `runtime.mode` | `dummy` — scripted actions, no weights; `model` — loads Hugging Face checkpoint. |
| Greedy decoding | `do_sample=False` — always pick highest-probability next token; deterministic. |
| `AutoProcessor` | Hugging Face helper that tokenizes text and prepares image tensors together. |
| `timing` dict | `preprocessing_ms`, `prompting_ms`, `inference_ms`, `total_ms` — baseline latency evidence. |
| Contract | `infer()` returns `action` (str), `timing`, `success`, `error` — never raises on model failure. |

## Guided code reading

Read these in order:

1. `litevla/inference.py` — `__init__` (mode branch, device/dtype), then `infer()` pipeline stages.
2. `tests/test_inference.py` — dummy path, mocked `model` path, exception → STOP.
3. `litevla/actions/adapter.py` — consumer that parses wrapper text (next epic task).

While reading, ask:
- What happens in `dummy` mode vs `model` mode?
- Where is greedy decoding enforced?
- Who converts preprocessing output to PIL?

## File and artifact index

| File or artifact | What it is | Why it matters | First thing to inspect |
|------------------|------------|----------------|------------------------|
| `litevla/inference.py` | Wrapper implementation | Model load + `infer()` | Exception handler at end of `infer` |
| `configs/default.example.yaml` | Config | `runtime.mode`, `model.path`, `prompt_version` | `runtime` and `model` sections |
| `tests/test_inference.py` | Unit tests | Dummy + mock model contracts | `test_infer_catches_exception_returns_stop` |
| `data/examples/*.png` | Few-shot frames | Loaded when `few_shot=True` | Used with `format_few_shot_prompt` |

## API contract and data flow

### Task-local flow

```text
BGR ndarray + instruction + few_shot flag
        │
        ├──> ImagePreprocessor ──> PIL query image
        ├──> PromptFormatter ──> prompt string (+ ref images if few_shot)
        ├──> AutoProcessor(text, images) ──> tensors on device
        ├──> model.generate(do_sample=False) ──> token ids
        └──> batch_decode ──> action str + timing dict
```

### Contract

| Surface | Rule |
|---------|------|
| **Input** | `image`: BGR `(H,W,3)` ndarray; `instruction`: str; `few_shot`: bool |
| **Output** | `dict` with `action` (str), `timing` (four ms fields), `success` (bool), `error` (str or None) |
| **Success path** | `success=True`, `error=None`, `action` is raw decoded text (may be invalid token) |
| **Failure path** | Any exception → `success=False`, `action="STOP"`, `error` message logged |
| **Invariant** | `dummy` mode never loads weights; `model` mode requires non-empty `model.path` |

## Naive approach vs chosen approach

| Approach | Why it seems attractive | Why we did or did not choose it |
|----------|-------------------------|---------------------------------|
| Model calls inside ROS node | Fewer layers | Crashes take down control; hard to test |
| Sampling (`do_sample=True`) | More diverse actions | Non-deterministic; bad for tests and safety replay |
| Parse actions inside wrapper | One-stop shop | Mixes ML and Epic 103 safety concerns |
| Wrapper returns text + timings; adapter parses | More files | Clear boundary: inference vs safety |
| Raise on CUDA OOM | Explicit errors | Would skip STOP fallback; robot keeps last velocity |

## Implementation breakdown

### Device and dtype selection

**Snippet** (`litevla/inference.py`):

```python
if device_name == "cuda" and torch.cuda.is_available():
    self.device = torch.device("cuda")
    self.torch_dtype = torch.bfloat16
elif device_name == "mps" and torch.backends.mps.is_available():
    self.device = torch.device("mps")
    self.torch_dtype = torch.float32
else:
    self.device = torch.device("cpu")
    self.torch_dtype = torch.float32
```

**What to notice:** CPU never uses `bfloat16` — avoids slow emulation. MPS stays `float32` for compatibility.

**Why it is written this way:** Match hardware capabilities at load time, not per inference call.

**Risks and gotchas:** Config may say `cuda` but hardware absent — silently falls back to CPU. Log lines are the operator's clue.

---

### Few-shot image stacking

**Snippet:**

```python
if few_shot:
    prompt_str, image_paths = self.prompt_formatter.format_few_shot_prompt(instruction)
    images_list = []
    for path in image_paths:
        ref_bgr = cv2.imread(path)
        # preprocess each ref → PIL
        images_list.append(ref_pil)
    images_list.append(query_pil)
else:
    prompt_str = self.prompt_formatter.format_prompt(instruction)
    images_list = query_pil
```

**What to notice:** Reference frames use the same `ImagePreprocessor` as the live frame. Query image is always last.

**Why it is written this way:** Visual consistency across demo and live embeddings.

**Risks and gotchas:** Missing path raises inside `infer` → STOP fallback, not at import time.

---

### Greedy generation and decode

**Snippet:**

```python
generated_ids = self.model.generate(
    **inputs,
    max_new_tokens=max_new_tokens,
    do_sample=False,
)
input_len = inputs["input_ids"].shape[1]
action = self.processor.batch_decode(
    generated_ids[:, input_len:],
    skip_special_tokens=True,
)[0].strip()
```

**What to notice:** Only *new* tokens are decoded — prompt echo is stripped. `max_new_tokens` from config (default 32).

**Why it is written this way:** Greedy decoding gives repeatable baseline metrics and simpler debugging.

**Risks and gotchas:** Model may still emit extra words within `max_new_tokens`; parser must normalize.

---

### Exception-safe STOP fallback

**Snippet:**

```python
except Exception as exc:
    logger.error(f"Inference failed with error: {exc}\n{traceback.format_exc()}")
    return {
        "action": "STOP",
        "success": False,
        "error": str(exc),
        "timing": { ... },
    }
```

**What to notice:** Never re-raises — control loop gets a dict it can branch on.

**Why it is written this way:** Fail-safe motion intent when ML stack breaks; adapter/safety gate still clamp.

**Risks and gotchas:** `"STOP"` string is not yet a `SafeCommand` until adapter runs.

## Engineering decisions

```text
ADR: AutoModelForImageTextToText
Status: Accepted
Context: Local transformers build exposes ImageTextToText for Idefics3/SmolVLM, not Vision2Seq.
Decision: Load via AutoModelForImageTextToText + AutoProcessor.
Alternatives Rejected: Custom GGUF path in wrapper (deferred); Vision2Seq (unavailable).
Consequences: Tied to Hugging Face inference path for baseline epic.
```

```text
ADR: Safety recovery at wrapper boundary
Status: Accepted
Context: Uncaught ML exceptions would stall robot loop with stale velocity.
Decision: Catch all exceptions; return action STOP and success False.
Alternatives Rejected: Propagate exception to ROS node (too brittle).
Consequences: Adapter must treat STOP from error same as STOP from valid token.
```

## Verification patterns

| Contract defended | Where |
|-------------------|-------|
| Dummy mode returns timing + action | `test_infer_dummy_mode` |
| Few-shot loads real example files | `test_infer_few_shot_dummy` |
| Empty model path fails at init | `test_init_model_mode_missing_path` |
| Mocked generate uses greedy args | `test_infer_model_mode_mocked` |
| Exception → STOP, success False | `test_infer_catches_exception_returns_stop` |

**Run:**

```bash
pytest tests/test_inference.py -v
```

### Failure modes and debugging path

| Symptom | Likely cause | How to investigate | Fix |
|---------|--------------|--------------------|-----|
| `success=False`, `error` mentions path | Missing model weights or few-shot image | Read `error` string; check `model.path` | Download weights or restore `data/examples` |
| Very slow on CPU | Full 256M forward on CPU | Check `timing.inference_ms` | Use `runtime.mode: dummy` for dev; enable CUDA |
| CUDA OOM | Batch too large / few-shot images | Reduce images; monitor `nvidia-smi` | Disable few-shot; smaller resize |
| Action is prompt echo | Decode slice wrong | Log `generated_ids` length vs `input_len` | Fix decode slice (regression test) |
| Mock tests pass, real model gibberish | Prompting issue not wrapper | Run eval script | See prompting + zero-shot docs |

## Engineering principle taught by this task

This task teaches **facade + fail-safe defaults** for ML in real-time loops: isolate framework details, measure stages, and never let an uncaught tensor exception be the last message your robot receives.

## Active learning checks

1. Why does `infer()` return text instead of `DiscreteAction`?
2. What changes in the tensor pipeline when `few_shot=True`?
3. Why is `do_sample=False` important for baseline benchmarking?
4. Where should velocity clamping happen — here or in the adapter?

## Small modification exercise

Set `model.max_tokens` to `8` in local config, run `pytest tests/test_inference.py`, then one dummy `infer()` call. Confirm generation still returns an action string and `timing.inference_ms` is populated. In `model` mode (if available), verify shorter outputs may truncate conversational hallucinations but can also clip valid tokens.

## Open questions

- Should wrapper strip or regex-extract the first allowed token before returning?
- Is JPEG preprocess + PIL round-trip still necessary for pure Hugging Face path?
- When do we split wrapper into load vs infer for faster ROS spin loops?

## Related docs

- Preprocessing: [`image-preprocessing-pipeline.md`](image-preprocessing-pipeline.md)
- Parser bridge: [`connect-baseline-inference-to-action-parser.md`](connect-baseline-inference-to-action-parser.md)
- Metrics: [`zero-shot-evaluation.md`](zero-shot-evaluation.md)
