#!/bin/bash

FORBIDDEN_PATHS=(
  "frontend/playwright-report"
  "frontend/test-results"
  "frontend/dist"
  "frontend/.vite"
)

FOUND=0

for path in "${FORBIDDEN_PATHS[@]}"; do
  if git ls-files --error-unmatch "$path" 2>/dev/null || \
     git diff --cached --name-only | grep -q "^$path"; then
    echo "ERROR: Generated artifact found: $path"
    echo "Please remove it. See CONTRIBUTING.md for help."
    FOUND=1
  fi
done

if [ "$FOUND" -eq 1 ]; then
  exit 1
fi

echo "All good! No artifacts found."
exit 0
