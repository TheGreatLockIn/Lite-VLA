#!/usr/bin/env bash
# Build, validate, review, and smoke-test processed dataset v0.1.0 (Epic 105 release).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
VERSION="${LITEVLA_DATASET_VERSION:-v0.1.0}"
PROC="${REPO_ROOT}/data/processed/${VERSION}"

cd "${REPO_ROOT}"

echo "==> Build processed dataset ${VERSION}"
python3 scripts/build_starter_dataset.py --version "${VERSION}" --write-artifacts

echo
echo "==> Export label review CSV"
python3 scripts/label_review.py export \
  --jsonl "${PROC}/train.jsonl" \
  --output "${PROC}/label_review.csv"

echo
echo "==> Bulk-approve starter labels (reference + synthetic only)"
python3 scripts/label_review.py bulk-approve \
  --csv "${PROC}/label_review.csv" \
  --reviewer "${LITEVLA_REVIEWER:-starter-release}"

echo
echo "==> Import reviewed train JSONL"
python3 scripts/label_review.py import \
  --jsonl "${PROC}/train.jsonl" \
  --csv "${PROC}/label_review.csv" \
  --output "${PROC}/train_reviewed.jsonl"

echo
echo "==> Validate reviewed train + pending gate"
python3 scripts/validate_dataset.py \
  --jsonl "${PROC}/train_reviewed.jsonl" \
  --review-csv "${PROC}/label_review.csv"

echo
echo "==> Version artifacts"
python3 scripts/validate_dataset.py \
  --version "${VERSION}" \
  --write-artifacts

echo
echo "==> Loader smoke test"
python3 scripts/smoke_dataset_loader.py \
  --jsonl "${PROC}/train_reviewed.jsonl" \
  --skip-validate

echo
echo "Release folder ready: ${PROC}"
