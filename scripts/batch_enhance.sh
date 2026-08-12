#!/usr/bin/env bash
#
# Batch enhance GitHub issues with detailed analysis
#
# Usage:
#   ./scripts/batch_enhance.sh [start_index] [end_index]
#   ./scripts/batch_enhance.sh 0 9    # Enhance issues 0-9
#

START=${1:-0}
END=${2:-9}

echo "================================================================"
echo "Batch Enhancement of GitHub Issues"
echo "================================================================"
echo "Range: Issue #$START to #$END"
echo "This will add detailed technical comments to existing issues."
echo ""
echo "Press Enter to continue, or Ctrl+C to cancel..."
read

ENHANCED=0
SKIPPED=0
FAILED=0

for i in $(seq $START $END); do
    echo ""
    echo "[$((i-START+1))/$((END-START+1))] Processing issue #$i..."
    echo "----------------------------------------------------------------"

    if ./scripts/enhance_with_gh.sh --our-index $i; then
        ((ENHANCED++))
        echo "✓ Success"
    else
        EXIT_CODE=$?
        if [ $EXIT_CODE -eq 0 ]; then
            ((SKIPPED++))
            echo "⚠️  Skipped (already enhanced or not found)"
        else
            ((FAILED++))
            echo "✗ Failed"
        fi
    fi

    # Rate limiting: wait between requests
    if [ $i -lt $END ]; then
        echo "Waiting 2 seconds (rate limiting)..."
        sleep 2
    fi
done

echo ""
echo "================================================================"
echo "Batch Enhancement Complete"
echo "================================================================"
echo "Enhanced:  $ENHANCED issues"
echo "Skipped:   $SKIPPED issues"
echo "Failed:    $FAILED issues"
echo "================================================================"
