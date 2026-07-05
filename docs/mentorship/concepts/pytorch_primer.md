# PyTorch Concept Primers
**Human-readable version (browser):** [`pytorch_primer.html`](pytorch_primer.html)

---

### PyTorch Datasets (`torch.utils.data.Dataset`)

#### Overview
PyTorch's `Dataset` is an abstract class representing a structured collection of data. By inheriting from it and implementing the double-underscore methods `__len__` (to return total size) and `__getitem__` (to fetch a single item by index), you tell PyTorch how to read your data. This is crucial for separating the details of how files are stored on your disk from the actual machine learning training loops.

#### Code Example
```python
import torch
from torch.utils.data import Dataset

class MockDataset(Dataset):
    def __init__(self, data_list: list[float]) -> None:
        self.data = data_list

    def __len__(self) -> int:
        return len(self.data)

    def __getitem__(self, index: int) -> dict[str, torch.Tensor]:
        # Return a dictionary containing a single numerical tensor
        return {"value": torch.tensor(self.data[index], dtype=torch.float32)}
```

#### Use-Case Scenarios
* **General Use-Case:** Loading images, audio samples, or text data from disk and wrapping them into PyTorch dictionary inputs.
* **Robotics & VLA Use-Case:** Loading robot demonstration logs, matching camera PNG files to action commands, and returning them dynamically on demand.

#### When to Use vs. When NOT to Use
* **Choose this when:** You are training models using PyTorch and have structured datasets that can be accessed by an index lookup.
* **Avoid this when:** You are streaming real-time network logs or reinforcement learning environments where inputs are generated on-the-fly based on immediate policy feedbacks (use custom stream loaders or environment steps instead).

---

### PyTorch DataLoaders (`torch.utils.data.DataLoader`)

#### Overview
While a `Dataset` retrieves a single item at a time, a `DataLoader` is the engine that orchestrates the training stream. It automatically handles shuffling (randomizing item order), batching (grouping multiple items together), and multi-processing (using background CPU worker threads to load images in parallel while the GPU handles training).

#### Code Example
```python
from torch.utils.data import DataLoader

dataset = MockDataset([1.0, 2.0, 3.0, 4.0])
# Create a loader that groups items into batches of 2 and shuffles them
loader = DataLoader(dataset, batch_size=2, shuffle=True, num_workers=2)

for batch in loader:
    # batch["value"] is a stacked tensor of shape [2]
    print("Batch values:", batch["value"])
```

#### Use-Case Scenarios
* **General Use-Case:** Speeding up deep learning training by pre-fetching batches in the background on CPU threads so the GPU never remains idle.
* **Robotics & VLA Use-Case:** Feeding frames and commands into SmolVLM fine-tuning loops. Using `num_workers > 0` ensures image file reads do not block GPU training updates.

#### When to Use vs. When NOT to Use
* **Choose this when:** You are training PyTorch models and want automated batching, shuffling, and multi-threaded loading.
* **Avoid this when:** You are doing single-sample inference (predicting a robot action from a single camera frame), which requires simple forward passes without batch loaders.

---

### Dataset Collation and `default_collate`

#### Overview
Collation is the process of merging a list of individual samples (retrieved from `__getitem__`) into a single aligned training batch. PyTorch's `default_collate` automatically stacks tensors, converts numpy arrays to tensors, lists strings, and copies dictionary structures. However, it fails if it encounters raw `PIL.Image.Image` objects or mixed types (like `NoneType`), which require pre-conversion.

#### Code Example
```python
import numpy as np
import torch
from torch.utils.data\_utils.collate import default_collate

# A batch list returned by dataset __getitem__ loops
sample_batch = [
    {"image": np.zeros((3, 224, 224), dtype=np.uint8), "action": "STOP"},
    {"image": np.ones((3, 224, 224), dtype=np.uint8), "action": "MOVE_FORWARD"}
]

# default_collate converts the numpy arrays into a single stacked torch tensor
collated_batch = default_collate(sample_batch)
print("Stacked Image Tensor Shape:", collated_batch["image"].shape) # Returns [2, 3, 224, 224]
```

#### Use-Case Scenarios
* **General Use-Case:** Formatting lists of image tensors and text tags into numerical batches for GPU model ingestion.
* **Robotics & VLA Use-Case:** Stacking multiple OpenCV camera frames and navigation instructions. If a frame is a raw PIL Image, we must use a transform (like `np.array`) to prevent collator type errors.

#### When to Use vs. When NOT to Use
* **Choose this when:** Your dataset items consist of standard types (tensors, numpy arrays, strings) and can be stacked directly by index.
* **Avoid this when:** Your batch items have varying dimensions (e.g., text sentences of different lengths), which require a custom `collate_fn` to pad sequences with special padding tokens.
