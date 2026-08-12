#!/bin/bash
set -e

REPO="utksh1/SecuScan"

echo "=== Analyzing Issues for Quality ==="
echo

echo "Fetching open issues..."

# Get issues that look suspicious
gh issue list --repo "$REPO" --limit 500 --state open --json number,title,body,comments,author,labels \
  --jq '.[] | select(.author.login != "utksh1") | {number, title, body: (.body // ""), comment_count: (.comments | length), author: .author.login, labels: [.labels[].name]}' > /tmp/issues.json

echo
echo "=== Analyzing Issues ==="
echo

> /tmp/suspicious.txt

# Find spam/low quality issues
jq -r '
  select(
    # Very short/empty body
    (.body | length < 30) or
    
    # Generic unhelpful titles
    (.title | test("^(bug|issue|error|problem|help|question|fix me|please help|assign)$"; "i")) or
    
    # Obvious spam keywords (but not crypto/security related)
    (.title + " " + .body | test("\\b(hire|freelance|fiverr|upwork|cheap services|buy now|loan|investment|casino|slots|dating)\\b"; "i")) or
    
    # Empty title
    (.title | length < 10)
  ) | 
  "SUSPICIOUS #\(.number): \(.title[0:60]) (by \(.author), body: \(.body | length) chars, comments: \(.comment_count))"
' /tmp/issues.json > /tmp/suspicious.txt

if [ ! -s /tmp/suspicious.txt ]; then
    echo "No suspicious issues found!"
    rm -f /tmp/issues.json /tmp/suspicious.txt
    exit 0
fi

echo "Found suspicious issues:"
cat /tmp/suspicious.txt
echo
echo "=== Total: $(wc -l < /tmp/suspicious.txt) issues ==="
echo

# Extract just the issue numbers
grep -o '#[0-9]\+' /tmp/suspicious.txt | sed 's/#//' > /tmp/to_close.txt

echo "Issue numbers:"
cat /tmp/to_close.txt
echo

read -p "Review each issue before closing? (y/n): " review

if [[ "$review" =~ ^[Yy]$ ]]; then
    while read -r issue_num; do
        echo "============================================"
        echo "Issue #$issue_num"
        echo "============================================"
        gh issue view "$issue_num" --repo "$REPO"
        echo
        read -p "Action - [c]lose / [s]kip / [q]uit: " action
        
        case "$action" in
            c|C)
                read -p "Reason (spam/not-planned/invalid) [not-planned]: " reason
                reason=${reason:-not-planned}
                
                read -p "Add comment? (enter text or leave empty): " comment_text
                
                if [ -n "$comment_text" ]; then
                    gh issue comment "$issue_num" --repo "$REPO" --body "$comment_text"
                fi
                
                gh issue close "$issue_num" --repo "$REPO" --reason "$reason"
                echo "✓ Closed #$issue_num as $reason"
                ;;
            q|Q)
                echo "Quitting."
                break
                ;;
            *)
                echo "✗ Skipped #$issue_num"
                ;;
        esac
        echo
    done < /tmp/to_close.txt
else
    echo "Showing first 5 issues for quick review:"
    head -n 5 /tmp/suspicious.txt
    echo
    read -p "Close ALL as 'not-planned'? (yes/no): " confirm
    if [[ "$confirm" == "yes" ]]; then
        while read -r issue_num; do
            if gh issue close "$issue_num" --repo "$REPO" --reason "not-planned" 2>&1; then
                echo "✓ Closed #$issue_num"
            else
                echo "✗ Failed to close #$issue_num"
            fi
        done < /tmp/to_close.txt
    else
        echo "Cancelled."
    fi
fi

rm -f /tmp/issues.json /tmp/suspicious.txt /tmp/to_close.txt

echo
echo "Done!"
