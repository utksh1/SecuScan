#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="$ROOT_DIR/venv_tests"

cd "$ROOT_DIR"

if [ ! -d "$VENV_DIR" ]; then
  python3 -m venv "$VENV_DIR"
fi

source "$VENV_DIR/bin/activate"
if ! python -c "import pip" >/dev/null 2>&1; then
  python -m ensurepip --upgrade
fi
python -m pip install --upgrade pip
python -m pip install -r backend/requirements-dev.txt
python - <<'PY'
import os
import pytest

exit_code = pytest.main(["tests/", "-q"])
# Force process exit to avoid hangs from lingering background resources.
os._exit(exit_code)
PY
