# Tutorial: Understanding Lite-VLA Data Schemas & File Layouts
**Files Covered:** [`litevla/data/schema.py`](file:///C:/Projects/Lite-VLA/litevla/data/schema.py), [`litevla/data/episode.py`](file:///C:/Projects/Lite-VLA/litevla/data/episode.py)  
**Epic Milestone:** [Epic 105 / VLA-06: Dataset Generation, Labeling, and Validation]  
**Human-readable version (browser):** [`schema_and_episode.html`](schema_and_episode.html)

---

## 1. Goal & Objective
The goal of the schema and episode modules is to define a strict, validated data format that maps physical robot inputs (camera image frames, user goals) and outputs (speed commands) into structured, read-only formats for our ML pipelines.

---

## 2. Why We Need It
During fine-tuning, the model consumes thousands of training records. In Python, raw dictionaries are loose, allowing silent typos (like writing `"img_path"` instead of `"image_path"`) or invalid speed commands to go unnoticed. Without this schema gate, invalid actions or missing files would cause GPU training processes to crash after running for hours, wasting computational resources and making debugging difficult. We need a hard boundary that fails fast at the ingestion stage.

---

## 3. How to Start Thinking About It
When designing a robust data pipeline:
1. **Define the shape:** First, define exactly what variables are required (path to image, the prompt text, the navigation action word, and timing metadata).
2. **Build a validator:** Read standard JSON schema files to check raw dictionaries before running any parsing logic.
3. **Parse into structured objects:** Copy the validated dictionaries into read-only containers ([dataclasses](../concepts/python_primer.md#dataclasses)) so that they are guaranteed to remain unchanged throughout downstream loaders.
4. **Stream memory-efficiently:** Write file readers using [generators](../concepts/python_primer.md#generators) so the system reads large dataset files line-by-line rather than trying to load the entire file into RAM at once.

---

## 4. Imports Explained

| Import Statement | What it is | Why it is used here | Concept Link |
|------------------|------------|---------------------|--------------|
| `from __future__ import annotations` | Postponed type hints | Prevents `NameError` exceptions when classes refer to themselves in type hints. | [Annotations](../concepts/python_primer.md#annotations) |
| `import json` | Standard JSON parser | Used to read and write raw dictionary text lines in JSONL format. | N/A |
| `from dataclasses import dataclass, field` | Boilerplate helper | Defines the structured, read-only data structures for records. | [Dataclasses](../concepts/python_primer.md#dataclasses) |
| `from pathlib import Path` | Cross-platform file paths | Handles directory paths, resolving slashes correctly on Windows and Linux. | [Pathlib](../concepts/python_primer.md#pathlib) |
| `from typing import Any, Iterator` | Type annotation tools | Declares return types for dictionaries (`Any`) and generators (`Iterator`). | N/A |
| `import jsonschema` | Draft schema validator | Checks that incoming dictionaries contain all mandatory variables. | N/A |
| `from jsonschema import Draft202012Validator` | Strict validator class | Implements the official Draft-2020 JSON Schema validator engine. | N/A |
| `from litevla.actions import parse_action` | Action word validator | Converts string actions (e.g. `"MOVE_FORWARD"`) to verified system commands. | N/A |

---

## 5. Code Walkthrough

### Global Constants
#### `REPO_ROOT`
* **Intent:** Resolves the absolute parent directory of the active Lite-VLA repository.
* **Implementation:**
  ```python
  REPO_ROOT = Path(__file__).resolve().parents[2]
  ```
* **Why it's chosen:** Resolves directories relative to the active file's location on disk, ensuring absolute paths are computed correctly on other developers' machines.
* **Connections:** Shared across all data loading utilities to locate the `data/` folder.

#### `RECORD_SCHEMA_PATH`
* **Intent:** Absolute path to the JSON Schema contract for training records.
* **Implementation:**
  ```python
  RECORD_SCHEMA_PATH = REPO_ROOT / "data" / "schema" / "record.schema.json"
  ```
* **Why it's chosen:** Tells the validator exactly where to find the contract file.

#### `FIXTURES_PATH`
* **Intent:** Path to sample mock dataset files for testing.

---

### Custom Classes
#### `TrainingRecord`
* **Intent:** Represents a single image-prompt-action pair for training.
* **Implementation:**
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
* **Data Contract:** Holds type-checked strings and optional metadata dictionaries. `frozen=True` enforces read-only access.
* **Why it's chosen:** Protects data integrity during multi-threaded training.
* **Connections:** Constructed by `parse_training_record`, used by `LiteVLADataset` in the loader module.

#### `RecordSchemaError`
* **Intent:** Custom exception raised when validation fails.
* **Why it's chosen:** Allows training scripts to catch and handle format issues specifically.

---

### Functions in `schema.py`

#### `load_record_schema()`
* **Intent:** Reads the validation schema file from disk.
* **Contract:** 
  * Inputs: None.
  * Outputs: `dict[str, Any]` (parsed JSON rules).
* **Connections:** Called by `validate_record_dict` during parsing.

#### `validate_record_dict(raw: dict[str, Any])`
* **Intent:** Validates a raw dictionary against the JSON schema.
* **Contract:** 
  * Inputs: `raw` dict, optional `schema` dict.
  * Outputs: `None` (raises `RecordSchemaError` if invalid).
* **Why it's chosen:** Separates raw schema validation from action validation.

#### `parse_training_record(raw: dict[str, Any])`
* **Intent:** Converts a raw dict into a validated `TrainingRecord` object.
* **Contract:**
  * Inputs: `raw` dict.
  * Outputs: `TrainingRecord` instance.
* **Why it's chosen:** Gatekeeper function. If validation or action parsing fails, it stops execution immediately.
* **Connections:** Main parsing method called during file reading.

#### `training_record_to_dict(record: TrainingRecord)`
* **Intent:** Converts a `TrainingRecord` back into a standard dictionary.
* **Contract:**
  * Inputs: `TrainingRecord` object.
  * Outputs: `dict[str, Any]` serialized dictionary.
* **Connections:** Called by `write_jsonl` to prepare records for saving.

#### `read_jsonl(path: str | Path)`
* **Intent:** Streams validated records from a JSONL file line-by-line.
* **Contract:**
  * Inputs: `path` to file.
  * Outputs: `Iterator[TrainingRecord]` (generator yielding records).
* **Why it's chosen:** Uses `yield` to load files sequentially, saving RAM.
* **Connections:** Called by `LiteVLADataset` to populate its record catalog.

#### `write_jsonl(path: str | Path, records: Iterator[TrainingRecord])`
* **Intent:** Saves records into a compact JSONL file.
* **Contract:**
  * Inputs: target file path, iterator of records.
  * Outputs: `int` (total row count written).
* **Connections:** Called by dataset builder scripts to write the train/val splits.

---

### Functions in `episode.py`

#### `validate_episode_dict(raw: dict[str, Any])`
* **Intent:** Validates raw simulator episode metadata against its JSON schema.
* **Connections:** Called by capture scripts when saving new episodes.

#### `init_raw_episode(...)`
* **Intent:** Sets up a new episode folder on disk with a default metadata file.
* **Contract:**
  * Inputs: directory paths, goal instruction, capture frequencies.
  * Outputs: `Path` to the created episode folder.
* **Why it's chosen:** Guarantees that every capture script creates a standard, well-formed directory structure.
* **Connections:** Called by simulator recording interfaces during collection runs.
