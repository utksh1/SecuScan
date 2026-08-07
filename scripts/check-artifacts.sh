#!/usr/bin/env bash
set -euo pipefail

BLOCKED_PATTERNS=(
  "frontend/playwright-report/"
  "frontend/test-results/"
  "frontend/dist/"
  "frontend/.vite/"
  "frontend/node_modules/"
  ".vite/deps/"
  "output/"
  "data/raw/"
  "data/reports/"
  "backend/data/raw/"
  "backend/data/reports/"
  "logs/"
)

check_diff_files() {
  local input_files="$1"
  local found=()
  local py_cache=()

  while IFS= read -r line || [[ -n "$line" ]]; do
    [[ -z "$line" ]] && continue
    local match="${line#\"}"
    match="${match%\"}"
    [[ "$match" == *".gitkeep" ]] && continue

    for pattern in "${BLOCKED_PATTERNS[@]}"; do
      if [[ "$match" == "${pattern}"* ]]; then
        found+=("$match")
        break
      fi
    done

    if [[ "$match" =~ (^|/)(__pycache__/|.*\.pyc$) ]]; then
      py_cache+=("$match")
    fi
  done <<< "$input_files"

  if [[ ${#found[@]} -gt 0 || ${#py_cache[@]} -gt 0 ]]; then
    return 1
  fi
  return 0
}

run_regression_tests() {
  echo "Running shell-level regression tests for artifact guard..."
  local failed=0

  # Test 1: Quoted path with spaces in blocked directory
  if check_diff_files $'\"output/my file with spaces.txt\"'; then
    echo "FAIL: Expected blocked artifact '\"output/my file with spaces.txt\"' to be caught"
    failed=$((failed + 1))
  else
    echo "PASS: Caught quoted path with spaces in blocked directory"
  fi

  # Test 2: Unquoted path with spaces in blocked directory
  if check_diff_files $'data/raw/sample data 123.csv'; then
    echo "FAIL: Expected blocked artifact 'data/raw/sample data 123.csv' to be caught"
    failed=$((failed + 1))
  else
    echo "PASS: Caught unquoted path with spaces in blocked directory"
  fi

  # Test 3: Path with escaped quotes in blocked directory
  if check_diff_files $'\"frontend/dist/app \\\"quoted\\\".js\"'; then
    echo "FAIL: Expected blocked artifact with quotes to be caught"
    failed=$((failed + 1))
  else
    echo "PASS: Caught path with escaped quotes in blocked directory"
  fi

  # Test 4: Quoted pycache file with spaces
  if check_diff_files $'\"backend/my app/__pycache__/main.cpython-311.pyc\"'; then
    echo "FAIL: Expected pycache file with spaces to be caught"
    failed=$((failed + 1))
  else
    echo "PASS: Caught quoted pycache file with spaces"
  fi

  # Test 5: Clean files with whitespace and .gitkeep
  if ! check_diff_files $'frontend/src/my component/Header.tsx\noutput/.gitkeep\nbackend/secuscan/main.py'; then
    echo "FAIL: Expected clean files with whitespace and .gitkeep to pass"
    failed=$((failed + 1))
  else
    echo "PASS: Clean files with whitespace and .gitkeep passed successfully"
  fi

  if [[ $failed -ne 0 ]]; then
    echo "ERROR: $failed regression test(s) failed."
    exit 1
  fi
  echo "All regression tests passed successfully!"
  exit 0
}

if [[ "${1:-}" == "--test" || "${1:-}" == "test" ]]; then
  run_regression_tests
fi

BASE_BRANCH="${1:-origin/main}"

# ── Check 1: files already tracked in git history ─────────────────────────────
# The diff-only check below cannot catch artifacts already committed to the base
# branch. This check catches those.
echo "Checking for tracked generated artifacts in git history..."
TRACKED_FOUND=()
for pattern in "${BLOCKED_PATTERNS[@]}"; do
  while IFS= read -r match || [[ -n "$match" ]]; do
    [[ -z "$match" ]] && continue
    match="${match#\"}"
    match="${match%\"}"
    [[ "$match" == *".gitkeep" ]] && continue
    TRACKED_FOUND+=("$match")
  done < <(git -c core.quotePath=false ls-files "${pattern}" 2>/dev/null || true)
done

if [[ ${#TRACKED_FOUND[@]} -gt 0 ]]; then
  echo "ERROR: Generated artifact is tracked by git and must be removed:"
  for f in "${TRACKED_FOUND[@]}"; do echo "  - $f"; done
  echo ""
  echo "Fix:"
  echo "  git rm --cached <file>"
  echo "  Add the path to .gitignore"
  echo "  See CONTRIBUTING.md for details."
  exit 1
fi

echo "Checking for tracked Python cache files..."
PY_CACHE_TRACKED=()
while IFS= read -r match || [[ -n "$match" ]]; do
  [[ -z "$match" ]] && continue
  match="${match#\"}"
  match="${match%\"}"
  if [[ "$match" =~ (^|/)(__pycache__/|.*\.pyc$) ]]; then
    PY_CACHE_TRACKED+=("$match")
  fi
done < <(git -c core.quotePath=false ls-files 2>/dev/null || true)

if [[ ${#PY_CACHE_TRACKED[@]} -gt 0 ]]; then
  echo "ERROR: Python cache files are tracked:"
  for f in "${PY_CACHE_TRACKED[@]}"; do echo "  - $f"; done
  echo ""
  echo "Fix:"
  echo "  git rm --cached <file>"
  exit 1
fi

# ── Check 2: files newly added in this PR/branch ──────────────────────────────
echo "Checking for generated artifacts in PR diff..."
if git rev-parse --verify "${BASE_BRANCH}" >/dev/null 2>&1; then
  CHANGED_FILES=$(git -c core.quotePath=false diff --name-only --diff-filter=A "${BASE_BRANCH}"...HEAD 2>/dev/null || git -c core.quotePath=false diff --name-only --cached)
else
  CHANGED_FILES=$(git -c core.quotePath=false diff --name-only --cached)
fi

FOUND=()
PY_CACHE_DIFF=()

while IFS= read -r match || [[ -n "$match" ]]; do
  [[ -z "$match" ]] && continue
  match="${match#\"}"
  match="${match%\"}"
  [[ "$match" == *".gitkeep" ]] && continue

  for pattern in "${BLOCKED_PATTERNS[@]}"; do
    if [[ "$match" == "${pattern}"* ]]; then
      FOUND+=("$match")
      break
    fi
  done

  if [[ "$match" =~ (^|/)(__pycache__/|.*\.pyc$) ]]; then
    PY_CACHE_DIFF+=("$match")
  fi
done <<< "$CHANGED_FILES"

if [[ ${#FOUND[@]} -gt 0 ]]; then
  echo "ERROR: Artifact files found in this branch:"
  for f in "${FOUND[@]}"; do echo "  - $f"; done
  echo ""
  echo "Fix: git rm --cached <file>"
  exit 1
fi

echo "Checking for Python cache files in PR diff..."

if [[ ${#PY_CACHE_DIFF[@]} -gt 0 ]]; then
  echo "ERROR: Python cache files found in this branch:"
  for f in "${PY_CACHE_DIFF[@]}"; do echo "  - $f"; done
  echo ""
  echo "Fix: git rm --cached <file>"
  exit 1
fi

echo "All clear!"
exit 0
