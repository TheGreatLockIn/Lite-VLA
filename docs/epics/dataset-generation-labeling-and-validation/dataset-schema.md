# Tutorial: Understanding Lite-VLA Data Schema & File Layout
**Files Covered:** [`litevla/data/schema.py`](file:///C:/Projects/Lite-VLA/litevla/data/schema.py)  
**Epic Milestone:** [Epic 105 / VLA-06: Dataset Generation, Labeling, and Validation]  
**Human-readable version (browser):** [`dataset-schema.html`](dataset-schema.html)

---

## 1. Goal & Objective
The goal of the schema module is to define a strict, validated data format that maps physical robot inputs (camera image frames, user goals) and outputs (speed commands) into structured, read-only formats for our ML pipelines.

---

## 2. Why We Need It
During fine-tuning, the model consumes thousands of training records. In Python, raw dictionaries are loose, allowing silent typos (like writing `"img_path"` instead of `"image_path"`) or invalid speed commands to go unnoticed. Without this schema gate, invalid actions or missing files would cause GPU training processes to crash after running for hours, wasting computational resources and making debugging difficult. We need a hard boundary that fails fast at the ingestion stage.

---

## 3. How to Start Thinking About It (AI Developer Thought Process)
When designing this code, I thought about the developer's sequential decision-making process:

1. **A loose dictionary is too risky:** "First, I thought about how we need to represent a single dataset item. A simple Python dictionary is too loose because we can write typos in the keys, and the program will continue running anyway. I need to define a strict data schema."
2. **Dataclass for safety:** "Then, I wanted to lock down mutations so that training records cannot be accidentally changed by loaders during training. So, I decided to use a Python `@dataclass` with `frozen=True`."
3. **JSON Schema for checking text structures:** "After that, I needed to check raw JSON data before loading it into memory. So, I decided to write JSON schema blueprint files and validate raw dictionaries using `jsonschema`'s Draft 2020-12 validator before converting them to dataclass objects."
4. **Action parsing validation:** "Next, I realized that checking schemas only validates strings, not the specific action values. So, I decided to import `parse_action` to make sure each action string maps to a valid system steering word (like `MOVE_FORWARD`)."
5. **Memory-efficient loading:** "Finally, when writing the file reader, I realized that datasets could have 10,000+ lines. Reading the entire file into a list would hog memory. Therefore, I chose to use Python's `yield` generator syntax so that we only load one record into memory at a time."

---

## 4. Imports & Global Constants Explained

### Imports Table

| Import Statement | What it is | Why it is used here | Concept Link |
|------------------|------------|---------------------|--------------|
| `from __future__ import annotations` | Postponed type hints | Solves self-referencing classes in type hints. | [Annotations](../../concepts/python_primer.md#postponed-annotations) |
| `import json` | Standard JSON parser | Used to read and write raw JSON/JSONL rows. | [JSON Serialization](../../concepts/python_primer.md#json-serialization) |
| `from dataclasses import dataclass, field` | Boilerplate helper | Defines the structured, read-only data structures for records. | [Dataclasses](../../concepts/python_primer.md#dataclasses-and-fields) |
| `from pathlib import Path` | Cross-platform file paths | Handles directory paths, resolving slashes correctly on Windows and Linux. | [Pathlib](../../concepts/python_primer.md#pathlib-file-resolution) |
| `from typing import Any, Iterator` | Type annotation tools | Declares return types for dictionaries (`Any`) and generators (`Iterator`). | [Typing](../../concepts/python_primer.md#typing-and-type-checking) |
| `import jsonschema` | Draft schema validator | Checks that incoming dictionaries contain all mandatory variables. | [JSON Schema](../../concepts/python_primer.md#json-schema-validation) |
| `from jsonschema import Draft202012Validator` | Strict validator class | Implements the official Draft-2020 JSON Schema validator engine. | [JSON Schema](../../concepts/python_primer.md#json-schema-validation) |
| `from litevla.actions import parse_action` | Action word validator | Converts string actions (e.g. `"MOVE_FORWARD"`) to verified system commands. | N/A |

### Global Constants

#### `REPO_ROOT`
* **What it is:** Resolves the absolute parent directory of the active Lite-VLA repository.
* **Why it is defined here:** Resolves directories relative to the active file's location on disk, ensuring absolute paths are computed correctly on other developers' machines.
* [Pathlib Concept Reference](../../concepts/python_primer.md#pathlib-file-resolution)

#### `RECORD_SCHEMA_PATH`
* **What it is:** Absolute path to the JSON Schema contract for training records.
* **Why it is defined here:** Tells the validator exactly where to find the contract file.

#### `FIXTURES_PATH`
* **What it is:** Path to sample mock dataset files for testing.

---

## 5. Class Data-Flow Diagrams

### `TrainingRecord` Ingestion & Export Flow

```mermaid
flowchart TD
    Raw[Raw JSONL Text Line] -->|read_jsonl| Parse[json.loads]
    Parse -->|validate_record_dict| SchemaCheck[Draft202012Validator]
    SchemaCheck -->|parse_action| ValidAct[parse_action]
    ValidAct -->|Construct| TR[TrainingRecord Dataclass]
    TR -->|training_record_to_dict| Serialized[Serialized Python Dict]
    Serialized -->|write_jsonl| OutFile[Output JSONL File on Disk]

    style TR fill:#FAF8F5,stroke:#B8602A,stroke-width:2px
```

---

## 6. Detailed Code Walkthrough

### Custom Classes

#### `TrainingRecord`
* **Intent:** Represents a single image-prompt-action pair for training.
* **Code Snippet:**
  ```python
  @dataclass(frozen=True)
  class TrainingRecord:
      image_path: str
      instruction: str
      action: str
      timestamp: str
      source: str
      id: str | None = None
      episode_id: str | None = None
      metadata: dict[str, Any] = field(default_factory=dict)
  ```
* **Data Contract:** 
  * Inputs: mandatory strings (`image_path`, `instruction`, `action`, `timestamp`, `source`), optional IDs (`id`, `episode_id`), and an optional `metadata` dictionary.
  * Outputs: An immutable record instance.
* **Why it's written this way:** `frozen=True` guarantees that once a record is parsed, its values cannot be modified during training. `field(default_factory=dict)` is used because standard mutable default parameters like `metadata: dict = {}` are shared across all class instances in Python, which leads to memory leaks.
* **System Connections:** Created by `parse_training_record`, read by the `LiteVLADataset` loader.
* [Dataclasses Concept Reference](../../concepts/python_primer.md#dataclasses-and-fields)

#### `RecordSchemaError`
* **Intent:** Custom exception raised when validation fails.
* **Why it's written this way:** Inherits from `ValueError`. This allows training scripts to catch and handle schema validation errors specifically.
* [Custom Exceptions Concept Reference](../../concepts/python_primer.md#custom-exceptions)

---

### Functions in `schema.py`

#### `record_schema_path()`
* **Intent:** Computes the path to the record schema file.
* **Data Contract:** Inputs: None. Outputs: `Path`.

#### `load_record_schema()`
* **Intent:** Reads and parses the validation schema file from disk.
* **Data Contract:** Inputs: None. Outputs: `dict[str, Any]`.
* **Why it's written this way:** Checks if the file exists using `is_file()` and raises a descriptive `FileNotFoundError` if missing.

#### `_format_validation_error(error)`
* **Intent:** Converts a validation error into a readable path string (e.g. `metadata -> world: ...`).
* **Data Contract:** Inputs: `jsonschema.ValidationError`. Outputs: `str`.

#### `validate_record_dict(raw, *, schema)`
* **Intent:** Validates a raw dictionary against the JSON schema rules.
* **Data Contract:** Inputs: `raw` dict, optional `schema` dict. Outputs: None (raises `RecordSchemaError` if invalid).
* **Why it's chosen:** Uses `Draft202012Validator.iter_errors` to collect all violations, formats them using `_format_validation_error`, and joins them into a single error string.
* [JSON Schema Concept Reference](../../concepts/python_primer.md#json-schema-validation)

#### `parse_training_record(raw, *, schema)`
* **Intent:** Converts a raw dict into a validated `TrainingRecord` object.
* **Data Contract:** Inputs: `raw` dict, optional `schema`. Outputs: `TrainingRecord`.
* **Why it's chosen:** Gatekeeper function. Converts raw actions into verified steering commands using `parse_action`.

#### `training_record_to_dict(record)`
* **Intent:** Converts a `TrainingRecord` back into a dictionary for JSON output.
* **Data Contract:** Inputs: `TrainingRecord`. Outputs: `dict[str, Any]`.

#### `read_jsonl(path, *, schema)`
* **Intent:** Streams validated records from a JSONL file line-by-line.
* **Data Contract:** Inputs: `path` to file, optional `schema`. Outputs: `Iterator[TrainingRecord]` generator.
* **Why it's chosen:** Uses `yield` to load files sequentially, keeping memory usage constant.
* [Generators Concept Reference](../../concepts/python_primer.md#generators-and-yield)

#### `write_jsonl(path, records)`
* **Intent:** Saves records into a compact JSONL file.
* **Data Contract:** Inputs: target file path, iterator of records. Outputs: `int` (total row count written).

---

## 7. Practical Engineering Context

### Executive Summary
VLA-41 owns the **processed training record contract** for supervised fine-tuning: one UTF-8 JSONL row per image-instruction-action example under `data/processed/<version>/`. Raw simulation logs (VLA-42) use a different on-disk shape; only rows validated against `record.schema.json` and Epic 103 `parse_action()` enter training. This story is the schema gate every downstream builder, reviewer, validator, and loader depends on.

### API Contract & Data Flow
```text
Raw capture (VLA-42)                    Processed SFT (VLA-41)
─────────────────────                   ────────────────────────
raw/episodes/<id>/commands.jsonl   ──>  processed/v0.1.0/train.jsonl
raw/episodes/<id>/frames/*.png     ──>       (image_path + instruction + action)
reference_images/manifest.json     ──>  (via VLA-43 builder)
```

### Naive Approach vs Chosen Approach
- **Naive approach**: Store data in simple CSV tables. Breaks because nested metadata is poorly structured and streaming into PyTorch is slow.
- **Chosen approach**: Newline-delimited JSON (JSONL) combined with a strict JSON Schema and frozen Python dataclass. Fast, appendable, and validates at boundaries.

### ADR Log Summary
- **ADR (VLA-169)**: Newline-delimited JSON (JSONL) chosen for dataset records; human review uses CSV spreadsheets.
- **ADR (VLA-170)**: Discrete action vocabulary is hardcoded in the schema, ensuring strict synchronization with Epic 103 commands.

### Verification Patterns & Failure Modes
- Command to run: `pytest tests/test_dataset_schema.py -q`
- Common error: `RecordSchemaError` due to a typo or incorrect action value. Verify path separator forms and correct values using the validation report tool.

### Related
- [action-schema.md](../action-interface-parser-and-safety-layer/action-schema.md)
- [simulation-data-capture.md](simulation-data-capture.md)
- [synthetic-starter-dataset.md](synthetic-starter-dataset.md)
- [labeling-workflow.md](labeling-workflow.md)
- [dataset-validation.md](dataset-validation.md)
- [dataset-loader.md](dataset-loader.md)
- [dataset-versioning.md](dataset-versioning.md)
