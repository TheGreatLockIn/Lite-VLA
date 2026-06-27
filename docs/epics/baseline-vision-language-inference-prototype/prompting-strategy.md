# prompting-strategy
**Jira Key:** [VLA-37](https://yashrajmote2001.atlassian.net/browse/VLA-37)
**Epic:** Baseline Vision-Language Inference Prototype (VLA-5)
**Human-readable version (browser):** [`prompting-strategy.html`](prompting-strategy.html)

---

## 1. Intent & Context
To implement a robust and versioned baseline prompting strategy for the `SmolVLM-256M-Instruct` visual-language model (VLM). The goal is to constrain model outputs strictly to five allowed discrete action tokens: `MOVE_FORWARD`, `TURN_LEFT`, `TURN_RIGHT`, `STOP`, and `SLOW_DOWN`. 

This baseline prompting ensures the visual and language inputs are formatted in accordance with LLaVA-1.5 multimodal formatting conventions, which require an `<image>` placeholder token to position the image embeddings in the sequence of text inputs.

---

## 2. Core Interfaces
The prompting module is defined in [`litevla/prompting.py`](file:///C:/Projects/Lite-VLA/litevla/prompting.py).

### Few-Shot Examples Configuration
- **`FEW_SHOT_EXAMPLES`**: A structured list of dictionaries mapping visual navigation states and instruction commands to target actions:
  - `image_path`: Path to the reference simulation frame (stored under `data/examples/`).
  - `instruction`: Text instruction goal matching simulation conventions (e.g. `"go to the red block"`).
  - `action`: Expected target output token (e.g. `"MOVE_FORWARD"`, `"STOP"`, `"TURN_LEFT"`).

### PromptFormatter Class
- **`__init__(self, version: str = "v1")`**:
  - *Validation Logic:* Validates that `version` exists as a key in `PROMPT_VERSIONS` (defined in `litevla/prompting.py`). If the version is not found, it raises a `ValueError` indicating the invalid version and listing the supported versions.
  - *State:* Stores the selected version string, system instruction prompt template, and user goal template.
- **`format_prompt(self, instruction: str) -> str`**:
  - *Input Shape:* Takes a single string argument `instruction` representing the goal command (e.g., `"go forward to the red block"`).
  - *Output Shape:* Returns a formatted string (`str`) following the LLaVA-1.5 multimodal template structure.
  - *Template format:*
    `USER: <image>\n{system_instruction}\n\n{user_instruction_formatted}\nASSISTANT:`
- **`format_few_shot_prompt(self, instruction: str) -> tuple[str, list[str]]`**:
  - *Input Shape:* Takes a single string argument `instruction` for the current live query.
  - *Output Shape:* Returns a tuple containing:
    1. A formatted multimodal multi-image prompt string (`str`) containing sequentially placed `<image>` placeholders.
    2. A list of image paths (`list[str]`) for the reference few-shot frames in chronological order (e.g., `["data/examples/red_cone_centered.png", ...]`).
  - *Template format:*
    `USER: <image>\n{system_instruction}\n\n{user_instr_ex1}\nASSISTANT: {action_ex1}\nUSER: <image>\n{user_instr_ex2}\nASSISTANT: {action_ex2}\n...\nUSER: <image>\n{user_instr_query}\nASSISTANT:`

---

## 3. Color Space Mechanics & Multi-modal Integration
While the text prompt provides the linguistic goal, the VLM correlates it with visual embeddings. 
- **BGR to RGB Swapping:** The camera produces images in BGR format. The `ImagePreprocessor` converts them to RGB. Swapping BGR to RGB is essential because the VLM's visual encoder (`SigLIP-400M` or similar) was trained on RGB images. If colors are not swapped, a prompt referring to a "red block" would fail to align with the visual embeddings since red and blue channels would be flipped in the encoder's input space.
- **Multimodal Insertion:** The prompt template includes the special `<image>` token. When parsing the prompt, the backend (`llama-cpp-python` / `clip.cpp`) looks for this token, extracts the visual features of the processed RGB image, and replaces/inserts the image embedding tensor at the position of the `<image>` token. For few-shot prompts, multiple `<image>` slots are filled using the sequence of preprocessed reference images and the current frame.

---

## 4. In-Memory Formats & Prompt Embedding
The model handler is configured to ingest images in compressed in-memory formats:
- **JPEG Format:** Lossy compression. Highly efficient with a minimal memory footprint in RAM, making it the preferred default to reduce latency during prompt feature extraction.
- **PNG Format:** Lossless compression. Retains full color fidelity, which is critical if the prompt contains fine-grained visual instructions (e.g., identifying small labels or distant landmarks), though it increases latency due to larger byte sizes.
- **In-Memory Loading:** The preprocessed bytes (JPEG/PNG) are kept in memory and passed directly to the model's visual loader, preventing SSD wear and latency spikes. Reference images for few-shot examples are saved under `data/examples/`.

---

## 5. Unit Test Coverage
Unit tests are implemented in [`tests/test_prompting.py`](file:///C:/Projects/Lite-VLA/tests/test_prompting.py):
- **`test_allowed_actions_list`**: Asserts that `ALLOWED_ACTIONS` matches the exact expected sequence of 5 discrete actions: `MOVE_FORWARD`, `TURN_LEFT`, `TURN_RIGHT`, `STOP`, `SLOW_DOWN`.
- **`test_prompt_formatter_invalid_version`**: Validates that initializing `PromptFormatter` with an unsupported version string (e.g., `"v3"`) raises a `ValueError` with a clean error message.
- **`test_prompt_formatter_valid_versions`**: Iterates through all keys in `PROMPT_VERSIONS` (e.g. `"v1"`, `"v2"`) and asserts that `PromptFormatter` initializes without error and correctly maps the system instructions and user templates.
- **`test_format_prompt_structure`**: Verifies that the prompt output matches the LLaVA-1.5 formatting structure: starts with `"USER: <image>\n"`, ends with `"\nASSISTANT:"`, and contains the correct formatted goal instruction and the `<image>` token exactly once.
- **`test_prompt_v1_constraints`**: Verifies that the `"v1"` template prompt contains the exact list of allowed actions and explicit instructions to output exactly one action token.
- **`test_prompt_v2_constraints`**: Verifies that the `"v2"` template prompt contains instructions targeting Pioneer 3-DX robot navigation under Webots and maps out the heuristic rules for visual steering.
- **`test_format_few_shot_prompt`**: Asserts that formatting a few-shot query returns a valid string and lists the correct reference image paths. It verifies that the number of `<image>` tokens matches the reference count plus one, and ensures the correct chronological sequence of image paths is returned.
- **`test_format_few_shot_prompt_v2`**: Confirms that few-shot formatting works correctly for version `"v2"` prompt configurations and injects simulation specific constraints.

---

## 6. Configuration & Experiment Run Logging
To enable repeatable benchmarking across different prompt templates, the active prompt template version is configured inside the model settings and automatically captured in the experiment logs:
- **Configuration Schema:** A `prompt_version` configuration field is added under `model:` inside [`litevla/config/schema.json`](file:///C:/Projects/Lite-VLA/litevla/config/schema.json). Valid values are restricted to the supported versions `["v1", "v2"]` via an enum constraint.
- **Default Settings:** The default configuration in [`litevla/config/loader.py`](file:///C:/Projects/Lite-VLA/litevla/config/loader.py) assigns `"v1"` as the baseline value.
- **Run Metadata Logging:** The context manager [`ExperimentRun`](file:///C:/Projects/Lite-VLA/litevla/experiment/run.py#L173) in [`litevla/experiment/run.py`](file:///C:/Projects/Lite-VLA/litevla/experiment/run.py) automatically extracts `prompt_version` from the configuration mapping at runtime, logging it into the final `metadata.json` output for the experiment run.
- **Validation Tests:** 
  - [`tests/test_config_loader.py`](file:///C:/Projects/Lite-VLA/tests/test_config_loader.py) validates that config loading fails cleanly if required fields are missing.
  - [`tests/test_experiment_logging.py`](file:///C:/Projects/Lite-VLA/tests/test_experiment_logging.py) asserts that the exact `prompt_version` used in the configuration is recorded properly in the experiment run metadata.

