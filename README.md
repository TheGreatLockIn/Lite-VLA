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

Project documentation, architecture decisions, setup guides, API notes, and runbooks. Cross-cutting topics live at `docs/` root (`.md` for agents) and `docs/html/` (for humans). Epic walkthroughs and Jira task docs live under `docs/epics/`. See [docs/AGENTS.md](docs/AGENTS.md) and [docs/epics/AGENTS.md](docs/epics/AGENTS.md).

Available documentation:
* **System Architecture**: [docs/architecture_summary.html](docs/architecture_summary.html)
* **MVP Demo Task & Non-Goals**: [docs/mvp_definition.html](docs/mvp_definition.html)
* **Epic walkthroughs**: [docs/epics/index.html](docs/epics/index.html)
* **Discrete Action Schema** (Epic 103): [docs/epics/action-interface-parser-and-safety-layer/action-schema.html](docs/epics/action-interface-parser-and-safety-layer/action-schema.html)
* **Dependency Guide**: [docs/requirements.html](docs/requirements.html)

### `scripts/`

Repository-wide helpers — environment setup, workspace builds, one-off automation, and CI entrypoints. Domain-specific logic should live in `ros_ws/`, `ml/`, or `deployment/` instead.

### `tests/`

Integration and smoke tests that span multiple areas (e.g. parser + ROS message flow). Unit tests should live next to the code they cover; this folder is for cross-cutting checks.

## Getting started

### Python environment

1. **Read the dependency guide** — [`docs/html/requirements.html`](docs/html/requirements.html) explains each package, which requirements file it belongs to, and how it maps to project areas (`ml/`, `data/`, `deployment/`, etc.).
2. **Run the setup script** from the repo root:

```bash
./scripts/setup_python_env.sh
```

This creates `.venv` and installs the default **dev** profile (`requirements/dev.txt`: base ML stack + pytest + ruff).

Other profiles:

```bash
./scripts/setup_python_env.sh --base    # inference and utilities only
./scripts/setup_python_env.sh --train   # add LoRA fine-tuning stack
./scripts/setup_python_env.sh --deploy  # add quantization / export tools
./scripts/setup_python_env.sh --all     # dev + train (+ deploy if supported)
```

3. **Activate the environment** before working on Python code:

```bash
source .venv/bin/activate
```

Manual install (without the script):

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Use a specific profile directly, e.g. `pip install -r requirements/train.txt`.

4. **Verify the environment** with Python smoke tests:

```bash
pytest tests/smoke -m "not optional" -v
```

This checks that base ML and utility packages import correctly and perform basic operations. Optional-profile packages (`train`, `deploy`) have separate tests — run `pytest tests/smoke -m optional -v` after installing those profiles.

5. **Log an example experiment run** (optional):

```bash
python scripts/run_dummy_pipeline.py --log-run
```

See [`docs/html/experiment-logging.html`](docs/html/experiment-logging.html) for the full run directory layout and metrics convention.
6. **Run the full CI check suite** locally before opening a PR:

```bash
./scripts/run_ci_checks.sh
```

See [`docs/ci.html`](docs/ci.html) for what runs in GitHub Actions and how to fix failures.

**Notes**

- PyTorch CUDA wheels are platform-specific; see [PyTorch install docs](https://pytorch.org/get-started/locally/) and `docs/html/requirements.html`.
- ROS 2 dependencies are installed separately via apt and `ros_ws/` — not via pip.

### ROS 2 workspace

ROS 2 **Jazzy** and `colcon` are required (not installed via pip). See [`ros_ws/README.md`](ros_ws/README.md) and the [VLA-19 task doc](docs/docs/epics/repository-development-environment-and-tooling/ros-2-workspace-setup.md).

```bash
source /opt/ros/jazzy/setup.bash
./ros_ws/scripts/build_ros_ws.sh
source ros_ws/install/setup.bash
ros2 run litevla_bridge workspace_ping
```

**Webots simulation (VLA-23)** needs two installs — the ROS bridge apt package and the Webots app:

```bash
sudo apt install ros-jazzy-webots-ros2
./ros_ws/scripts/install_webots.sh
./ros_ws/scripts/run_webots_mvp.sh
```

Details: [Webots environment task doc](docs/docs/epics/ros-2-simulation-and-robot-control-skeleton/webots-sim-environment.md).

The `litevla_bridge` package holds camera, velocity, dummy-action, heartbeat, and teleop nodes (Epic 102).

## Contributing

Match the folder boundaries above when adding new code. If you are unsure where something belongs, check `docs/` for conventions or open a discussion before introducing a new top-level directory.

### CI checks

Every pull request runs automated checks via [GitHub Actions](.github/workflows/ci.yml):

- **Lint and format** — `ruff check` and `ruff format --check` (see [`pyproject.toml`](pyproject.toml))
- **Tests** — `pytest tests -m "not optional"`
- **Sanity** — dummy pipeline script with example config

Run the same steps locally:

```bash
./scripts/run_ci_checks.sh
```

Details: [`docs/ci.html`](docs/ci.html) (humans) · [`docs/ci.md`](docs/ci.md) (agents).
