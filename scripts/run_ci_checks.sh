#!/usr/bin/env bash
# Run the same lightweight checks used in GitHub Actions CI.
#
# Usage:
#   ./scripts/run_ci_checks.sh
#
# Prerequisites:
#   Python 3.10+ with requirements/dev.txt installed (see setup_python_env.sh).
#
# Read docs/ci.md (agents) or docs/html/ci.html (humans).

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

usage() {
  sed -n '3,10p' "$0" | sed 's/^# \{0,1\}//'
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

if ! command -v python3 >/dev/null 2>&1; then
  echo "Python interpreter not found: python3" >&2
  exit 1
fi

for tool in ruff pytest; do
  if ! command -v "$tool" >/dev/null 2>&1; then
    echo "Missing required tool: $tool" >&2
    echo "Install dev dependencies: ./scripts/setup_python_env.sh" >&2
    exit 1
  fi
done

echo "==> Lite-VLA CI checks"
echo "    Repo:   $ROOT_DIR"
echo "    Python: $(python3 --version)"
echo

echo "==> ruff check"
ruff check .

echo
echo "==> ruff format --check"
ruff format --check .

echo
echo "==> pytest (excluding optional profile tests)"
pytest tests -m "not optional" -v

echo
echo "==> dummy pipeline sanity check"
python3 scripts/run_dummy_pipeline.py

echo
echo "All CI checks passed."
