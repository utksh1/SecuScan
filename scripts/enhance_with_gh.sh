#!/usr/bin/env bash
#
# Add detailed technical comments to existing GitHub issues using gh CLI.
#
# Usage:
#   ./scripts/enhance_with_gh.sh --dry-run --our-index 0
#   ./scripts/enhance_with_gh.sh --github-issue 1826
#

set -e

REPO="utksh1/SecuScan"
DRY_RUN=false
OUR_INDEX=""
GH_NUMBER=""

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --our-index)
            OUR_INDEX="$2"
            shift 2
            ;;
        --github-issue)
            GH_NUMBER="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Check gh is installed
if ! command -v gh &> /dev/null; then
    echo "ERROR: gh CLI is not installed"
    exit 1
fi

# Check gh is authenticated
if ! gh auth status &> /dev/null; then
    echo "ERROR: gh CLI is not authenticated"
    echo "Run: gh auth login"
    exit 1
fi

# Function to find GitHub issue number from our index
# Note: GitHub uses [#1] for our index 0, [#2] for our index 1, etc.
find_github_issue() {
    local idx=$1
    local github_tag=$((idx + 1))  # Convert to 1-based
    gh issue list --repo "$REPO" --limit 1000 --state open --json number,title --jq ".[] | select(.title | contains(\"[#${github_tag}]\")) | .number" | head -1
}

# Main logic
if [ -z "$OUR_INDEX" ] && [ -z "$GH_NUMBER" ]; then
    echo "Please specify either --our-index <number> or --github-issue <number>"
    echo ""
    echo "Examples:"
    echo "  # Our issue #0 (TLS verification disabled)"
    echo "  ./scripts/enhance_with_gh.sh --dry-run --our-index 0"
    echo ""
    echo "  # Or use GitHub issue number directly"
    echo "  ./scripts/enhance_with_gh.sh --dry-run --github-issue 1826"
    exit 1
fi

# Determine which issue to process
if [ -n "$OUR_INDEX" ]; then
    echo "Processing our issue #${OUR_INDEX}..."
    ISSUE_IDX=$OUR_INDEX

    # Find GitHub issue
    if [ -z "$GH_NUMBER" ]; then
        GH_NUMBER=$(find_github_issue "$OUR_INDEX")
        if [ -z "$GH_NUMBER" ]; then
            echo "✗ Could not find GitHub issue for our index #${OUR_INDEX}"
            echo "Try using --github-issue <number> instead"
            exit 1
        fi
    fi
else
    # User provided GitHub number - need to find our index
    echo "Looking up our index for GitHub issue #${GH_NUMBER}..."
    TITLE=$(gh issue view "$GH_NUMBER" --repo "$REPO" --json title --jq '.title')

    # Extract [#X] from title
    if [[ $TITLE =~ \[#([0-9]+)\] ]]; then
        GITHUB_TAG="${BASH_REMATCH[1]}"
        ISSUE_IDX=$((GITHUB_TAG - 1))  # Convert to 0-based
        echo "Found our index: #${ISSUE_IDX}"
    else
        echo "✗ Could not find issue index tag in title: $TITLE"
        exit 1
    fi
fi

echo "GitHub issue #${GH_NUMBER} corresponds to our issue #${ISSUE_IDX}"

# Read issue data from Python
ISSUE_TITLE=$(python3 -c "import sys; sys.path.insert(0, 'scripts'); from issues_data import ISSUES; print(ISSUES[${ISSUE_IDX}]['title'])")
ISSUE_BODY=$(python3 -c "import sys; sys.path.insert(0, 'scripts'); from issues_data import ISSUES; print(ISSUES[${ISSUE_IDX}]['body'])")
ISSUE_TYPE=$(python3 -c "import sys; sys.path.insert(0, 'scripts'); from issues_data import ISSUES; print(ISSUES[${ISSUE_IDX}]['type'])")
ISSUE_AREA=$(python3 -c "import sys; sys.path.insert(0, 'scripts'); from issues_data import ISSUES; print(ISSUES[${ISSUE_IDX}]['area'])")
ISSUE_PRIORITY=$(python3 -c "import sys; sys.path.insert(0, 'scripts'); from issues_data import ISSUES; print(ISSUES[${ISSUE_IDX}]['priority'])")

# Generate comment
COMMENT=$(cat << EOF
## 🔍 Enhanced Technical Analysis

This comment provides additional technical depth, attack scenarios, and fix recommendations from comprehensive security audit.

---

### 📋 Issue Details

**Audit Index:** #${ISSUE_IDX}
**Type:** \`${ISSUE_TYPE}\`
**Area:** \`${ISSUE_AREA}\`
**Priority:** \`${ISSUE_PRIORITY}\`

### 📝 Detailed Analysis

${ISSUE_BODY}

### 🧪 Testing Recommendations

- [ ] Add test that reproduces the issue
- [ ] Verify test fails before fix
- [ ] Verify test passes after fix
- [ ] Add edge case tests
- [ ] Run security/regression tests

### 🔗 Related Documentation

This issue is part of a comprehensive security audit (102 issues discovered). See:
- [Complete Bug Report](https://github.com/utksh1/SecuScan/blob/main/DISCOVERED_BUGS_REPORT.md)
- [Bug Hunt Summary](https://github.com/utksh1/SecuScan/blob/main/BUG_HUNT_SUMMARY.md)
- [Final Results](https://github.com/utksh1/SecuScan/blob/main/FINAL_RESULTS.md)

---

*Enhanced analysis from security audit - July 9, 2026*
EOF
)

if [ "$DRY_RUN" = true ]; then
    echo ""
    echo "=========================================="
    echo "WOULD ADD COMMENT TO GITHUB ISSUE #${GH_NUMBER}"
    echo "Our Issue Index: #${ISSUE_IDX}"
    echo "=========================================="
    echo ""
    echo "$COMMENT"
    echo ""
    echo "=========================================="
else
    # Check if we already commented
    if gh issue view "$GH_NUMBER" --repo "$REPO" --json comments --jq '.comments[].body' | grep -q "Enhanced Technical Analysis"; then
        echo "⚠️  Issue #${GH_NUMBER} already has enhancement comment - skipping"
        exit 0
    fi

    echo "$COMMENT" | gh issue comment "$GH_NUMBER" --repo "$REPO" --body-file -
    echo "✓ Added enhancement comment to GitHub issue #${GH_NUMBER} (Our index #${ISSUE_IDX})"
fi
