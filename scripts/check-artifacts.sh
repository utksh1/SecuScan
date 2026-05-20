#!/usr/bin/env bash
set -euo pipefail
BASE_BRANCH="${1:-origin/main}"
BLOCKED_PATTERNS=(
  "frontend/playwright-report/"
  "frontend/test-results/"
  "frontend/dist/"
  "frontend/.vite/"
  "frontend/node_modules/"
  ".vite/deps/"
)
echo "Checking for generated frontend artifacts..."
if git rev-parse --verify "${BASE_BRANCH}" >/dev/null 2>&1; then
  CHANGED_FILES=$(git diff --name-only "${BASE_BRANCH}"...HEAD 2>/dev/null || git diff --name-only HEAD)
else
  CHANGED_FILES=$(git diff --name-only --cached)
fi
FOUND=()
for pattern in "${BLOCKED_PATTERNS[@]}"; do
  while IFS= read -r match; do FOUND+=("$match")
  done < <(echo "$CHANGED_FILES" | grep -E "^${pattern}" 2>/dev/null || true)
done
if [[ ${#FOUND[@]} -gt 0 ]]; then
  echo "ERROR: Artifact files found:"
  for f in "${FOUND[@]}"; do echo "  - $f"; done
  echo "Fix: git rm --cached <file>"
  exit 1
fi
echo "All clear!"
exit 0