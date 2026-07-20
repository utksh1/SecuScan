#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
VENV_DIR="$ROOT_DIR/venv_tests"

cd "$ROOT_DIR"

find_compatible_python() {
  local candidates=(
    "python3"
    "python"
    "/opt/homebrew/bin/python3"
    "/usr/local/bin/python3"
    "python3.13"
    "python3.12"
    "python3.11"
  )
  for candidate in "${candidates[@]}"; do
    local path
    if command -v "$candidate" >/dev/null 2>&1; then
      path="$(command -v "$candidate")"
    elif [ -x "$candidate" ]; then
      path="$candidate"
    else
      continue
    fi
    if "$path" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)' >/dev/null 2>&1; then
      echo "$path"
      return 0
    fi
  done
  return 1
}

# If a venv already exists, check Python version compatibility
if [ -d "$VENV_DIR" ]; then
  if [ -d "$VENV_DIR/Scripts" ]; then
    VENV_BIN_DIR="$VENV_DIR/Scripts"
  else
    VENV_BIN_DIR="$VENV_DIR/bin"
  fi

  if [ -x "$VENV_BIN_DIR/python3" ]; then
    VENV_PYTHON="$VENV_BIN_DIR/python3"
  elif [ -x "$VENV_BIN_DIR/python" ]; then
    VENV_PYTHON="$VENV_BIN_DIR/python"
  else
    VENV_PYTHON="$VENV_BIN_DIR/python3"
  fi

  if [ ! -x "$VENV_PYTHON" ] || \
     ! "$VENV_PYTHON" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)' >/dev/null 2>&1; then
    echo "Existing venv_tests is incompatible. Recreating..."
    rm -rf "$VENV_DIR"
  fi
fi

if [ ! -d "$VENV_DIR" ]; then
  PYTHON_BIN=$(find_compatible_python || true)
  if [ -z "$PYTHON_BIN" ]; then
    echo "Error: Python 3.11+ is required to run backend tests." >&2
    exit 1
  fi
  echo "Creating virtual environment in '$VENV_DIR' using $PYTHON_BIN..."
  "$PYTHON_BIN" -m venv "$VENV_DIR"
fi

if [ -d "$VENV_DIR/Scripts" ]; then
  VENV_BIN_DIR="$VENV_DIR/Scripts"
else
  VENV_BIN_DIR="$VENV_DIR/bin"
fi

source "$VENV_BIN_DIR/activate"
if ! python -c "import pip" >/dev/null 2>&1; then
  python -m ensurepip --upgrade
fi
python -m pip install --upgrade pip
python -m pip install -r backend/requirements.txt
python -m pip install -r backend/requirements-dev.txt
python - <<'PY'
import os
import pytest

exit_code = pytest.main(["testing/backend", "-q", "-m", "not benchmark"])
# Force process exit to avoid hangs from lingering background resources.
os._exit(exit_code)
PY
