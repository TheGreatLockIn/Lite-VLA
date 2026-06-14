#!/usr/bin/env bash
# Create a Python virtual environment and install Lite-VLA dependencies.
#
# Usage:
#   ./scripts/setup_python_env.sh              # default: dev (base + pytest + ruff)
#   ./scripts/setup_python_env.sh --base       # base only
#   ./scripts/setup_python_env.sh --train      # base + training stack
#   ./scripts/setup_python_env.sh --deploy     # base + deployment/quantization stack
#   ./scripts/setup_python_env.sh --all        # dev + train (see requirements/all.txt)
#
# Read docs/requirements.md to understand what each dependency is used for.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="${VENV_DIR:-$ROOT_DIR/.venv}"
PYTHON="${PYTHON:-python3}"
PROFILE="dev"

usage() {
  sed -n '3,11p' "$0" | sed 's/^# \{0,1\}//'
  echo
  echo "Environment variables:"
  echo "  VENV_DIR   Virtual environment path (default: <repo>/.venv)"
  echo "  PYTHON     Python interpreter (default: python3)"
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --base)
      PROFILE="base"
      shift
      ;;
    --dev)
      PROFILE="dev"
      shift
      ;;
    --train)
      PROFILE="train"
      shift
      ;;
    --deploy)
      PROFILE="deploy"
      shift
      ;;
    --all)
      PROFILE="all"
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

REQ_FILE="$ROOT_DIR/requirements/${PROFILE}.txt"
if [[ ! -f "$REQ_FILE" ]]; then
  echo "Requirements file not found: $REQ_FILE" >&2
  exit 1
fi

if ! command -v "$PYTHON" >/dev/null 2>&1; then
  echo "Python interpreter not found: $PYTHON" >&2
  exit 1
fi

PY_VERSION="$("$PYTHON" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
PY_MAJOR="${PY_VERSION%%.*}"
PY_MINOR="${PY_VERSION#*.}"
if [[ "$PY_MAJOR" -lt 3 ]] || [[ "$PY_MAJOR" -eq 3 && "$PY_MINOR" -lt 10 ]]; then
  echo "Python 3.10+ is required (found $PY_VERSION)." >&2
  exit 1
fi

echo "==> Lite-VLA Python environment setup"
echo "    Repo:        $ROOT_DIR"
echo "    Python:      $($PYTHON --version)"
echo "    Virtual env: $VENV_DIR"
echo "    Profile:     $PROFILE ($REQ_FILE)"
echo
echo "    See docs/requirements.md for what each dependency is used for."
echo

if [[ ! -d "$VENV_DIR" ]]; then
  echo "==> Creating virtual environment"
  "$PYTHON" -m venv "$VENV_DIR"
else
  echo "==> Using existing virtual environment"
fi

# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

echo "==> Upgrading pip"
python -m pip install --upgrade pip

echo "==> Installing dependencies from requirements/${PROFILE}.txt"
pip install -r "$REQ_FILE"

if [[ "$PROFILE" == "all" ]]; then
  echo
  echo "==> Optional: deployment extras (bitsandbytes, onnxruntime)"
  echo "    These may fail on macOS or CPU-only machines."
  if pip install -r "$ROOT_DIR/requirements/deploy.txt"; then
    echo "    Deployment extras installed."
  else
    echo "    Skipped deployment extras (unsupported platform or missing CUDA)." >&2
  fi
fi

echo
echo "Setup complete."
echo
echo "Activate the environment:"
echo "  source $VENV_DIR/bin/activate"
echo
echo "Understand the dependency layout:"
echo "  docs/requirements.md"
echo
echo "Requirements files:"
echo "  requirements/base.txt   - ML inference and utilities"
echo "  requirements/dev.txt    - base + pytest + ruff (default)"
echo "  requirements/train.txt  - base + LoRA fine-tuning"
echo "  requirements/deploy.txt - base + quantization / export"
echo "  requirements/all.txt    - dev + train (+ optional deploy)"
echo
if [[ "$PROFILE" == "deploy" ]]; then
  echo "Note: bitsandbytes usually requires Linux with CUDA. See docs/requirements.md."
fi
