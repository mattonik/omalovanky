#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

PYTHON_BIN="${PYTHON_BIN:-.venv/bin/python}"
PYTEST_BIN="${PYTEST_BIN:-.venv/bin/pytest}"

if [[ ! -x "$PYTHON_BIN" || ! -x "$PYTEST_BIN" ]]; then
  echo "error: create .venv and install requirements-dev.txt first" >&2
  exit 1
fi

echo "[1/4] Python compile check"
PYTHONPYCACHEPREFIX=/tmp/omalovanky-pycache "$PYTHON_BIN" -m py_compile app/*.py tests/*.py

echo "[2/4] Unit and integration tests"
"$PYTEST_BIN" -m "not e2e"

echo "[3/4] Browser E2E tests"
RUN_E2E=1 "$PYTEST_BIN" -m e2e

echo "[4/4] Docker image build"
docker build -t omalovanky:test .

echo "check complete"

