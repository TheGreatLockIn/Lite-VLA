# PyTorch Concept Primers
**Human-readable version (browser):** [`pytorch_primer.html`](pytorch_primer.html)

---

## Navigation
* [PyTorch Datasets](#pytorch-datasets)
* [PyTorch DataLoaders](#pytorch-dataloaders)
* [Dataset Collation](#dataset-collation)
* [PyTorch Tensors](#pytorch-tensors)

---

### PyTorch Datasets

#### Overview
PyTorch's `Dataset` (from `torch.utils.data`) is an abstract class representing a structured collection of data. By inheriting from it and implementing the double-underscore methods `__len__` (to return total size) and `__getitem__` (to fetch a single item by index), you tell PyTorch how to read your data. This separates how your files are stored on your hard drive from the actual machine learning training loops.
* `__init__(self)`: Stores catalog paths, roots, and transformations.
* `__len__(self)`: Returns total number of rows.
* `__getitem__(self, index)`: Performs the file resolution and reads raw files (e.g. images) on-demand (lazy loading).

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
        return {"value": torch.tensor(self.data[index], dtype=torch.float32)}
```

#### Use-Case Scenarios
* **General Use-Case:** Loading images, audio samples, or text data from disk and wrapping them into PyTorch dictionary inputs.
* **Robotics & VLA Use-Case:** Loading robot demonstration logs, matching camera PNG files to action commands, and returning them dynamically on demand.

#### When to Use vs. When NOT to Use
* **Choose this when:** You are training models using PyTorch and have structured datasets that can be accessed by an index lookup.
* **Avoid this when:** You are streaming real-time network logs or reinforcement learning environments where inputs are generated on-the-fly based on immediate policy feedbacks.

---

### PyTorch DataLoaders

#### Overview
While a `Dataset` retrieves a single item at a time, a `DataLoader` (from `torch.utils.data`) is the engine that orchestrates the training stream. It automatically handles shuffling (randomizing item order), batching (grouping multiple items together), and multi-processing (using background CPU worker threads to load images in parallel).
* `batch_size`: The number of items to group together in a single step (e.g., `batch_size=8`).
* `shuffle`: Set to `True` during training to randomize data order, preventing the model from memorizing the sequence of episodes.
* `num_workers`: The number of CPU processes spawned to load data. Setting `num_workers > 0` allows workers to load images in parallel while the GPU handles model updates.
* `pin_memory`: Set to `True` to copy tensors to CUDA pinned memory, speeding up transfers to the GPU.
* `drop_last`: Set to `True` to drop the last incomplete batch if the dataset size is not divisible by the batch size.

#### Code Example
```python
from torch.utils.data import DataLoader

dataset = MockDataset([1.0, 2.0, 3.0, 4.0])
loader = DataLoader(
    dataset,
    batch_size=2,
    shuffle=True,
    num_workers=2,
    pin_memory=True,
    drop_last=True
)

for batch in loader:
    print("Batch values tensor:", batch["value"])
```

#### Use-Case Scenarios
* **General Use-Case:** Speeding up deep learning training by pre-fetching batches in the background on CPU threads so the GPU never remains idle.
* **Robotics & VLA Use-Case:** Feeding frames and commands into SmolVLM fine-tuning loops. Using `num_workers > 0` ensures image file reads do not block GPU training updates.

#### When to Use vs. When NOT to Use
* **Choose this when:** You are training PyTorch models and want automated batching, shuffling, and multi-threaded loading.
* **Avoid this when:** You are doing single-sample inference (predicting a robot action from a single camera frame), which requires simple forward passes without batch loaders.

---

### Dataset Collation

#### Overview
Collation is the process of merging a list of individual samples (retrieved from `__getitem__`) into a single aligned training batch. PyTorch's `default_collate` automatically stacks tensors, converts numpy arrays to tensors, lists strings, and copies dictionary structures. However, it fails if it encounters raw `PIL.Image.Image` objects or mixed types (like `NoneType`), which require pre-conversion.
* `default_collate(batch_list)`: The default function that stacks lists of dictionaries into dictionary batches.
* If your dataset contains raw PIL Images, `default_collate` throws:
  `TypeError: default_collate: batch must contain tensors, numpy arrays... found <class 'PIL.Image.Image'>`
  To resolve this, we pass a `transform` function (like `np.array` or `transforms.ToTensor()`) to convert the PIL Image to a numerical matrix before collation occurs.

#### Code Example
```python
import numpy as np
import torch
from torch.utils.data._utils.collate import default_collate

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
* **Robotics & VLA Use-Case:** Stacking multiple OpenCV camera frames and navigation instructions. If a frame is a raw PIL Image, we must use a transform to prevent collator type errors.

#### When to Use vs. When NOT to Use
* **Choose this when:** Your dataset items consist of standard types (tensors, numpy arrays, strings) and can be stacked directly by index.
* **Avoid this when:** Your batch items have varying dimensions (e.g., text sentences of different lengths), which require a custom `collate_fn` to pad sequences with special padding tokens.

---

### PyTorch Tensors

#### Overview
A PyTorch `Tensor` is a multi-dimensional matrix containing elements of a single data type. It is very similar to a NumPy `ndarray`, but can run on a GPU to accelerate computing.
* `torch.tensor(data)`: Constructs a tensor from a list, tuple, or numpy array.
* `dtype`: Specifies the data type (e.g. `torch.float32` for model weights, `torch.long` (int64) for category indices and token labels).
* **Shape stacking:** PyTorch groups multiple individual tensors of shape `[C, H, W]` (channels, height, width) into a single batch tensor of shape `[B, C, H, W]` (batch size, channels, height, width) using stacking operations during collation.

#### Code Example
```python
import torch

# Create a float tensor representing model weights
weights = torch.tensor([0.25, 0.5, 0.75], dtype=torch.float32)

# Create a long (int64) tensor representing action token IDs
token_ids = torch.tensor([102, 5003, 103], dtype=torch.long)
```

#### Use-Case Scenarios
* **General Use-Case:** Performing high-speed matrix multiplications, representing layers of neural networks, and computing backpropagation gradients.
* **Robotics & VLA Use-Case:** Stacking visual frame matrices and steering action lists into numerical matrices to feed into model input layers.

#### When to Use vs. When NOT to Use
* **Choose this when:** You are loading inputs into a deep learning model, training neural network layers, or running GPU-accelerated mathematical operations.
* **Avoid this when:** Dealing with standard file saving, network sockets, or string parsing, which should use native Python types instead.
