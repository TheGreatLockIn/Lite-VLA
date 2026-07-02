# zero-shot-evaluation
**Jira Key:** [VLA-161](https://yashrajmote2001.atlassian.net/browse/VLA-161) (Subtask VLA-10083)
**Epic:** Baseline Vision-Language Inference Prototype (VLA-5)
**Human-readable version (browser):** [`zero-shot-evaluation.html`](zero-shot-evaluation.html)

---

## 1. Executive Summary
The zero-shot evaluation module measures how well the untrained, starter vision-language-action (VLA) model (`SmolVLM-256M-Instruct`) follows our discrete prompting constraints and produces steering decisions. By running the model over a controlled, augmented test dataset, we establish baseline metrics (syntax accuracy, semantic correctness, and latencies) prior to dataset collection and fine-tuning.

---

## 2. Dataset Structure and Augmentations
The evaluation set contains **20 images** programmatically generated via [scripts/generate_test_set.py](file:///C:/Projects/Lite-VLA/scripts/generate_test_set.py) using the 4 real Webots simulation frames as seeds. Each seed maps to 5 distinct variations simulating typical robotic camera artifacts:

- **Original:** Unmodified BGR frame.
- **Brightness High:** Scaled pixel intensities (adding a constant beta value) simulating bright arena spotlights.
- **Contrast Low:** Blended colors simulating light glare or dusty camera lenses.
- **Gaussian Blur:** Convolution filter (9x9 kernel) simulating motion blur and defocus.
- **Sensor Noise:** Gaussian noise (sigma=18) added to BGR channels simulating sensor compression.

### Target Distribution
| Original Seed File | Variation Types | Target Ground-Truth Action | Count |
| :--- | :--- | :--- | :--- |
| `red_cone_centered.png` | original, bright, low-contrast, blur, noise | `MOVE_FORWARD` | 5 |
| `red_cone_left.png` | original, bright, low-contrast, blur, noise | `TURN_LEFT` | 5 |
| `red_cone_right.png` | original, bright, low-contrast, blur, noise | `TURN_RIGHT` | 5 |
| `stop_barrier_close.png` | original, bright, low-contrast, blur, noise | `STOP` | 5 |

The dataset metadata is compiled in [data/evaluation/metadata.json](file:///C:/Projects/Lite-VLA/data/evaluation/metadata.json).

---

## 3. Evaluation Runner
The evaluation loop is implemented in [scripts/evaluate_baseline.py](file:///C:/Projects/Lite-VLA/scripts/evaluate_baseline.py).

```text
[metadata.json] ──> Read Records ──> Loop 20 Images ──> [InferenceWrapper] ──> Compare predictions ──> [results.json]
```

### Metrics Definitions
1. **Valid Action Rate (Syntax Accuracy):** The percentage of generated model tokens that belong strictly to the 5 allowed action commands: `MOVE_FORWARD`, `TURN_LEFT`, `TURN_RIGHT`, `STOP`, `SLOW_DOWN` (ignoring case/whitespace).
2. **Correct Action Rate (Semantic Accuracy):** The percentage of generated model tokens that match the exact expected ground-truth steering decision.
3. **Latency Splits:** The average execution time in milliseconds for the pipeline stages: preprocessing, prompting, model inference, and overall total loop.

---

## 4. Failure Categories Summary

Through zero-shot testing, VLA model errors are classified into three primary categories:

### A. Syntactical Hallucinations (Syntax Failures)
- **Description:** The model outputs explanation text, punctuation, quotes, or markdown instead of the raw action token (e.g. *`"I should TURN_LEFT to reach the block."`* or *`"action: STOP"`*).
- **Cause:** Pretrained VLMs are trained to be conversational assistants and have a high bias toward formatting and natural language responses, which overrides the system prompt's format constraints.
- **Impact:** Prevents the ROS action parser node from reading the command, requiring safe STOP fallbacks.

### B. Spatial Reasoning Deficits (Semantic Failures)
- **Description:** The model selects a wrong directional action (e.g. predicting `TURN_RIGHT` when the target red block is clearly on the left).
- **Cause:** SmolVLM-256M-Instruct has a lightweight visual encoder (`SigLIP-93M`) that struggles with fine-grained spatial coordination and coordinate offsets without custom tuning.
- **Impact:** Causes the robot to steer away from the target object.

### C. Distance and Safety Glitches
- **Description:** The model predicts `MOVE_FORWARD` when the target obstacle is directly blocking the front camera (distance threshold underflow).
- **Cause:** Pretrained language components do not inherently map the visual size of the obstacle to the concept of depth or stopping limits.
- **Impact:** Leads to physical collisions in the simulation.

---

## 5. Engineering Decisions

### ADR: Augmentation-based Test Dataset
- **Status:** Accepted
- **Context:** To compute meaningful baseline rates, evaluating against only the 4 seed images is insufficient. However, collecting 20 separate manual frames from Webots is slow and error-prone.
- **Decision:** Apply standard computer vision augmentations (blur, contrast, brightness, noise) to the 4 seed images. This generates 20 distinct scenarios that test the model's robustness to visual camera artifacts.

---

## 6. Verification Patterns

### Executable Unit Tests
Unit tests in [tests/test_evaluation_runner.py](file:///C:/Projects/Lite-VLA/tests/test_evaluation_runner.py) check:
- Clean runner execution and exit code handling.
- JSON structure and schema verification of the output benchmark report.
- Semantic correctness checks (dummy mode yields exactly 25% semantic accuracy and 100% valid token rate).

### Run Commands
1. **Generate Dataset:**
   ```bash
   .venv\Scripts\python scripts/generate_test_set.py
   ```
2. **Execute Evaluation:**
   ```bash
   .venv\Scripts\python scripts/evaluate_baseline.py
   ```
3. **Execute Unit Tests:**
   ```bash
   .venv\Scripts\pytest tests/test_evaluation_dataset.py tests/test_evaluation_runner.py -v
   ```
