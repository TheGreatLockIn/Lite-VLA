# Prepare model training format — code walkthrough

**Epic:** Supervised Fine-Tuning and Model Evaluation (106) · **Jira:** Story 1036, subtasks 10108–10110 · **Status:** Complete (verified locally)

**Human-readable version (browser):** [`prepare-model-training-format.html`](prepare-model-training-format.html)

**Architecture doc (system design):** [`../architecture/prepare-model-training-format.md`](../architecture/prepare-model-training-format.md)

## Files touched

| File | Role in this task |
|------|-------------------|
| `ml/__init__.py` | Declares `ml` as the project’s ML package |
| `ml/finetune/__init__.py` | Exposes the public Story 1036 formatting API |
| `ml/finetune/prompt_template.py` | Builds inference-aligned prompt, target, and full-text parts |
| `ml/finetune/format_dataset.py` | Converts `TrainingRecord` objects and writes SFT JSONL |
| `scripts/format_training_data.py` | Command-line entry point for conversion |
| `scripts/inspect_training_samples.py` | Command-line quality gate for reviewing formatted examples |
| `tests/test_training_format.py` | Automated contract checks; run with pytest |

## Plain-English purpose

The code turns an Epic 105 `TrainingRecord` into a small, explicit Python object containing the image path, input prompt, expected action, and complete prompt-plus-answer text. It reuses the inference prompt formatter instead of inventing a training-only syntax.

This walkthrough focuses on how the Python implementation performs that transformation. For the system contract, masking boundary, trade-offs, and ADRs, read the [architecture doc](../architecture/prepare-model-training-format.md).

## Concepts in this task

- Frozen dataclasses (`@dataclass(frozen=True)`)
- Type annotations and union types (`str | None`)
- Keyword-only arguments (`*`)
- Package public APIs (`__all__`)
- Iterator and list transformations
- JSONL serialization
- `pathlib.Path`
- `argparse` command-line interfaces
- Prompt/target separation
- Assistant-only loss masking boundary
- Train/inference prompt alignment
- Hard errors vs soft warnings
- Process exit codes

## How to run and verify

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest \
  tests/test_training_format.py -q
```

Expected result: `8 passed`.

```bash
.venv/bin/ruff check \
  ml/ \
  scripts/format_training_data.py \
  scripts/inspect_training_samples.py \
  tests/test_training_format.py
```

Expected result: `All checks passed!`

```bash
.venv/bin/python scripts/format_training_data.py \
  --input data/processed/v0.1.0/train_reviewed.jsonl \
  --output data/processed/v0.1.0/sft_train.jsonl \
  --prompt-version v1
```

Expected result for the local v0.1.0 reviewed dataset: `Wrote 501 SFT examples → data/processed/v0.1.0/sft_train.jsonl`, followed by prompt-version and first-sample details.

```bash
.venv/bin/python scripts/inspect_training_samples.py \
  --input data/processed/v0.1.0/train_reviewed.jsonl \
  --n 10
```

Expected result: `Summary: 10/10 samples passed format checks (0 with image warnings)` when all reviewed images are present.

## Follow one example through the pipeline

Use this validated Epic 105 record throughout:

```json
{
  "id": "ref_001",
  "image_path": "data/reference_images/red_cone_centered.png",
  "instruction": "Move toward the red cube.",
  "action": "MOVE_FORWARD",
  "timestamp": "2026-06-24T12:00:00+00:00",
  "source": "reference"
}
```

```text
JSON line
  ↓ read_jsonl
TrainingRecord
  ↓ TrainingPromptTemplate.build
TrainingPromptParts
  ↓ format_training_record
FormattedSFTExample
  ↓ write_sft_jsonl
compact JSON line
```

### Stage 1: `read_jsonl` — `litevla/data/schema.py`

`litevla.data.schema.read_jsonl` (an existing dependency) validates the JSON object and returns a `TrainingRecord`. At this point the important values are Python strings:

| Name | Value |
|------|-------|
| `record.instruction` | `"Move toward the red cube."` |
| `record.action` | `"MOVE_FORWARD"` |
| `record.image_path` | `"data/reference_images/red_cone_centered.png"` |

The type transition is JSON text on disk → Python dictionary during parsing → frozen `TrainingRecord`.

### Stage 2: `TrainingPromptTemplate.build` — `ml/finetune/prompt_template.py`

`format_training_record` passes `record.instruction` and `record.action` to the shared template:

```python
parts = tmpl.build(record.instruction, record.action)
```

Inside `build`, `action.strip().upper()` produces `"MOVE_FORWARD"`. `is_valid_action` accepts it. `PromptFormatter.format_prompt` then returns:

```text
USER: <image>
You are an autonomous mobile robot navigator. Analyze the visual frame and goal instruction, then select the single best action from the following allowed list:
Allowed Actions: MOVE_FORWARD, TURN_LEFT, TURN_RIGHT, STOP, SLOW_DOWN

Respond with exactly one action token from the allowed list and absolutely nothing else. Do not include explanation, punctuation, or conversational text.

Goal Instruction: Move toward the red cube.
ASSISTANT:
```

The method appends one space and the normalized action to produce `full_text`.

| Name | Shape after this stage |
|------|------------------------|
| `parts.prompt` | Input text ending in `ASSISTANT:` |
| `parts.target` | `"MOVE_FORWARD"` |
| `parts.full_text` | Prompt followed by `" MOVE_FORWARD"` |
| `parts.prompt_version` | `"v1"` |

The type transition is two source strings → `TrainingPromptParts`.

### Stage 3: `format_training_record` — `ml/finetune/format_dataset.py`

The formatter combines `parts` with audit fields from the source record:

```python
return FormattedSFTExample(
    id=record.id,
    image_path=record.image_path,
    instruction=record.instruction,
    action=record.action,
    prompt=parts.prompt,
    target=parts.target,
    full_text=parts.full_text,
    prompt_version=parts.prompt_version,
    source=record.source,
    episode_id=record.episode_id,
    image_exists=image_exists,
)
```

The result is another frozen dataclass. The source `action` and formatted `target` are intentionally both visible, allowing the inspection tool to verify equality.

| Output field | Concrete value |
|--------------|----------------|
| `id` | `"ref_001"` |
| `image_path` | `"data/reference_images/red_cone_centered.png"` |
| `instruction` | `"Move toward the red cube."` |
| `action` / `target` | `"MOVE_FORWARD"` / `"MOVE_FORWARD"` |
| `prompt_version` | `"v1"` |
| `image_exists` | `None` when no check was requested |

### Stage 4: `formatted_example_to_dict` and `write_sft_jsonl` — `ml/finetune/format_dataset.py`

`formatted_example_to_dict` calls `asdict(example)`, then removes keys whose values are `None`. `write_sft_jsonl` encodes the remaining mapping as compact JSON and writes one newline.

The final object contains:

```json
{
  "image_path": "data/reference_images/red_cone_centered.png",
  "instruction": "Move toward the red cube.",
  "action": "MOVE_FORWARD",
  "prompt": "USER: <image>\nYou are an autonomous mobile robot navigator. Analyze the visual frame and goal instruction, then select the single best action from the following allowed list:\nAllowed Actions: MOVE_FORWARD, TURN_LEFT, TURN_RIGHT, STOP, SLOW_DOWN\n\nRespond with exactly one action token from the allowed list and absolutely nothing else. Do not include explanation, punctuation, or conversational text.\n\nGoal Instruction: Move toward the red cube.\nASSISTANT:",
  "target": "MOVE_FORWARD",
  "full_text": "USER: <image>\nYou are an autonomous mobile robot navigator. Analyze the visual frame and goal instruction, then select the single best action from the following allowed list:\nAllowed Actions: MOVE_FORWARD, TURN_LEFT, TURN_RIGHT, STOP, SLOW_DOWN\n\nRespond with exactly one action token from the allowed list and absolutely nothing else. Do not include explanation, punctuation, or conversational text.\n\nGoal Instruction: Move toward the red cube.\nASSISTANT: MOVE_FORWARD",
  "prompt_version": "v1",
  "id": "ref_001",
  "source": "reference"
}
```

The type transition is `FormattedSFTExample` → dictionary → JSON text.

### Stage 5: `_check_example` and `main` — `scripts/inspect_training_samples.py`

`scripts/inspect_training_samples.py` checks that:

- `<image>` occurs in `prompt`;
- `prompt` ends with `ASSISTANT:`;
- `target == action`;
- `target` is valid;
- `full_text` ends with `target`;
- the answer was not already inserted into `prompt`.

For `ref_001`, the shared markers are present, `action == target == "MOVE_FORWARD"`, and the checked reference image exists, so `_check_example` returns `([], [])`. `_print_example` therefore renders status `OK`; `main` includes it in the passed count.

## Related dependencies

| Dependency | Role in this task |
|------------|-------------------|
| `litevla.data.schema.TrainingRecord` | Validated, model-neutral source record from Epic 105 |
| `litevla.data.schema.read_jsonl` | Parses and validates input JSONL before formatting |
| [`litevla.prompting.PromptFormatter`](../../baseline-vision-language-inference-prototype/prompting-strategy.md) | Shared inference prompt syntax used to prevent train/runtime drift |
| [`litevla.prompting.PROMPT_VERSIONS`](../../baseline-vision-language-inference-prototype/prompting-strategy.md) | Allowed CLI values for `--prompt-version` |
| [`litevla.actions.ACTION_NAMES`](../../action-interface-parser-and-safety-layer/action-schema.md) | Shared five-action vocabulary used in messages and inspection |
| [`litevla.actions.is_valid_action`](../../action-interface-parser-and-safety-layer/action-schema.md) | Exact action-label validator |

## File walkthrough: `ml/finetune/prompt_template.py`

This is the heart of the prompt boundary. It does not read files or tokenize text; it receives one instruction/action pair and returns a validated, immutable representation.

### Imports

| Import | Plain meaning | Why it is needed |
|--------|---------------|------------------|
| `from __future__ import annotations` | Defers annotation evaluation | Keeps modern type annotations lightweight |
| `from dataclasses import dataclass` | Dataclass decorator | Defines immutable value objects without manual constructors |
| `from litevla.actions import ACTION_NAMES, is_valid_action` | Shared action API | Validates targets and builds useful errors |
| `from litevla.prompting import PromptFormatter` | Existing inference formatter | Makes training prompt text match runtime |

### Module-level constants

`ASSISTANT_PREFIX = "ASSISTANT:"` names the boundary instead of scattering a string literal across the implementation and inspection script.

`IMAGE_TOKEN = "<image>"` names the multimodal placeholder. The template only verifies its presence; a future model processor decides how it expands into model inputs.

### `TrainingPromptParts`

```python
@dataclass(frozen=True)
class TrainingPromptParts:
    prompt: str
    target: str
    full_text: str
    prompt_version: str
```

`@dataclass` generates `__init__`, equality, and representation methods. `frozen=True` prevents field reassignment after construction, which is useful because these strings form a contract: later conversion code should copy them, not mutate them.

The class separates four related values:

- `prompt` is answer-free input.
- `target` is the expected action.
- `full_text` is the tokenization string.
- `prompt_version` records which shared template produced the text.

### `TrainingPromptTemplate.__init__`

```python
def __init__(self, version: str = "v1") -> None:
    self.formatter = PromptFormatter(version=version)
    self.version = version
```

Calling `PromptFormatter` performs version validation, so unsupported versions fail during template construction. `self` refers to the new `TrainingPromptTemplate` instance. Saving one formatter allows `format_training_records` to reuse it for every row rather than rebuilding it repeatedly.

### `TrainingPromptTemplate.build`

The method accepts an instruction and action and returns `TrainingPromptParts`.

```python
token = action.strip().upper()
if not is_valid_action(token):
    valid = ", ".join(ACTION_NAMES)
    raise ValueError(...)
```

`.strip()` removes accidental surrounding whitespace and `.upper()` normalizes case. The resulting token still must be a real Epic 103 action. `", ".join(ACTION_NAMES)` creates an error-friendly list such as `"MOVE_FORWARD, TURN_LEFT, ..."`.

```python
prompt = self.formatter.format_prompt(instruction)
if not prompt.endswith(ASSISTANT_PREFIX):
    raise ValueError(...)
if IMAGE_TOKEN not in prompt:
    raise ValueError(...)
```

These are structural assertions against the external `PromptFormatter` result. The method fails rather than silently adding missing markers because a changed inference prompt is a contract event that maintainers need to see.

```python
full_text = f"{prompt} {token}"
return TrainingPromptParts(...)
```

The f-string adds exactly one separator space. The returned dataclass preserves both pieces and their joined form.

### `build_training_prompt`

This function is a convenience for callers formatting one example:

```python
return TrainingPromptTemplate(version=version).build(instruction, action)
```

The `*` in its signature makes `version` keyword-only, so callers write `version="v2"` instead of passing an unexplained third positional argument.

## File walkthrough: `ml/finetune/format_dataset.py`

This module owns representation conversion and persistence. It composes the Story 1036 prompt boundary with Epic 105’s record type.

### Imports

| Import | Plain meaning | Why it is needed |
|--------|---------------|------------------|
| `from __future__ import annotations` | Deferred annotations | Supports concise modern type hints |
| `import json` | Standard JSON encoder | Writes one compact object per line |
| `from collections.abc import Iterator` | Iterator protocol type | Describes streaming record inputs |
| `from dataclasses import asdict, dataclass` | Dataclass tools | Defines and serializes the output value object |
| `from pathlib import Path` | Filesystem path abstraction | Resolves images and output files |
| `from typing import Any` | Unconstrained value type | Types serialized dictionary values |
| `from litevla.data.schema import REPO_ROOT, TrainingRecord, read_jsonl` | Epic 105 data API | Supplies root, source type, and validated reader |
| `from ml.finetune.prompt_template import TrainingPromptTemplate` | Story prompt adapter | Builds prompt/target parts |

### `FormattedSFTExample`

This frozen dataclass is the public in-memory schema:

| Field | Value carried through the pipeline |
|-------|------------------------------------|
| `image_path` | Source image reference; the image itself is not loaded |
| `instruction` | Natural-language goal from the reviewed record |
| `action` | Source label retained for audit/comparison |
| `prompt` | Answer-free runtime-aligned text ending at `ASSISTANT:` |
| `target` | Normalized action text used as supervision |
| `full_text` | Prompt plus one space plus target |
| `prompt_version` | Shared formatter version that produced the prompt |
| `id` | Optional source record identifier |
| `source` | Optional provenance such as `manual_review` or `reference` |
| `episode_id` | Optional capture episode identifier |
| `image_exists` | `True`/`False` when checked; `None` when not checked |

`TrainingRecord.timestamp` and `TrainingRecord.metadata` are deliberately not copied into the SFT example. They remain available in the source dataset; later experiment metadata must identify that source dataset for provenance.

### `format_training_record`

The signature uses `*`, making all configuration arguments keyword-only. This prevents confusing calls where `"v2"` or a path appears positionally.

```python
tmpl = template or TrainingPromptTemplate(version=prompt_version)
parts = tmpl.build(record.instruction, record.action)
```

Callers formatting a single record may rely on `prompt_version`; batch conversion passes a shared `template`. The `or` expression chooses the supplied template when it is truthy.

The optional image branch resolves relative paths against `repo_root` or the repository default:

```python
if check_image:
    root = repo_root or REPO_ROOT
    path = Path(record.image_path)
    if not path.is_absolute():
        path = root / path
    image_exists = path.is_file()
```

No image is loaded here; only filesystem existence is checked. The function then creates `FormattedSFTExample`, combining source fields with formatted fields.

### `format_training_records`

This function creates one `TrainingPromptTemplate` and uses a list comprehension to transform every source record:

```python
return [
    format_training_record(record, template=template, ...)
    for record in records
]
```

The input accepts either an `Iterator[TrainingRecord]` or a list. The output is intentionally a list because current starter datasets are small and subsequent writing/inspection needs repeated access. For much larger datasets, this is the place to introduce streaming.

### `formatted_example_to_dict`

`asdict(example)` recursively converts the dataclass to a normal dictionary. The dictionary comprehension keeps each `(key, value)` pair only when `value is not None`. It does not remove `False`, which matters for `image_exists=False`.

### `write_sft_jsonl`

`Path(path)` normalizes either a string or existing `Path`. `mkdir(parents=True, exist_ok=True)` creates missing output directories without failing if they already exist.

The loop encodes each example with compact separators, writes `"\n"`, and increments `count`. Returning the count gives CLI callers a simple completion metric.

### `convert_jsonl_to_sft`

This orchestration function composes the module’s three stages:

1. `read_jsonl` validates and yields records.
2. `format_training_records` builds examples.
3. `write_sft_jsonl` persists them.

It returns the examples after writing so the CLI can report sample details without rereading the output.

## File walkthrough: `ml/finetune/__init__.py`

This package initializer creates a stable import surface such as:

```python
from ml.finetune import TrainingPromptTemplate, format_training_record
```

### Imports

| Import | Plain meaning | Why it is needed |
|--------|---------------|------------------|
| `from ml.finetune.format_dataset import FormattedSFTExample, format_training_record, format_training_records, write_sft_jsonl` | Imports four conversion symbols | Re-exports the common record-formatting API |
| `from ml.finetune.prompt_template import ASSISTANT_PREFIX, TrainingPromptTemplate, build_training_prompt` | Imports three prompt symbols | Re-exports the common prompt-boundary API |

`__all__` lists exactly seven public names:

| Name | Public role |
|------|-------------|
| `ASSISTANT_PREFIX` | Shared answer-boundary marker |
| `FormattedSFTExample` | Model-ready record type |
| `TrainingPromptTemplate` | Reusable prompt builder |
| `build_training_prompt` | One-example convenience function |
| `format_training_record` | Single-record converter |
| `format_training_records` | Batch converter |
| `write_sft_jsonl` | Output writer |

Lower-level or orchestration symbols such as `IMAGE_TOKEN`, `formatted_example_to_dict`, and `convert_jsonl_to_sft` are intentionally not re-exported.

## File walkthrough: `ml/__init__.py`

This one-line module docstring declares the package’s purpose. Creating `ml/__init__.py` makes package intent explicit to Python tooling and gives future training, inference, and evaluation modules a common namespace.

It defines no imports, constants, classes, or functions.

## File walkthrough: `scripts/format_training_data.py`

This CLI is a thin operator-facing wrapper around `convert_jsonl_to_sft`.

### Imports

| Import | Plain meaning | Why it is needed |
|--------|---------------|------------------|
| `from __future__ import annotations` | Deferred annotations | Consistent typing behavior |
| `import argparse` | CLI parser | Defines options and help |
| `import sys` | Runtime/system access | Writes errors and extends import path |
| `from pathlib import Path` | Path abstraction | Locates repository and input |
| `from litevla.prompting import PROMPT_VERSIONS` | Imports the shared version registry | Restricts CLI choices |
| `from ml.finetune.format_dataset import convert_jsonl_to_sft` | Imports the conversion orchestrator | Performs the actual work |

### Module-level constant: `ROOT`

`ROOT = Path(__file__).resolve().parent.parent` starts from the script file, moves to `scripts/`, then to the repository root. Adding that string to `sys.path` lets direct script execution import `litevla` and `ml`.

### `_parse_args`

The function creates an `ArgumentParser` and registers:

- `--input`: Epic 105 JSONL;
- `--output`: generated SFT JSONL;
- `--prompt-version`: constrained to shared prompt versions;
- `--check-image`: optional existence reporting.

It returns `argparse.Namespace`, whose attributes match the option names with hyphens converted to underscores.

### `main`

`main` parses arguments and returns an integer process status. A missing input prints to `stderr` and returns `1`.

On success it calls `convert_jsonl_to_sft`, counts examples whose `image_exists is False`, then prints the row count, prompt version, and a concise first-sample preview. It returns `0`.

The bottom guard:

```python
if __name__ == "__main__":
    raise SystemExit(main())
```

runs only during direct execution. `SystemExit` turns the returned integer into the shell exit code.

## File walkthrough: `scripts/inspect_training_samples.py`

This script supports the human review subtask while also applying deterministic structural checks.

### Imports

| Import | Plain meaning | Why it is needed |
|--------|---------------|------------------|
| `from __future__ import annotations` | Deferred annotations | Consistent typing behavior |
| `import argparse` | CLI parser | Defines inspection options |
| `import json` | JSON decoder | Reads already-formatted SFT JSONL |
| `import sys` | Runtime/system access | Errors, path setup, exit status |
| `from pathlib import Path` | Path abstraction | Input and image resolution |
| `from litevla.actions import ACTION_NAMES, is_valid_action` | Imports shared action names and validator | Prints vocabulary and validates targets |
| `from litevla.data.schema import read_jsonl` | Imports the Epic 105 reader | Loads model-neutral input |
| `from litevla.prompting import PROMPT_VERSIONS` | Imports the prompt registry | Restricts CLI choices |
| `from ml.finetune.format_dataset import FormattedSFTExample, format_training_records` | Imports SFT type and batch formatter | Loads or creates inspectable examples |
| `from ml.finetune.prompt_template import ASSISTANT_PREFIX, IMAGE_TOKEN` | Imports structural markers | Applies prompt checks |

### Module-level constant: `ROOT`

The inspection script computes `ROOT` exactly like the conversion CLI. It supports repository imports and resolves relative image paths during filesystem checks.

### `_parse_args`

In addition to input, prompt version, and sample count, the parser provides two modes:

- `--from-sft` reads an existing converted file instead of converting input on the fly.
- `--require-images` promotes missing images from warnings to hard failures.

`--check-image` asks on-the-fly conversion to populate the `image_exists` field. It does not control whether inspection checks paths: `_check_example` always performs its own filesystem existence check. `--require-images` changes missing paths from warnings to hard issues.

### `_load_sft_jsonl`

This function opens an already-formatted file, skips blank lines, parses each JSON object, and constructs `FormattedSFTExample` explicitly.

Required keys use `raw["field"]`, which raises `KeyError` if missing, and their values are coerced with `str(...)`. Optional provenance keys use `.get`; `prompt_version` defaults to `"v1"` when absent, while `image_exists` passes through from JSON as-is. The `except KeyError` block adds file and line context before raising `ValueError`.

### `_check_example`

The function returns `(issues, warnings)`, a tuple of two string lists. Structural failures always enter `issues`. It uses `example.prompt.rstrip().endswith(ASSISTANT_PREFIX)`, allowing harmless trailing whitespace while requiring the same semantic boundary. Missing images are always checked on disk; they enter `issues` only when `require_images=True`, otherwise `warnings`.

The check:

```python
if f"{ASSISTANT_PREFIX} {example.target}" in example.prompt:
    issues.append("action already present after ASSISTANT: in prompt")
```

specifically detects answer leakage after the assistant boundary. It does not reject action names appearing in the system prompt’s allowed-action list.

### `_print_example`

Status selection prioritizes `ISSUES`, then `WARN`, then `OK`. The function prints provenance, prompt, target, and a shortened tail of `full_text`. It then prints hard issues with `!` and warnings with `~`.

The last-six-lines preview keeps the repeated system prompt from overwhelming terminal output while still showing the assistant boundary and target.

### `main`

The function validates the input path, chooses either `_load_sft_jsonl` or `read_jsonl` plus `format_training_records`, and rejects empty datasets. In `--from-sft` mode, `--prompt-version` is not used because the artifact carries its own version (or receives the loader's `v1` default).

```python
n = min(max(args.n, 1), len(examples))
```

The nested `max` prevents zero/negative review counts; `min` prevents indexing beyond the dataset.

Before the loop, the script prints the shared allowed-action list. The loop checks and prints each selected example while counting samples with issues and warnings. Its summary has the form `Summary: 10/10 samples passed format checks (0 with image warnings)`. Hard issues produce exit code `1`; warnings preserve exit code `0`.

The direct-execution guard converts that return value into the shell status just like the conversion CLI.

## Check your understanding

1. Why does batch formatting pass one `TrainingPromptTemplate` into each single-record call?
2. What is the semantic difference between `image_exists=False` and `image_exists=None`?
3. Why does `_check_example` search for `ASSISTANT: <target>` instead of rejecting any target name found in the prompt?
4. Which function should change if future datasets become too large to materialize in memory?
