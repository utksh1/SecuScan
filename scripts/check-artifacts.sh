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
  "output/"
  "data/raw/"
  "data/reports/"
  "backend/data/raw/"
  "backend/data/reports/"
  "logs/"
  # Python virtual environments (local development and automation)
  "venv/"
  ".venv/"
  ".venv-codex/"
)

# ── Check 1: files already tracked in git history ─────────────────────────────
# The diff-only check below cannot catch artifacts already committed to the base
# branch. This check catches those.
echo "Checking for tracked generated artifacts in git history..."
TRACKED_FOUND=()
for pattern in "${BLOCKED_PATTERNS[@]}"; do
  while IFS= read -r match; do
    # Allow .gitkeep placeholder files — they are intentional empty markers
    [[ "$match" == *".gitkeep" ]] && continue
    TRACKED_FOUND+=("$match")
  done < <(git ls-files "${pattern}" 2>/dev/null || true)
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

# ── Check 2: files newly added in this PR/branch ──────────────────────────────
echo "Checking for generated artifacts in PR diff..."
if git rev-parse --verify "${BASE_BRANCH}" >/dev/null 2>&1; then
  CHANGED_FILES=$(git diff --name-only --diff-filter=A "${BASE_BRANCH}"...HEAD 2>/dev/null || git diff --name-only --cached)
else
  CHANGED_FILES=$(git diff --name-only --cached)
fi

FOUND=()
for pattern in "${BLOCKED_PATTERNS[@]}"; do
  while IFS= read -r match; do
    [[ "$match" == *".gitkeep" ]] && continue
    FOUND+=("$match")
  done < <(echo "$CHANGED_FILES" | grep -E "^${pattern}" 2>/dev/null || true)
done

if [[ ${#FOUND[@]} -gt 0 ]]; then
  echo "ERROR: Artifact files found in this branch:"
  for f in "${FOUND[@]}"; do echo "  - $f"; done
  echo ""
  echo "Fix: git rm --cached <file>"
  exit 1
fi

echo "All clear!"
exit 0