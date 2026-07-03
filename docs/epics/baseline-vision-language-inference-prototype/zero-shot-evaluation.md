# Zero-shot baseline evaluation

**Epic:** Baseline Vision-Language Inference Prototype (104) · **Jira:** VLA-161 / Story 1027 (Subtask VLA-10083)

**Human-readable version (browser):** [`zero-shot-evaluation.html`](zero-shot-evaluation.html)

## Executive summary

The zero-shot evaluation pipeline measures how well **unfine-tuned** SmolVLM-256M-Instruct follows discrete prompting constraints on a fixed 20-image test set before dataset collection or LoRA training. `scripts/generate_test_set.py` builds augmented frames; `scripts/evaluate_baseline.py` runs `InferenceAdapter` over `data/evaluation/metadata.json` and writes `results.json` with syntax accuracy, semantic accuracy, and latency splits.

This establishes the **baseline yardstick**: if fine-tuning or prompt changes cannot beat these numbers, they are not ready for robot integration. Metrics deliberately separate "valid token shape" from "correct steering decision."

## Mental model

Think of this module as a **regression exam for the VLA stack**, not a proof the robot is safe.

It exists because subjective "the model seems fine" demos hide syntax hallucinations, spatial errors, and latency spikes that only appear across many frames.

The key engineering tension is **coverage vs cost**: 20 augmented images are cheap but not representative of full arena diversity; they are enough to compare prompt versions and code changes.

A beginner mistake is celebrating 100% valid-action rate while semantic accuracy is near chance — syntax is necessary, not sufficient.

A senior engineer watches for **dummy vs model mode**, **whether metrics use parsed or raw strings**, and **failure category trends** (syntax vs semantics vs depth).

## Backstory: why this exists

Before structured eval, teammates ran one-off screenshots through notebooks. Results were not reproducible, not logged, and not comparable across prompt versions.

The naive solution is manually clicking through four seed images in a GUI.

That breaks because augmentations (blur, noise, glare) expose fragility real arenas produce; manual runs skip timing instrumentation and JSON artifacts future epics need.

So this design chooses a **generated metadata-driven loop** with explicit metrics definitions and saved `results.json`.

This pattern appears in real systems as **golden-set regression** for ML services — small, fast, committed to the repo.

## Prerequisites

- [`inference-wrapper.md`](inference-wrapper.md) — timing fields and `runtime.mode`.
- [`connect-baseline-inference-to-action-parser.md`](connect-baseline-inference-to-action-parser.md) — adapter output shape used in eval loop.
- [`prompting-strategy.md`](prompting-strategy.md) — zero-shot vs few-shot flag.

## Concept primer / vocabulary

| Term | Meaning in this project |
|------|-------------------------|
| Zero-shot | No few-shot reference images; only live frame + prompt template. |
| Valid action rate | Syntax accuracy — output maps to one of five allowed tokens after normalization. |
| Correct action rate | Semantic accuracy — predicted action equals `expected_action` in metadata. |
| Augmentation | Programmatic image transform (brightness, blur, noise) from four seed PNGs. |
| `metadata.json` | Eval dataset index: paths, instructions, expected labels, variation type. |
| `results.json` | Benchmark output: per-run rows + aggregate stats and average latencies. |
| Contract | Eval script promises: given metadata file, produce comparable metrics dict and exit code 0/1 on config or IO errors. |

## Guided code reading

Read these in order:

1. `scripts/generate_test_set.py` — how 4 seeds become 20 records.
2. `data/evaluation/metadata.json` — one record's fields.
3. `scripts/evaluate_baseline.py` — loop, metric counters, JSON write.
4. `tests/test_evaluation_runner.py` — dummy mode expected accuracies.

While reading, ask:
- Where is ground truth stored?
- Does the loop use wrapper or adapter?
- How are latencies aggregated?

## File and artifact index

| File or artifact | What it is | Why it matters | First thing to inspect |
|------------------|------------|----------------|------------------------|
| `scripts/generate_test_set.py` | Dataset builder | Creates 20 images + metadata | Augmentation functions |
| `data/evaluation/metadata.json` | Eval index | Ground truth labels | `expected_action` per row |
| `data/evaluation/images/` | Augmented frames | Input images for eval | Filename vs `variation_type` |
| `scripts/evaluate_baseline.py` | Benchmark runner | Computes metrics + latencies | Metric accumulation loop |
| `data/evaluation/results.json` | Latest benchmark output | Historical comparison | `summary` block |
| `tests/test_evaluation_dataset.py` | Dataset tests | Metadata/image integrity | Record count |
| `tests/test_evaluation_runner.py` | Runner tests | JSON schema + dummy accuracies | Semantic rate assertion |

## API contract and data flow

### Task-local flow

```text
generate_test_set.py ──> metadata.json + images/
        │
        └──> evaluate_baseline.py
                  │
                  ├──> load_config
                  ├──> InferenceWrapper + InferenceAdapter
                  ├──> for each record: imread → adapt_inference → compare
                  └──> results.json (summary + per-run rows)
```

### Metrics definitions

| Metric | Definition | What it tells you |
|--------|------------|-------------------|
| Valid action rate | % outputs in `ALLOWED_ACTIONS` (normalized) | Is prompting + parser containing syntax failures? |
| Correct action rate | % outputs matching `expected_action` | Is the model steering correctly on this set? |
| Latency splits | Mean `preprocessing_ms`, `prompting_ms`, `inference_ms`, `total_ms` | Can we hit control-loop Hz targets? |

### Target distribution (20 images)

| Seed file | Variations (×5) | Expected action |
|-----------|-----------------|-----------------|
| `red_cone_centered.png` | original, bright, low-contrast, blur, noise | `MOVE_FORWARD` |
| `red_cone_left.png` | same five | `TURN_LEFT` |
| `red_cone_right.png` | same five | `TURN_RIGHT` |
| `stop_barrier_close.png` | same five | `STOP` |

`SLOW_DOWN` is in the allowed vocabulary but not represented in this golden set — a known coverage gap.

## Naive approach vs chosen approach

| Approach | Why it seems attractive | Why we did or did not choose it |
|----------|-------------------------|---------------------------------|
| Eyeball four seeds | Fast | Misses robustness to blur/noise; no latency numbers |
| 100+ manual Webots captures | Realistic | Slow to label; blocks baseline epic |
| 4 seeds × 5 augmentations | Synthetic diversity | Cheap, repeatable, good for regression |
| Compare raw model strings | Pure VLM metric | Ignores parser; deployment uses adapter |
| Adapter output for labels | Extra work | Matches production safety path |

## Implementation breakdown

### Dataset generation

**Concept:** `scripts/generate_test_set.py` reads four Webots reference PNGs from `data/examples/`, applies OpenCV transforms, writes `data/evaluation/images/`, and emits `metadata.json` with `image_id`, `image_path`, `instruction`, `expected_action`, `variation_type`, `source_image`.

**What to notice:** Same instruction text across seeds — isolates visual reasoning from language variety.

**Why it is written this way:** Controlled variable for baseline; matches few-shot training aesthetic.

**Risks and gotchas:** Augmentations are not physics-based; high scores may not transfer to live sim.

---

### Evaluation loop

**Snippet** (`scripts/evaluate_baseline.py`):

```python
wrapper = InferenceWrapper(config)
adapter = InferenceAdapter(wrapper, config)
# ...
res = adapter.adapt_inference(image, instruction, few_shot=few_shot)
predicted = res["action"]
# compare to expected; accumulate valid_action_count, correct_action_count, latencies
```

**What to notice:** Uses adapter — metrics include parser normalization. `few_shot` CLI flag toggles prompting mode.

**Why it is written this way:** Baseline numbers reflect the same path as integration stories.

**Risks and gotchas:** `runtime.mode: dummy` yields deterministic ~25% semantic accuracy in tests — not a model quality signal.

---

### Failure categories (model behavior)

| Category | Description | Typical cause | Impact |
|----------|-------------|---------------|--------|
| A. Syntactical hallucination | Prose, markdown, or `action: STOP` wrappers | Conversational VLM prior | Parser → STOP; valid rate drops |
| B. Spatial reasoning deficit | Wrong turn direction | Small SigLIP backbone limits | Semantic accuracy drops |
| C. Distance / safety glitch | `MOVE_FORWARD` into close barrier | No depth pretraining | Collision risk in sim |

These categories guide follow-up work: prompting (A), fine-tuning (B,C), or adding `SLOW_DOWN` examples (C).

## Engineering decisions

```text
ADR: Augmentation-based test dataset
Status: Accepted
Context: Four seeds alone are too small; manual 20-frame capture is slow.
Decision: Five CV augmentations per seed → 20 labeled images.
Alternatives Rejected: Single-frame smoke test only; large human-labeled set before baseline.
Consequences: Metrics are regression-oriented, not sim-generalization proofs.
```

## Verification patterns

| Contract defended | Where |
|-------------------|-------|
| Metadata has 20 records with valid paths | `test_evaluation_dataset.py` |
| Runner exits 0 and writes JSON schema | `test_evaluation_runner.py` |
| Dummy mode semantic rate ~25%, valid 100% | `test_evaluation_runner.py` |
| Latency keys present in results | `test_evaluation_runner.py` |

**Run:**

```bash
python scripts/generate_test_set.py
python scripts/evaluate_baseline.py
pytest tests/test_evaluation_dataset.py tests/test_evaluation_runner.py -v
```

Optional few-shot benchmark:

```bash
python scripts/evaluate_baseline.py --few-shot
```

### Failure modes and debugging path

| Symptom | Likely cause | How to investigate | Fix |
|---------|--------------|--------------------|-----|
| Metadata file not found | Skipped `generate_test_set.py` | Read stderr from eval script | Run generator first |
| Valid rate 0% in model mode | Prose outputs | Inspect `results.json` per-run `raw_output` if logged | Tighten prompts; few-shot |
| Semantic 25% in dummy mode | Expected — keyword heuristics | Check `runtime.mode` | Switch to `model` for real baseline |
| All latencies 0 | Mocked or broken timing | Open `results.json` averages | Run real infer path |
| Results differ with no code change | Config or `prompt_version` drift | Diff `metadata.json` in experiment logs | Pin config file in results |

## Engineering principle taught by this task

This task teaches **measure before you train**: separate metrics for format compliance, task accuracy, and latency so you know which layer failed — prompt, model, or parser — instead of chasing a single accuracy number.

## Active learning checks

1. Why are syntax and semantic accuracy both reported?
2. Why does the dataset omit `SLOW_DOWN` examples?
3. What changes when you pass `--few-shot` to the eval script?
4. Why use adapter output rather than raw wrapper strings for `predicted`?

## Small modification exercise

Run eval twice: `prompt_version: v1` vs `v2` in local config (same `runtime.mode`). Compare `results.json` summary blocks for valid rate, correct rate, and mean `inference_ms`. Document which version wins on semantics and whether latency cost is acceptable.

## Open questions

- Should `results.json` store `raw_output` and `parse_status` per image for failure taxonomy automation?
- When do we add live Webots frames to the golden set without breaking regression comparability?
- Is 20 images enough to gate fine-tuning start, or just to gate prompt/code regressions?

## Related docs

- Adapter: [`connect-baseline-inference-to-action-parser.md`](connect-baseline-inference-to-action-parser.md)
- Prompting: [`prompting-strategy.md`](prompting-strategy.md)
- Epic walkthrough: [`index.html`](index.html)
