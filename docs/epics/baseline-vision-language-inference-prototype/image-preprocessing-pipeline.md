# Image preprocessing pipeline

**Epic:** Baseline Vision-Language Inference Prototype (104) · **Jira:** VLA-36 / Story 1024

**Human-readable version (browser):** [`image-preprocessing-pipeline.html`](image-preprocessing-pipeline.html)

## Executive summary

`litevla.preprocessing` owns the **camera-frame contract** between OpenCV capture and the SmolVLM vision encoder. It converts simulation or ROS camera frames (BGR `numpy` arrays) into model-ready tensors or in-memory JPEG/PNG bytes with consistent size, color order, and encoding.

Downstream modules (`InferenceWrapper`, evaluation scripts) depend on this layer so they never re-implement BGR→RGB swaps, resize rules, or compression logic. Getting color order wrong silently inverts red and blue in the visual embedding space — a classic beginner failure mode that looks like "the model ignores the red block."

## Mental model

Think of this module as a **camera adapter** between robot vision hardware and a pretrained VLM.

It exists because VLMs were trained on RGB images at fixed resolutions, while OpenCV and most robot drivers deliver BGR arrays at arbitrary sizes.

The key engineering tension is **fidelity vs latency**: lossy JPEG shrinks memory and transfer time; raw arrays skip encode/decode but may not match every inference backend.

A beginner mistake is passing BGR directly to the model because "it still looks like a normal image on screen."

A senior engineer watches for **channel order**, **resize aspect ratio**, and **whether the consumer expects bytes or a PIL/array object**.

## Backstory: why this exists

Before this module existed, every script that touched a VLM duplicated resize and color-conversion code inline. That scattered logic made it easy to fix preprocessing in tests but ship the wrong channel order in evaluation.

The naive solution would be to call `cv2.resize` once in `InferenceWrapper` and pass the array straight to Hugging Face.

That breaks because OpenCV defaults to BGR, SigLIP (SmolVLM's vision backbone) expects RGB, and some inference paths historically required file-like JPEG/PNG bytes rather than raw matrices.

So this design chooses a **single configurable preprocessor** loaded from the global config dict, with fail-fast validation at construction time.

This pattern appears in real systems as an **ETL boundary** for sensor data: normalize once at the edge, keep ML code backend-agnostic.

## Prerequisites

- OpenCV reads images as BGR; PIL and most VLMs expect RGB.
- SmolVLM-256M-Instruct uses a SigLIP vision encoder trained on natural RGB photos.
- Epic 103 discrete actions are unrelated here — this task only prepares pixels.

## Concept primer / vocabulary

| Term | Meaning in this project |
|------|-------------------------|
| BGR | OpenCV's default channel order (blue, green, red). Camera frames from `cv2.imread` or `/image_raw` bridges arrive this way. |
| RGB | Channel order expected by SigLIP and PIL. Red and blue channels are swapped relative to BGR. |
| `ImagePreprocessor` | Config-driven class in `litevla/preprocessing.py` that validates settings and transforms frames. |
| `PreprocessingError` | Raised on invalid config, bad input shape, or OpenCV failures — distinct from model errors. |
| In-memory encoding | `cv2.imencode` writes JPEG/PNG into a byte buffer without touching disk. |
| Contract | The promise this module makes: given a 3-channel BGR `(H, W, 3)` array, return resized pixels in the configured color space, optionally as compressed bytes. |

## Guided code reading

Read these in order:

1. `litevla/preprocessing.py`
   - Start with `ImagePreprocessor.__init__` — what is validated before any frame is processed?
   - Then read `preprocess()` — follow color convert → resize → encode.
   - Ignore callers for now; this file has no ROS or torch imports.

2. `tests/test_preprocessing.py`
   - See how a synthetic half-red / half-blue image proves RGB channel swap.
   - `test_preprocessing_encoding_jpeg` shows the bytes round-trip contract.

3. `litevla/inference.py` (consumer)
   - After `preprocess()`, bytes become `PIL.Image` via `io.BytesIO`; arrays use `Image.fromarray`.
   - The wrapper owns timing around this step.

While reading, ask:
- Where does data enter? (BGR `numpy` from camera or file.)
- Where is it validated? (`__init__` for config; `preprocess()` for array shape.)
- Where can it fail? (Wrong dimensions, unsupported format strings, OpenCV errors.)
- Who owns the final side effect? (Caller converts output to PIL for the model.)

## File and artifact index

| File or artifact | What it is | Why it matters | First thing to inspect |
|------------------|------------|----------------|------------------------|
| `litevla/preprocessing.py` | Preprocessor implementation | Single source of truth for frame normalization | `preprocess()` color and encode branches |
| `configs/default.example.yaml` | Example runtime config | Shows `model`, `safety`, `runtime`; `preprocessing` section is optional with code defaults | Add `preprocessing:` block when tuning resize |
| `tests/test_preprocessing.py` | Unit tests | Executable spec for resize, RGB swap, JPEG bytes | `test_preprocessing_resize_and_color_rgb` |
| `data/examples/*.png` | Few-shot reference frames | Consumed later by prompting/inference, preprocessed the same way | Channel order after `cv2.imread` |

## API contract and data flow

### Task-local flow

```text
Camera / file BGR (H, W, 3)
        │
        ├──> validate shape (3-channel ndarray)
        ├──> color convert (BGR → RGB | gray | keep BGR)
        ├──> resize (bilinear to config width × height)
        └──> encode (jpeg | png bytes) OR return raw ndarray
                    │
                    └──> InferenceWrapper → PIL Image → SmolVLM processor
```

### Contract

In this module, **contract** means the guaranteed input/output shape and semantics any caller can rely on without re-reading OpenCV docs.

| Surface | Rule |
|---------|------|
| **Input** | `numpy.ndarray`, shape `(H, W, 3)`, BGR channel order |
| **Config** | `preprocessing` dict: `resize_width`, `resize_height`, `color_format` (`rgb`/`bgr`/`gray`), `encoding` (`jpeg`/`png`/`none`) |
| **Output** | `bytes` (JPEG/PNG) when encoding is set; `numpy.ndarray` when `encoding: none` |
| **Invariant** | Default resize 512×512, `color_format: rgb`, `encoding: jpeg` if config section missing |
| **Errors** | `PreprocessingError` on bad config, non-ndarray input, wrong rank, or OpenCV failure |

Example config (add to `configs/local.yaml`):

```yaml
preprocessing:
  resize_width: 512
  resize_height: 512
  color_format: rgb
  encoding: jpeg
```

## Naive approach vs chosen approach

| Approach | Why it seems attractive | Why we did or did not choose it |
|----------|-------------------------|---------------------------------|
| Resize inside `InferenceWrapper` only | Fewer files | Duplicates logic; tests cannot validate vision input in isolation |
| Pass BGR directly to the model | One less `cvtColor` call | Inverts red/blue in embeddings; "red block" prompts fail silently |
| Write JPEG to disk per frame | Simple debugging | Adds I/O latency and wear; hurts 5–10 Hz control loops |
| Central `ImagePreprocessor` + config | Extra class | One tested boundary; same path for live camera, few-shot refs, and eval set |

## Implementation breakdown

### Config loading and fail-fast validation

**Snippet** (`litevla/preprocessing.py`):

```python
preproc_cfg = config.get("preprocessing", {})
if not preproc_cfg:
    preproc_cfg = {
        "resize_width": 512,
        "resize_height": 512,
        "color_format": "rgb",
        "encoding": "jpeg",
    }
# ...
if self.color_format not in {"rgb", "bgr", "gray"}:
    raise PreprocessingError(f"Unsupported color format: {self.color_format}")
```

**What to notice:** Empty or missing `preprocessing` config does not crash — sensible defaults apply. Invalid enum strings fail at **startup**, not on the first camera frame.

**Why it is written this way:** Robot nodes should refuse to boot with bad config rather than publish garbage embeddings mid-run.

**Risks and gotchas:** `default.example.yaml` does not yet list `preprocessing`; newcomers may assume it is required. Defaults are code-owned, not YAML-owned.

---

### Color space and resize pipeline

**Snippet:**

```python
if self.color_format == "rgb":
    processed = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
# ...
processed = cv2.resize(
    processed,
    (self.resize_width, self.resize_height),
    interpolation=cv2.INTER_LINEAR,
)
```

**What to notice:** Input is always documented as BGR; `color_format: bgr` copies without swap. Grayscale collapses to 2D — verify your model path supports it before enabling.

**Why it is written this way:** OpenCV and robot drivers are the de facto BGR suppliers; RGB is the ML training convention.

**Risks and gotchas:** Bilinear resize on wide aspect-ratio frames distorts objects. Future work may add letterboxing. Wrong `color_format` is the hardest bug to spot because previews still "look fine."

---

### In-memory JPEG/PNG encoding

**Snippet:**

```python
success, encoded_img = cv2.imencode(ext, processed)
if not success:
    raise PreprocessingError(f"Failed to encode image to {self.encoding} format")
return encoded_img.tobytes()
```

**What to notice:** Returns raw file bytes, not a base64 string. `InferenceWrapper` decodes via `PIL.Image.open(io.BytesIO(...))`.

**Why it is written this way:** Matches file-based VLM loaders while avoiding disk I/O; keeps a path open for GGUF/llama.cpp backends that ingest encoded buffers.

**Risks and gotchas:** JPEG is lossy — fine for navigation, risky for fine-grained label reading. `encoding: none` returns ndarray; caller must handle dtype and channel count.

## Engineering decisions

```text
ADR: In-memory compression
Status: Accepted
Context: Some VLM backends ingest JPEG/PNG bytes or paths, not raw NumPy matrices.
Decision: Optional cv2.imencode in RAM; default jpeg for latency.
Alternatives Rejected: Per-frame disk writes (too slow); always raw arrays (not portable across backends).
Consequences: InferenceWrapper must branch on bytes vs ndarray; lossy default may hide compression artifacts in eval.
```

```text
ADR: BGR in, RGB default out
Status: Accepted
Context: Camera pipeline is OpenCV-native; SigLIP is RGB-trained.
Decision: Document input as BGR; default color_format rgb.
Alternatives Rejected: Auto-detect channel order (unreliable); require callers to pre-convert (error-prone).
Consequences: Any new image source must use BGR or explicitly set color_format.
```

## Verification patterns

Tests defend specific behavioral contracts:

| Contract defended | Where |
|-------------------|-------|
| Defaults when config section empty | `test_preprocessor_init_with_defaults` |
| Invalid dimensions/formats rejected at init | `test_preprocessor_init_invalid_configs` |
| BGR → RGB channel swap + resize | `test_preprocessing_resize_and_color_rgb` |
| Grayscale output shape | `test_preprocessing_gray` |
| JPEG bytes round-trip decodable | `test_preprocessing_encoding_jpeg` |
| Bad input type/shape raises `PreprocessingError` | `test_preprocessing_input_validation` |

**Run:**

```bash
pytest tests/test_preprocessing.py -v
```

### Failure modes and debugging path

| Symptom | Likely cause | How to investigate | Fix |
|---------|--------------|--------------------|-----|
| Model steers away from red targets | BGR passed as RGB (channels flipped) | Log mean of R vs B channel on a known red patch | Set `color_format: rgb`; verify `test_preprocessing_resize_and_color_rgb` |
| `PreprocessingError` at node startup | Invalid `color_format` or negative resize | Check config against schema | Fix `preprocessing` block; restart |
| `PreprocessingError` on frame | Non-3-channel array or wrong dtype | Print `image.shape` from camera callback | Ensure `(H,W,3)` uint8 BGR |
| JPEG decode fails downstream | Corrupt bytes or wrong encoding flag | `cv2.imdecode` on returned bytes in REPL | Match `encoding` with consumer expectations |
| Stretched objects in VLM attention | Fixed resize without aspect preservation | Compare source aspect to 512×512 output | Tune dimensions or add letterbox (future) |

## Engineering principle taught by this task

This task teaches the **sensor normalization boundary**: treat camera frames like an API with explicit color order, dimensions, and encoding — never assume the model "sees what you see" on a matplotlib plot.

## Active learning checks

Before modifying this module, answer:

1. Why is input documented as BGR when humans think in RGB?
2. What breaks if you skip `cvtColor` but the preview image still looks correct?
3. When does this module return `bytes` vs `ndarray`, and who converts to PIL?
4. Why validate config in `__init__` instead of lazily on first frame?

## Small modification exercise

Change `resize_width` and `resize_height` to `384` in your local config, run `pytest tests/test_preprocessing.py`, then run one `InferenceWrapper.infer()` call in dummy mode and confirm `timing.preprocessing_ms` is still populated. Expected: tests pass; preprocessing timing reflects the new code path without changing action output in dummy mode.

## Open questions

- Should `default.example.yaml` include an explicit `preprocessing` section so defaults are visible without reading Python?
- Do we need letterbox resize to preserve aspect ratio for Webots camera frames?
- When the stack is Hugging Face-only, is JPEG encoding still worth the encode/decode cost vs direct ndarray→PIL?

## Related docs

- Prompting (text + `<image>` slots): [`prompting-strategy.md`](prompting-strategy.md)
- Inference consumer: [`inference-wrapper.md`](inference-wrapper.md)
- Epic walkthrough: [`index.html`](index.html)
