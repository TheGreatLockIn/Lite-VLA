# Lite-VLA

On-device Vision-Language-Action (VLA) inference for robotic control — a beginner-friendly implementation inspired by the LiteVLA-Edge paper. This repository combines ML inference, ROS 2 robot integration, deployment tooling, and benchmarking in one workspace.

## Repository layout

```
Lite-VLA/
├── ros_ws/       # ROS 2 workspace (packages, nodes, launch files)
├── ml/           # Model training, inference, and evaluation
├── data/         # Datasets, schemas, and collection artifacts
├── deployment/   # Edge runtime, quantization, and packaging
├── docs/         # Architecture, guides, and design notes
├── scripts/      # Shared setup, build, and utility scripts
└── tests/        # Cross-cutting integration and smoke tests
```

### `ros_ws/`

ROS 2 workspace for the robot control loop: camera subscriptions, velocity publishing, action parsing, and the bridge between model outputs and robot commands. Simulation and on-robot nodes live here.

### `ml/`

Python code for vision-language models — baseline inference, fine-tuning, prompts, preprocessing, and evaluation. Keeps ML experiments separate from ROS runtime code.

### `data/`

Dataset schemas, raw and processed data, labeling artifacts, and train/validation splits. Large binary assets should stay out of git; use `.gitignore` and document download paths in `docs/`.

### `deployment/`

Scripts and configs for packaging models for edge devices (e.g. quantization, GGUF export, Jetson/llama.cpp runtime). Benchmark and latency tooling belongs here when it targets deployed artifacts.

### `docs/`

Project documentation: architecture decisions, setup guides, action schemas, API notes, and runbooks. Prefer markdown files that link back to the relevant code folders.

### `scripts/`

Repository-wide helpers — environment setup, workspace builds, one-off automation, and CI entrypoints. Domain-specific logic should live in `ros_ws/`, `ml/`, or `deployment/` instead.

### `tests/`

Integration and smoke tests that span multiple areas (e.g. parser + ROS message flow). Unit tests should live next to the code they cover; this folder is for cross-cutting checks.

## Getting started

Detailed setup instructions will be added as the development environment epic (VLA-2) progresses. For now, clone the repo and explore the folders above to see where each subsystem will live.

## Contributing

Match the folder boundaries above when adding new code. If you are unsure where something belongs, check `docs/` for conventions or open a discussion before introducing a new top-level directory.
