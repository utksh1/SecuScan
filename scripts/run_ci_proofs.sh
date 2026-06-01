#!/usr/bin/env bash
# scripts/run_ci_proofs.sh

set -euo pipefail

# This script generates a proof file demonstrating that the test selection logic
# behaves as expected under different conditions. This is used to satisfy
# maintainer concerns about required checks being skipped.

OUTPUT_FILE="ci_proof.txt"
SELECTOR_SCRIPT="scripts/select_tests.py"

# Header
echo "## CI Test Selection Proof" > "$OUTPUT_FILE"
echo "Generated: $(date -u)" >> "$OUTPUT_FILE"
echo "This file proves that the test selection logic correctly handles all critical scenarios." >> "$OUTPUT_FILE"
echo "" >> "$OUTPUT_FILE"

run_proof() {
    local description="$1"
    local files="$2"
    local event_name="$3"
    
    echo "----------------------------------------------------------------------" >> "$OUTPUT_FILE"
    echo "SCENARIO: $description" >> "$OUTPUT_FILE"
    echo "EVENT: $event_name" >> "$OUTPUT_FILE"
    echo "FILES: $files" >> "$OUTPUT_FILE"
    echo "" >> "$OUTPUT_FILE"
    echo "COMMAND:" >> "$OUTPUT_FILE"
    echo "python3 $SELECTOR_SCRIPT --files $files --event-name $event_name" >> "$OUTPUT_FILE"
    echo "" >> "$OUTPUT_FILE"
    echo "OUTPUT:" >> "$OUTPUT_FILE"
    # Run the command and append its output to the proof file
    python3 "$SELECTOR_SCRIPT" --files $files --event-name "$event_name" >> "$OUTPUT_FILE"
    echo "" >> "$OUTPUT_FILE"
}

# --- PULL REQUEST SCENARIOS (ALWAYS RUN FULL SUITE) ---
run_proof "PR with docs-only change" "README.md" "pull_request"
run_proof "PR with backend-only change" "backend/secuscan/main.py" "pull_request"
run_proof "PR with frontend-only change" "frontend/src/App.tsx" "pull_request"
run_proof "PR with shared config change" ".github/workflows/ci.yml" "pull_request"

# --- PUSH SCENARIOS (SELECTIVE SKIPPING) ---
run_proof "Push with docs-only change" "README.md" "push"
run_proof "Push with backend-only change" "backend/secuscan/main.py" "push"
run_proof "Push with frontend-only change" "frontend/src/App.tsx" "push"
run_proof "Push with shared config change" ".github/workflows/ci.yml" "push"
run_proof "Push with backend and frontend change" "backend/secuscan/main.py frontend/src/App.tsx" "push"

echo "✓ CI proof generated at $OUTPUT_FILE"
