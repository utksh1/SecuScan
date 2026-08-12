#!/bin/bash
set -e

REPO="utksh1/SecuScan"

echo "=== GitHub Issue Assignment Tool ==="
echo

# Count current assignments per user
echo "Fetching current assignments..."
gh issue list --repo "$REPO" --limit 1000 --state open --json assignees \
  --jq '.[] | .assignees[].login' | sort | uniq -c | sort -rn > /tmp/counts.txt

echo
echo "=== Users at 5-issue limit ==="
awk '$1 >= 5 {print $2}' /tmp/counts.txt | tee /tmp/at_limit.txt
echo

# Get issues with recent comments requesting assignment (last 5 days)
echo "Fetching issues with recent assignment requests..."
gh issue list --repo "$REPO" --limit 200 --state open --json number,title,assignees,comments,updatedAt \
  --jq '.[] | 
    select(.assignees | length == 0) | 
    select(.comments | length > 0) |
    select(.updatedAt | fromdateiso8601 > (now - 432000)) |
    {
      number, 
      title, 
      last_requester: (.comments | last | select(.body | test("assign|work on this|take it on|i would like|please assign"; "i")) | .author.login // empty),
      last_comment_date: (.comments | last | .createdAt)
    } |
    select(.last_requester != null and .last_requester != "utksh1")' \
  > /tmp/requests.json

if [ ! -s /tmp/requests.json ]; then
    echo "No pending assignment requests found."
    rm -f /tmp/counts.txt /tmp/at_limit.txt /tmp/requests.json
    exit 0
fi

echo
echo "=== Issues Requesting Assignment ==="
jq -r '"#\(.number): \(.title[0:60])... - \(.last_requester)"' /tmp/requests.json
echo

# Create assignment plan
> /tmp/plan.txt

jq -r '.last_requester' /tmp/requests.json | sort -u | while read -r user; do
    # Check if user is at limit
    if grep -qw "^${user}$" /tmp/at_limit.txt 2>/dev/null; then
        echo "SKIP $user (at 5-issue limit)"
        continue
    fi
    
    # Get current count
    current=$(grep -w "$user" /tmp/counts.txt 2>/dev/null | awk '{print $1}' || echo "0")
    available=$((5 - current))
    
    if [ "$available" -le 0 ]; then
        echo "SKIP $user (at limit: $current issues)"
        continue
    fi
    
    echo "USER $user: $current assigned, $available slots"
    
    # Get issues requested by this user
    jq -r "select(.last_requester == \"$user\") | \"\(.number)|\(.title[0:50])\"" /tmp/requests.json | \
    head -n "$available" | while IFS='|' read -r num title; do
        echo "  → #$num: $title"
        echo "$num $user" >> /tmp/plan.txt
    done
    echo
done

if [ ! -s /tmp/plan.txt ]; then
    echo "No assignments can be made (all users at limit or no valid requests)."
    rm -f /tmp/counts.txt /tmp/at_limit.txt /tmp/requests.json /tmp/plan.txt
    exit 0
fi

echo
echo "=== Assignment Plan ==="
awk '{print "#" $1 " → " $2}' /tmp/plan.txt
echo
echo "Total: $(wc -l < /tmp/plan.txt) assignments"
echo

read -p "Proceed with these assignments? (yes/no): " confirm

if [[ "$confirm" == "yes" ]]; then
    echo
    echo "Assigning issues..."
    while read -r issue_num user; do
        if gh issue edit "$issue_num" --repo "$REPO" --add-assignee "$user" 2>&1; then
            echo "✓ Assigned #$issue_num to $user"
        else
            echo "✗ Failed to assign #$issue_num to $user"
        fi
    done < /tmp/plan.txt
    echo
    echo "Done!"
else
    echo "Cancelled."
fi

rm -f /tmp/counts.txt /tmp/at_limit.txt /tmp/requests.json /tmp/plan.txt
