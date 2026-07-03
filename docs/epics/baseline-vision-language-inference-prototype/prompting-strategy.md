# Baseline prompting strategy

**Epic:** Baseline Vision-Language Inference Prototype (104) · **Jira:** VLA-37 / Story 1025

**Human-readable version (browser):** [`prompting-strategy.html`](prompting-strategy.html)

## Executive summary

`litevla.prompting` owns the **text-side contract** for SmolVLM baseline navigation: which discrete action tokens the model may emit, how goal instructions are wrapped in LLaVA-style templates, and how few-shot visual demonstrations are sequenced with `<image>` placeholders.

VLMs output free text, not robot commands. This module constrains the *prompt* so the model's continuation is more likely to be a single token from Epic 103's vocabulary (`MOVE_FORWARD`, `TURN_LEFT`, etc.). Parser and safety layers still treat model output as untrusted text — prompting reduces but does not eliminate hallucinated prose.

## Mental model

Think of this module as a **compiler from navigation intent to multimodal chat format**.

It exists because Hugging Face SmolVLM expects a conversation template with explicit `<image>` slots, while the robot loop only has a plain English goal string and a camera frame.

The key engineering tension is **constraint vs expressiveness**: stronger instructions reduce conversational answers but can overfit to template wording; few-shot examples teach spatial heuristics at the cost of longer prompts and more images per forward pass.

A beginner mistake is assuming the system prompt alone guarantees valid tokens — pretrained VLMs bias toward helpful natural language.

A senior engineer watches for **prompt version drift**, **`<image>` count matching image tensors**, and **alignment between `ALLOWED_ACTIONS` and Epic 103 schema**.

## Backstory: why this exists

Before this module, inference scripts inlined prompt strings. Changing "output exactly one token" wording required hunting through multiple files, and few-shot demos were copy-pasted with inconsistent `<image>` counts.

The naive solution would be a single hard-coded f-string in `InferenceWrapper`.

That breaks because prompt experiments (v1 vs v2, Webots-specific heuristics) need versioning, few-shot paths need ordered image path lists, and experiment logs must record which template was active.

So this design chooses a **`PromptFormatter` + `PROMPT_VERSIONS` registry** with shared `ALLOWED_ACTIONS` and `FEW_SHOT_EXAMPLES`.

This pattern appears in real systems as **prompt templates with schema validation** — same idea as versioned SQL migrations, but for model instructions.

## Prerequisites

- Epic 103 [`action-schema.md`](../action-interface-parser-and-safety-layer/action-schema.md) — five discrete tokens and nominal velocities.
- Image preprocessing — reference frames are BGR on disk, RGB inside the model.
- LLaVA-style format: `USER: <image>\n...\nASSISTANT:` tells the processor where to inject vision embeddings.

## Concept primer / vocabulary

| Term | Meaning in this project |
|------|-------------------------|
| VLM | Vision-language model; here SmolVLM-256M-Instruct. Outputs text, not `Twist` messages. |
| Zero-shot | Prompt uses only the live camera image + goal text; no reference demonstrations. |
| Few-shot | Prompt includes prior USER/ASSISTANT turns with reference images and gold actions before the live query. |
| `<image>` token | Placeholder in the text stream; the processor replaces it with vision embeddings. Count must match image list length. |
| `ALLOWED_ACTIONS` | Tuple of five exact uppercase tokens shared with parser and dataset labels. |
| `prompt_version` | Config key (`v1`, `v2`) selecting system instructions from `PROMPT_VERSIONS`. |
| Contract | Formatter promises: valid version → deterministic prompt string; few-shot → `(prompt, image_paths)` with matching `<image>` count. |

## Guided code reading

Read these in order:

1. `litevla/prompting.py`
   - Read `ALLOWED_ACTIONS` and `FEW_SHOT_EXAMPLES` first — the vocabulary and demo set.
   - Skim `PROMPT_VERSIONS` v1 vs v2 system text differences.
   - Then `PromptFormatter.format_prompt` and `format_few_shot_prompt`.

2. `tests/test_prompting.py`
   - `test_format_few_shot_prompt` proves `<image>` count = examples + 1.
   - Version constraint tests show fail-fast on unknown `prompt_version`.

3. `litevla/inference.py`
   - See how `prompt_version` from config constructs `PromptFormatter`.
   - Few-shot branch loads and preprocesses each path in `image_paths`.

While reading, ask:
- Where does the allowed vocabulary enter the prompt?
- How many images does each method require?
- What happens if `prompt_version` is misspelled?

## File and artifact index

| File or artifact | What it is | Why it matters | First thing to inspect |
|------------------|------------|----------------|------------------------|
| `litevla/prompting.py` | Templates, formatter, few-shot table | Source of truth for prompt text | `PROMPT_VERSIONS`, `format_few_shot_prompt` |
| `data/examples/*.png` | Reference navigation frames | Few-shot visual demonstrations | Paths in `FEW_SHOT_EXAMPLES` |
| `configs/default.example.yaml` | Runtime config | `model.prompt_version` default `v1` | `model:` section |
| `litevla/config/schema.json` | Config validation | Restricts `prompt_version` to enum | `model.prompt_version` |
| `litevla/experiment/run.py` | Experiment logging | Records `prompt_version` in `metadata.json` | Metadata extraction |

## API contract and data flow

### Task-local flow

```text
Goal instruction (str) + config.prompt_version
        │
        ├──> PromptFormatter
        │         ├── format_prompt ──> single-image LLaVA string
        │         └── format_few_shot_prompt ──> multi-image string + path list
        │
        └──> InferenceWrapper pairs string with PIL image(s) ──> SmolVLM generate ──> raw text
```

### Contract

| Surface | Rule |
|---------|------|
| **Input** | `instruction: str` (goal text); `version` from config or constructor |
| **Zero-shot output** | `str` with exactly one `<image>` before the live query `ASSISTANT:` |
| **Few-shot output** | `tuple[str, list[str]]` — prompt plus ordered reference paths (live frame appended by wrapper) |
| **Invariant** | `ALLOWED_ACTIONS` matches Epic 103 tokens; system prompt lists all five |
| **Errors** | Unknown `version` → `ValueError` listing supported keys |

Few-shot template shape (simplified):

```text
USER: <image>
{system}
{example_1_instruction}
ASSISTANT: MOVE_FORWARD
USER: <image>
{example_2_instruction}
ASSISTANT: TURN_LEFT
...
USER: <image>
{live_instruction}
ASSISTANT:
```

## Naive approach vs chosen approach

| Approach | Why it seems attractive | Why we did or did not choose it |
|----------|-------------------------|---------------------------------|
| One static prompt string | Fastest to ship | Cannot A/B test v1/v2 or log template version |
| Natural language "turn left a bit" | Easier for humans | Breaks discrete parser and dataset labels |
| JSON action output in prompt | Structured | SmolVLM baseline is text-generation; parser owns structure |
| Versioned `PromptFormatter` + few-shot table | More code | Reproducible experiments; `<image>` order is testable |
| Rely on post-hoc parser only | Parser fixes everything | Conversational outputs waste tokens and add latency |

## Implementation breakdown

### Shared vocabulary

**Snippet** (`litevla/prompting.py`):

```python
ALLOWED_ACTIONS = ("MOVE_FORWARD", "TURN_LEFT", "TURN_RIGHT", "STOP", "SLOW_DOWN")

FEW_SHOT_EXAMPLES: list[dict[str, str]] = [
    {
        "image_path": "data/examples/red_cone_centered.png",
        "instruction": "go to the red block",
        "action": "MOVE_FORWARD",
    },
    # ... left, right, stop variants ...
]
```

**What to notice:** Same five strings as `DiscreteAction` in Epic 103. Few-shot uses one instruction phrase with different visuals — teaches appearance, not phrasing variety.

**Why it is written this way:** Single vocabulary source for prompts; tests assert list equality with schema.

**Risks and gotchas:** Adding a sixth action requires coordinated changes in schema, parser, prompts, and datasets.

---

### Versioned system instructions

**Snippet:**

```python
PROMPT_VERSIONS: dict[str, dict[str, str]] = {
    "v1": {
        "system": (
            "You are an autonomous mobile robot navigator. "
            # ... lists ALLOWED_ACTIONS ...
            "Respond with exactly one action token ..."
        ),
        "user": "Goal Instruction: {instruction}",
    },
    "v2": {
        "system": (
            "You are a Pioneer 3-DX wheeled mobile robot navigating "
            "a Webots simulation arena. "
            # ... heuristic rules: centered → MOVE_FORWARD, etc. ...
        ),
        "user": "Navigate command: {instruction}",
    },
}
```

**What to notice:** v2 adds explicit spatial heuristics for Webots. Both versions demand a single token, no markdown.

**Why it is written this way:** Baseline benchmarking needs togglable templates without code forks.

**Risks and gotchas:** Heuristic text can overfit simulation layouts; zero-shot eval may not improve with v2 on unseen augments.

---

### Formatter methods

**Snippet:**

```python
def format_prompt(self, instruction: str) -> str:
    goal_text = self.user_template.format(instruction=instruction)
    return f"USER: <image>\n{self.system_instruction}\n\n{goal_text}\nASSISTANT:"

def format_few_shot_prompt(self, instruction: str) -> tuple[str, list[str]]:
    # First example includes system block; later examples omit it
    # ...
    return prompt_str, image_paths
```

**What to notice:** Few-shot returns paths only for reference frames; `InferenceWrapper` appends the live query image after preprocessing.

**Why it is written this way:** Matches LLaVA multi-turn layout; keeps formatter pure (no I/O).

**Risks and gotchas:** Missing files under `data/examples/` fail at inference time with `FileNotFoundError`, not at format time.

## Engineering decisions

```text
ADR: Discrete action constraints and multimodal few-shot
Status: Accepted
Context: VLMs hallucinate prose; Webots steering benefits from visual demonstrations.
Decision: Five-token vocabulary; FEW_SHOT_EXAMPLES with chronological <image> slots.
Alternatives Rejected: Open vocabulary motion; text-only few-shot without images.
Consequences: Prompt length and image count grow in few-shot mode; latency increases.
```

```text
ADR: prompt_version in config and experiment metadata
Status: Accepted
Context: Benchmark comparisons require knowing which template produced a run.
Decision: schema.json enum + ExperimentRun logs prompt_version.
Alternatives Rejected: Ad-hoc string in script globals.
Consequences: New template versions need schema + test updates.
```

## Verification patterns

| Contract defended | Where |
|-------------------|-------|
| `ALLOWED_ACTIONS` exact five tokens | `test_allowed_actions_list` |
| Unknown version rejected | `test_prompt_formatter_invalid_version` |
| LLaVA structure (USER/ASSISTANT, `<image>`) | `test_format_prompt_structure` |
| v1 lists allowed actions | `test_prompt_v1_constraints` |
| v2 Webots heuristics present | `test_prompt_v2_constraints` |
| Few-shot `<image>` count and paths | `test_format_few_shot_prompt` |
| Config schema + metadata logging | `test_config_loader.py`, `test_experiment_logging.py` |

**Run:**

```bash
pytest tests/test_prompting.py -v
pytest tests/test_config_loader.py tests/test_experiment_logging.py -q
```

### Failure modes and debugging path

| Symptom | Likely cause | How to investigate | Fix |
|---------|--------------|--------------------|-----|
| Model replies with sentences | Weak constraint or wrong template version | Log full prompt; check `metadata.json` `prompt_version` | Use v1/v2 with explicit "one token only"; enable few-shot |
| `ValueError: Unsupported prompt version` | Typo in config | `load_config` output | Set `model.prompt_version` to `v1` or `v2` |
| Vision/text misalignment in few-shot | `<image>` count ≠ images passed to processor | Count `<image>` in string vs `len(images_list)` | Fix `format_few_shot_prompt` or wrapper append order |
| Few-shot `FileNotFoundError` | Missing `data/examples` assets | `ls data/examples` | Restore seed images from repo |
| Valid rate 100% but semantic accuracy low | Prompt OK; model weak on spatial reasoning | Compare zero-shot vs few-shot eval | Tune v2 heuristics or plan fine-tuning (later epic) |

## Engineering principle taught by this task

This task teaches that **VLMs are text generators, not robot controllers** — prompting is the first line of defense, not the last. Structure the model's input like a strict API request; still parse and safety-gate the output.

## Active learning checks

1. Why does the formatter return image *paths* while the wrapper loads pixels?
2. How many `<image>` tokens appear in a few-shot prompt with four examples?
3. What is the difference between syntax accuracy and semantic accuracy in eval?
4. Why must `ALLOWED_ACTIONS` stay synchronized with `DiscreteAction`?

## Small modification exercise

Add a comment-only duplicate of the v2 system block describing when to output `SLOW_DOWN`, without changing `PROMPT_VERSIONS` yet. Run `pytest tests/test_prompting.py` to confirm no drift. Then switch local config to `prompt_version: v2`, run `python scripts/evaluate_baseline.py`, and compare `metadata.json` / `results.json` prompt fields to a v1 run.

## Open questions

- Should `SLOW_DOWN` appear in few-shot examples (currently only four spatial refs)?
- Is v2's heuristic text helping zero-shot eval or only memorizing seed layouts?
- Do we need a `v3` with JSON-only output once parser supports structured extraction?

## Related docs

- Discrete tokens: [`../action-interface-parser-and-safety-layer/action-schema.md`](../action-interface-parser-and-safety-layer/action-schema.md)
- Inference integration: [`inference-wrapper.md`](inference-wrapper.md)
- Zero-shot metrics: [`zero-shot-evaluation.md`](zero-shot-evaluation.md)
