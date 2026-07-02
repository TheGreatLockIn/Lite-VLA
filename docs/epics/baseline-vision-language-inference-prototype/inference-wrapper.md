# inference-wrapper
**Jira Key:** [VLA-38](https://yashrajmote2001.atlassian.net/browse/VLA-38)
**Epic:** Baseline Vision-Language Inference Prototype (VLA-5)
**Human-readable version (browser):** [`inference-wrapper.html`](inference-wrapper.html)

---

## 1. Executive Summary
The inference wrapper module acts as a stable, model-agnostic layer that encapsulates the starter Vision-Language-Action (VLA) model (`SmolVLM-256M-Instruct`). It is architecturally responsible for transforming raw camera inputs and goal instruction commands into discrete action tokens, while isolating the rest of the control loop (e.g., ROS 2 nodes and safety filters) from Hugging Face library internals, tokenizer details, and tensor dimensions.

---

## 2. API Contract and Data Flow
Data flows from the camera and configuration inputs, through the preprocessor, prompt compiler, and VLM, to yield action decisions alongside timing metrics.

```text
Camera BGR Array ──> [ImagePreprocessor] ──> RGB PIL Image ──┐
                                                           ├──> [InferenceWrapper] ──> (Action Token, Latency Metrics)
Text Instruction ──> [PromptFormatter]   ──> Text Prompt   ──┘
```

### In-Memory Formats
- **Input:** Raw BGR image NumPy matrix (`numpy.ndarray`) of shape `(H, W, 3)`.
- **Output:** A structured dictionary containing:
  - `action` (`str`): The predicted navigation command from the allowed action token set: `MOVE_FORWARD`, `TURN_LEFT`, `TURN_RIGHT`, `STOP`, `SLOW_DOWN` (or `"STOP"` fallback).
  - `timing` (`dict`): Floating point execution latencies in milliseconds:
    - `preprocessing_ms`: Latency of channel conversion and image resizing.
    - `prompting_ms`: Latency of formatting templates and loading few-shot arrays.
    - `inference_ms`: Latency of token generation and model forward execution.
    - `total_ms`: End-to-end wrapper latency.
  - `success` (`bool`): Operational status indicating successful model forward pass.
  - `error` (`str` or `None`): Error string describing any runtime execution exceptions.

---

## 3. Implementation Breakdown
The core logic resides in [`litevla/inference.py`](file:///C:/Projects/Lite-VLA/litevla/inference.py).

### Model Initialization & Device Selection
The wrapper reads settings from the configuration and selectively initializes PyTorch and Hugging Face weights to support both fast local CPU testing and high-speed GPU execution:
- If `runtime.mode` is set to `"dummy"`, it bypasses downloading or loading weights to save RAM/VRAM.
- If `runtime.mode` is `"model"`, it resolves the hardware platform:
  - **CUDA:** Loads model weights in `torch.bfloat16` to take advantage of GPU Tensor Cores.
  - **MPS (Apple Silicon):** Loads model in `torch.float32`.
  - **CPU:** Loads model in `torch.float32` to avoid conversion overhead.

```python
# litevla/inference.py
if self.runtime_mode == "model":
    model_path = config.get("model", {}).get("path", "")
    device_name = config.get("model", {}).get("device", "cpu")

    # Determine device and torch_dtype
    if device_name == "cuda" and torch.cuda.is_available():
        self.device = torch.device("cuda")
        self.torch_dtype = torch.bfloat16
    elif device_name == "mps" and torch.backends.mps.is_available():
        self.device = torch.device("mps")
        self.torch_dtype = torch.float32
    else:
        self.device = torch.device("cpu")
        self.torch_dtype = torch.float32

    self.processor = AutoProcessor.from_pretrained(model_path)
    self.model = AutoModelForImageTextToText.from_pretrained(
        model_path,
        torch_dtype=self.torch_dtype,
        low_cpu_mem_usage=True
    ).to(self.device)
```

### Multimodal Few-Shot Preprocessing
When `few_shot=True` is enabled, the wrapper loads reference image paths from [litevla/prompting.py](file:///C:/Projects/Lite-VLA/litevla/prompting.py), preprocesses each historical frame through the cached `ImagePreprocessor`, converts them to PIL format, and appends the live query image to the end of the stack:

```python
# litevla/inference.py
if few_shot:
    prompt_str, image_paths = self.prompt_formatter.format_few_shot_prompt(instruction)
    images_list = []
    for path in image_paths:
        ref_bgr = cv2.imread(path)
        if ref_bgr is None:
            raise FileNotFoundError(f"Few-shot image path not found: {path}")
        ref_processed = self.preprocessor.preprocess(ref_bgr)
        if isinstance(ref_processed, bytes):
            ref_pil = Image.open(io.BytesIO(ref_processed))
        else:
            ref_pil = Image.fromarray(ref_processed)
        images_list.append(ref_pil)
    images_list.append(query_pil)
else:
    prompt_str = self.prompt_formatter.format_prompt(instruction)
    images_list = query_pil
```

### Execution, Token Decoding & Device-Safe Fallback
The processor handles raw texts and images. The token generation parameters enforce **greedy decoding** (`do_sample=False`) to avoid non-deterministic behavior during real-time steering:

```python
# litevla/inference.py
inputs = self.processor(
    text=prompt_str,
    images=images_list,
    return_tensors="pt"
)

# Move tensors to target device (handles both BatchEncoding and test dict mocks)
if hasattr(inputs, "to"):
    inputs = inputs.to(self.device)
else:
    inputs = {
        k: v.to(self.device) if isinstance(v, torch.Tensor) else v
        for k, v in inputs.items()
    }

# Generate output tokens
max_new_tokens = self.config.get("model", {}).get("max_tokens", 32)
generated_ids = self.model.generate(
    **inputs,
    max_new_tokens=max_new_tokens,
    do_sample=False
)

# Decode response and slice input tokens
input_len = inputs["input_ids"].shape[1]
action = self.processor.batch_decode(
    generated_ids[:, input_len:],
    skip_special_tokens=True
)[0].strip()
```

### Risks and Gotchas
- **Mock Dictionary Attributes:** Standard mock libraries dynamically reply to `.to()` call checks, creating fake sub-mocks. The codebase uses `isinstance(v, torch.Tensor)` to prevent this mock leakage.
- **CPU Data Conversion Overhead:** Loading `bfloat16` on CPU triggers massive conversion slowdowns; hence, `torch.float32` is strictly enforced for non-GPU targets.
- **Reference Image Missing Checks:** If the reference few-shot images under `data/examples/` are missing, the loop immediately fails. The wrapper logs the specific path error and recovers.

---

## 4. Engineering Decisions

### ADR: Model Class Binding
- **Status:** Accepted
- **Context:** The system needs a flexible model loader. While `AutoModelForVision2Seq` is common in modern VLM setups, the installed version of `transformers` only exposes `AutoModelForImageTextToText` for models derived from `Idefics3` (like SmolVLM).
- **Decision:** Adopt `AutoModelForImageTextToText` inside the loading phase to maintain direct compatibility with the local package stack.

### ADR: Safety Recovery Boundary
- **Status:** Accepted
- **Context:** If a memory spike or CUDA exception crashes the model during robot control, letting the script panic would result in the robot maintaining its last velocity command indefinitely, risking collisions.
- **Decision:** Wrap the model call in a top-level exception handler. In the event of any crash, log the traceback and return a clean dictionary with `action: "STOP"`, `success: False`, allowing the ROS controller to command immediate deceleration.

---

## 5. Verification Patterns

### Executable Unit Tests
Unit tests in [`tests/test_inference.py`](file:///C:/Projects/Lite-VLA/tests/test_inference.py) cover:
- **Dummy Mode Integrity:** Verifies zero-shot and few-shot pipeline runs, timing extraction, and deterministic action mappings.
- **Config Mismatch Rejection:** Ensures empty model configurations fail during initialization.
- **Model Execution flow:** Uses mocks to inspect correct tokenization arguments, greedy generation properties, and batch decoding.
- **OOM Catching & Safe Fallback:** Feeds runtime exceptions to check that the wrapper catches errors and falls back to `"STOP"`.

### Run Command
Execute the pytest suite using:
```bash
.venv\Scripts\pytest tests/test_inference.py -v
```
