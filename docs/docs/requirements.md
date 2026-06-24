# Python dependencies

This document explains Lite-VLA Python dependencies: what each package does, where it is used in the project, and which requirements file installs it.

**Human-readable version (browser):** [`requirements.html`](html/requirements.html)

For install commands, see [Getting started](../README.md#getting-started) or run `./scripts/setup_python_env.sh`.

## Requirements file structure

Dependencies are split so you install only what you need:

| File | Purpose | When to install |
|------|---------|-----------------|
| [`requirements/base.txt`](../requirements/base.txt) | ML inference, preprocessing, config, and data utilities | Everyone working on `ml/`, `data/`, `deployment/`, or `scripts/` |
| [`requirements/dev.txt`](../requirements/dev.txt) | Base + testing and linting | Local development and CI |
| [`requirements/train.txt`](../requirements/train.txt) | Base + LoRA fine-tuning and evaluation | Epic: supervised fine-tuning (`ml/` training) |
| [`requirements/deploy.txt`](../requirements/deploy.txt) | Base + quantization and export experiments | Epic: edge deployment (`deployment/`) |
| [`requirements/all.txt`](../requirements/all.txt) | Base + dev + train (deploy installed separately) | Full ML workflow on one machine |

Root [`requirements.txt`](../requirements.txt) points to `requirements/dev.txt` for backward compatibility and matches the default setup script profile.

### Not installed via pip

| Dependency | How to install | Used for |
|------------|----------------|----------|
| ROS 2 (`rclpy`, `cv_bridge`, `geometry_msgs`, etc.) | System packages + `colcon` workspace build | Robot control loop in `ros_ws/` |
| `llama.cpp` | Build from source or system package | GGUF inference on edge hardware |
| CUDA toolkit | NVIDIA driver + platform-specific PyTorch wheel | GPU inference and training |

---

## Base dependencies (`requirements/base.txt`)

### ML core

| Package | Used for | Project area |
|---------|----------|--------------|
| **torch** | Tensor operations, model inference, training loops | `ml/` inference wrapper, fine-tuning, benchmarks |
| **torchvision** | Image transforms (resize, normalize, tensor conversion) | `ml/` preprocessing pipeline for VLM input |
| **transformers** | Load and run compact vision-language models (e.g. SmolVLM-style backbones) | `ml/` baseline inference and training format conversion |
| **accelerate** | Device placement and distributed-friendly model loading | `ml/` inference wrapper and training scripts |
| **huggingface-hub** | Download and cache models from Hugging Face Hub | `ml/`, `deployment/` model artifact management |
| **pillow** | Load and save RGB images in offline scripts | `ml/`, `data/` dataset tooling |
| **numpy** | Numeric arrays for frames, metrics, and preprocessing | `ml/`, `data/`, `deployment/` benchmarks |
| **opencv-python-headless** | Resize, color conversion, and array image ops without a GUI | `ml/` preprocessing; offline frame handling before ROS bridge |

### Utilities

| Package | Used for | Project area |
|---------|----------|--------------|
| **pyyaml** | Load runtime, training, and benchmark configuration | `scripts/`, `ml/`, `deployment/` config loader |
| **jsonschema** | Validate dataset records and structured action JSON | `data/` schema checks; action parser validation |
| **tqdm** | Progress bars in dataset, training, and benchmark scripts | `ml/`, `data/`, `deployment/` |
| **pandas** | Tabular dataset views, JSONL/CSV tooling, metric tables | `data/` labeling and validation reports |

---

## Development dependencies (`requirements/dev.txt`)

Includes everything in **base**, plus:

| Package | Used for | Project area |
|---------|----------|--------------|
| **pytest** | Unit tests, smoke tests, and CI test runs | `tests/`, package-level tests across the repo |

Run base smoke tests after setup: `pytest tests/smoke -m "not optional" -v`
| **ruff** | Fast Python linting and style checks | CI and pre-PR local checks |

See [`ci.md`](ci.md) for the full CI workflow and local commands.

---

## Training dependencies (`requirements/train.txt`)

Includes everything in **base**, plus:

| Package | Used for | Project area |
|---------|----------|--------------|
| **peft** | LoRA adapters for parameter-efficient fine-tuning | `ml/` LoRA config and training loop |
| **datasets** | Hugging Face dataset loading, caching, and map operations | `ml/` dataset loader integration |
| **scikit-learn** | Validation metrics (accuracy, confusion-style summaries) | `ml/` evaluation scripts |

---

## Deployment dependencies (`requirements/deploy.txt`)

Includes everything in **base**, plus:

| Package | Used for | Project area |
|---------|----------|--------------|
| **bitsandbytes** | 4-bit / 8-bit model loading for low-bit inference experiments | `deployment/` quantization before GGUF export |
| **onnxruntime** | Optional ONNX export and inference fallback path | `deployment/` when GGUF / llama.cpp path is blocked |

**Platform note:** `bitsandbytes` typically requires Linux with a CUDA GPU. It may fail on macOS or CPU-only hosts. Use `requirements/deploy.txt` only when running quantization experiments on supported hardware.

---

## Manual / external tooling

| Tool | Used for | Project area |
|------|----------|--------------|
| **llama.cpp** | Low-latency GGUF inference on edge devices | `deployment/` Jetson and local CUDA runtime |
| **GGUF conversion tooling** | Compress trained model for on-device inference | `deployment/` packaging pipeline |
| **ROS 2** | Camera subscription, velocity publishing, control loop | `ros_ws/` simulation and robot integration |

These are documented and scripted separately; they are intentionally not pinned in pip requirements.

---

## Choosing a profile

| Your work | Install |
|-----------|---------|
| Baseline VLM inference and preprocessing only | `pip install -r requirements/base.txt` |
| Day-to-day repo development (recommended default) | `pip install -r requirements/dev.txt` or `./scripts/setup_python_env.sh` |
| Fine-tuning experiments | `pip install -r requirements/train.txt` |
| Quantization / edge packaging | `pip install -r requirements/deploy.txt` (after checking GPU/OS support) |
| ML + dev + train on one machine | `pip install -r requirements/all.txt` |

---

## PyTorch and CUDA

Default `torch` wheels from pip are **CPU-only**. For NVIDIA GPU support, install PyTorch using the selector at [pytorch.org/get-started/locally](https://pytorch.org/get-started/locally/) **before** or **after** the requirements install, matching your CUDA version.

Document the torch build you used in experiment run metadata so results stay reproducible.
