# Tutorial: The PyTorch Dataset Loader
**Files Covered:** [`litevla/data/loader.py`](file:///C:/Projects/Lite-VLA/litevla/data/loader.py)  
**Epic Milestone:** [Epic 105 / VLA-06: Dataset Generation, Labeling, and Validation]  
**Human-readable version (browser):** [`dataset_loader.html`](dataset_loader.html)

---

## 1. Goal & Objective
The goal of the dataset loader is to provide a memory-efficient PyTorch interface that loads dataset records and JPEG/PNG frames on demand, applies visual transformations, and formats them into aligned training dictionaries.

---

## 2. Why We Need It
Deep learning training loops feed on batches of image-action pairs. However, loading thousands of images into RAM during initialization will trigger Out-Of-Memory (OOM) crashes. We need a system that utilizes [lazy loading](../concepts/pytorch_primer.md#datasets) to read images from disk only when requested, and uses PyTorch's multi-threaded [DataLoader](../concepts/pytorch_primer.md#dataloaders) to pre-fetch and batch training items concurrently.

---

## 3. How to Start Thinking About It
When designing the training dataloader:
1. **Extend the base contract:** Subclass PyTorch's [Dataset](../concepts/pytorch_primer.md#datasets) class.
2. **Implement len:** Define `__len__` to return the total size of the JSONL metadata rows.
3. **Implement item retrieval:** Define `__getitem__` to load a single PNG image frame on demand, convert it to RGB mode, and apply transforms.
4. **Standardize data:** Return a structured dictionary mapping keys to values (ID, image, instruction, action).

---

## 4. Imports Explained

| Import Statement | What it is | Why it is used here | Concept Link |
|------------------|------------|---------------------|--------------|
| `from __future__ import annotations` | Postponed type hints | Solves self-referencing classes in parameter declarations. | [Annotations](../concepts/python_primer.md#annotations) |
| `from pathlib import Path` | Path resolution utility | Resolves relative file paths into absolute locations on the host drive. | [Pathlib](../concepts/python_primer.md#pathlib) |
| `from typing import Any, Callable` | Type checking utilities | Annotates transforms (`Callable`) and dictionary keys (`Any`). | N/A |
| `from litevla.data.schema import REPO_ROOT` | Global path constant | Serves as the fallback project root directory. | N/A |
| `from litevla.data.schema import read_jsonl` | File reader generator | Reads training metadata rows line-by-line using `yield`. | [Generators](../concepts/python_primer.md#generators) |
| `from torch.utils.data import Dataset` | Base dataset class | Abstract class representing a collection of items. | [Datasets](../concepts/pytorch_primer.md#datasets) |

---

## 5. Code Walkthrough

### Type Aliases
#### `ImageTransform`
* **Intent:** Defines the expected type signature for image preprocessing callables.
* **Implementation:**
  ```python
  ImageTransform = Callable[[Any], Any]
  ```

---

### Custom Classes
#### `LiteVLADataset`
* **Intent:** Subclasses PyTorch's abstract dataset helper to feed batches to the model.
* **Implementation:**
  ```python
  class LiteVLADataset(Dataset):
      def __init__(
          self,
          jsonl_path: str | Path,
          *,
          repo_root: Path | None = None,
          transform: ImageTransform | None = None,
      ) -> None:
          self.jsonl_path = Path(jsonl_path)
          self.repo_root = repo_root or REPO_ROOT
          self.transform = transform
          self.records: list[TrainingRecord] = list(read_jsonl(self.jsonl_path))
  ```
* **Why it's chosen:** Inherits PyTorch's native loader contract so that it can be passed directly to PyTorch DataLoaders.
* **Connections:** Instantiated in training scripts and passed to `torch.utils.data.DataLoader`.

---

### Functions in `LiteVLADataset`

#### `__len__()`
* **Intent:** Returns the total size of the dataset.
* **Contract:**
  * Inputs: None.
  * Outputs: `int` (total record count).
* **Connections:** Called internally by PyTorch's sampler to distribute indexes.

#### `resolve_image_path(record: TrainingRecord)`
* **Intent:** Resolves relative image paths.
* **Contract:**
  * Inputs: `TrainingRecord` instance.
  * Outputs: `Path` absolute location.
* **Connections:** Called inside `__getitem__` before loading files.

#### `__getitem__(index: int)`
* **Intent:** Retrieves the image and instruction at a specific index.
* **Contract:**
  * Inputs: `int` index.
  * Outputs: `dict[str, Any]` (ID, loaded PIL Image, instruction text, action command).
* **Why it's chosen:** Implements lazy loading. Reads the PNG file on demand, converts it to RGB, and returns it.
* **Connections:** Called automatically by PyTorch `DataLoader` worker threads to build training batches.
