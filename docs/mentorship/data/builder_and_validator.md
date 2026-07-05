# Tutorial: Dataset Building and Quality Validation
**Files Covered:** [`litevla/data/builder.py`](file:///C:/Projects/Lite-VLA/litevla/data/builder.py), [`litevla/data/validator.py`](file:///C:/Projects/Lite-VLA/litevla/data/validator.py)  
**Epic Milestone:** [Epic 105 / VLA-06: Dataset Generation, Labeling, and Validation]  
**Human-readable version (browser):** [`builder_and_validator.html`](builder_and_validator.html)

---

## 1. Goal & Objective
The goal of the dataset builder and validator is to compile raw simulation steps (PNG visual frames and command streams) into aligned training/validation pairs, augment them with visual variations, partition them, and validate the final dataset layout to guarantee correct formats.

---

## 2. Why We Need It
Training vision-language models requires structured, diverse datasets. Collecting episodes generates irregular timestamps. We need a system that automatically aligns frames with robot actions. Furthermore, training on a few static images causes overfitting. The builder applies data augmentations to introduce variety. Finally, we need a validator to verify there are no missing files or duplicate records before launching training runs.

---

## 3. How to Start Thinking About It
When designing the dataset compilation and quality checks:
1. **Timestamp Alignment:** Find the closest speed command matching each camera frame's recording time.
2. **Apply Image Augmentations:** Introduce light variations, cropping, blurs, and JPEG compressions.
3. **Partition Cleanly:** Shuffle deterministically and split into non-overlapping training and validation splits.
4. **Automate Checks:** Scan the output folder to verify all PNG paths exist and that action command classes are balanced.

---

## 4. Imports Explained

| Import Statement | What it is | Why it is used here | Concept Link |
|------------------|------------|---------------------|--------------|
| `import hashlib` | Hash digest builder | Generates unique hashes to seed local random generators. | N/A |
| `import json` | Standard JSON utility | Reads JSON files (like the reference image manifest). | N/A |
| `import random` | Random number generator | Shuffles the records list and creates variations. | N/A |
| `import re` | Regular expressions parser | Extracts sim stamp values from frame filenames. | N/A |
| `from pathlib import Path` | Path resolution utility | Resolves relative image locations across platforms. | [Pathlib](../concepts/python_primer.md#pathlib) |
| `from PIL import Image` | Python Imaging Library | Opens and saves visual frames. | N/A |
| `from PIL import ImageEnhance, ImageFilter` | Image filter enhancers | Alters brightness, contrast, sharping, and blurs. | N/A |
| `import numpy as np` | Multi-dimensional arrays | Performs visual matrix adjustments and handles noise overlays. | N/A |
| `from litevla.data.schema import TrainingRecord` | Dataclass definition | Creates type-safe records for the output files. | [Dataclass](../concepts/python_primer.md#dataclasses) |

---

## 5. Code Walkthrough

### Global Constants
#### `DEFAULT_MAX_VARIANTS_PER_IMAGE`
* **Intent:** Limits the number of augmented variations generated per reference image.
* **Why it's chosen:** Keeps the dataset size manageable and prevents a single pose from dominating training.

#### `FRAME_STAMP_RE`
* **Intent:** Matches frame filenames (e.g. `12_340000000.png`) to extract simulation seconds and nanoseconds.

---

### Functions in `builder.py`

#### `parse_frame_stamp(filename: str)`
* **Intent:** Parse file timestamps.
* **Contract:**
  * Inputs: `str` filename.
  * Outputs: `tuple[int, int] | None` (seconds, nanoseconds).
* **Connections:** Called during episode parsing to determine the frame's timeline offset.

#### `_action_at_sim_time(commands, sim_ns)`
* **Intent:** Finds the latest velocity command that happened at or before the camera frame was captured.
* **Contract:**
  * Inputs: `Sequence[dict]`, `int` (simulation nanoseconds).
  * Outputs: `dict | None` (closest matched command dictionary).
* **Connections:** Internal helper used in `records_from_raw_episode`.

#### `records_from_raw_episode(episode_dir)`
* **Intent:** Compiles and labels raw simulation runs.
* **Contract:**
  * Inputs: `Path` episode directory.
  * Outputs: `tuple[list[TrainingRecord], int]` (records list, row count).
* **Why it's chosen:** Walks through the captured frames directory, aligns them to ROS commands, and builds record instances.
* **Connections:** Called by `build_starter_dataset` to collect simulator training data.

#### `_apply_augmentation(image, variant, rng)`
* **Intent:** Generates visual variants of reference photos to prevent overfitting.
* **Contract:**
  * Inputs: PIL `Image`, `int` variant count, local `random.Random` instance.
  * Outputs: Augmented PIL `Image`.
* **Why it's chosen:** Uses a local seed generator to produce reproducible visual noise and cropping.
* **Connections:** Called by `augment_reference_records`.

#### `split_records(records, val_ratio, seed)`
* **Intent:** Shuffles and partitions data into train/val sets.
* **Contract:**
  * Inputs: list of records, float ratio, int random seed.
  * Outputs: `tuple[list[TrainingRecord], list[TrainingRecord]]` (train, val splits).
* **Why it's chosen:** Uses `random.Random(seed)` locally to prevent global state conflicts.
* **Connections:** Called by `build_starter_dataset` before writing the output files.

---

### Functions in `validator.py`

#### `validate_dataset(...)`
* **Intent:** Audits a compiled dataset JSONL file for structural issues.
* **Contract:**
  * Inputs: dataset path, optional check flags.
  * Outputs: `DatasetValidationReport` object.
* **Why it's chosen:** Scans all lines in the output JSONL file, verifies file existence of image paths on disk, checks for duplicate IDs, and raises warning issues on class imbalances.
* **Connections:** Invoked by CI checks and training starter scripts to check dataset health.
