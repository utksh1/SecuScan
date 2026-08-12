#!/usr/bin/env python3
"""
Script to analyze GitHub issues and make assignments based on recent activity.
Respects the 5-issue limit per contributor.
"""

import json
import subprocess
from datetime import datetime, timedelta
from collections import defaultdict

# Load the issues data
with open('/Users/Utkarsh/.zcode/cli/artifacts/sess_1b8b3e21-4b98-47c9-8f5c-245be02a0f65/tooluse_yE93WJLLw7samRRIshaQSN-tool-result-452bf350-ce6d-4f7a-8ac8-cf6fdce88683.json', 'r') as f:
    issues = json.load(f)

# Count current assignments
assignment_counts = defaultdict(int)
for issue in issues:
    for assignee in issue.get('assignees', []):
        assignment_counts[assignee['login']] += 1

print("=== Current Assignment Counts ===")
for user, count in sorted(assignment_counts.items(), key=lambda x: x[1], reverse=True):
    print(f"{user}: {count} issues")
print()

# Find issues with recent activity (last 3 days) that need assignment
from datetime import timezone
cutoff_date = datetime.now(timezone.utc) - timedelta(days=3)
needs_assignment = []

for issue in issues:
    # Skip if already assigned
    if issue.get('assignees'):
        continue
    
    # Check for recent comments
    comments = issue.get('comments', [])
    if not comments:
        continue
    
    # Find people requesting assignment
    for comment in comments:
        comment_date = datetime.fromisoformat(comment['createdAt'].replace('Z', '+00:00'))
        if comment_date > cutoff_date:
            body = comment['body'].lower()
            # Look for assignment requests
            if any(phrase in body for phrase in ['assign', 'work on this', 'take it on', 'i would like']):
                needs_assignment.append({
                    'number': issue['number'],
                    'title': issue['title'],
                    'requester': comment['author']['login'],
                    'comment_date': comment['createdAt'],
                    'comment_body': comment['body'][:100]
                })
                break

print(f"=== Found {len(needs_assignment)} issues with recent assignment requests ===\n")

# Group by requester
by_requester = defaultdict(list)
for item in needs_assignment:
    by_requester[item['requester']].append(item)

# Prepare assignments
assignments_to_make = []

for requester, items in sorted(by_requester.items()):
    current_count = assignment_counts.get(requester, 0)
    available_slots = 5 - current_count
    
    print(f"{requester}: {current_count} current assignments, {available_slots} slots available")
    
    if available_slots > 0:
        for item in items[:available_slots]:
            print(f"  ✓ Can assign #{item['number']}: {item['title'][:60]}...")
            assignments_to_make.append((item['number'], requester))
    else:
        print(f"  ✗ At limit, cannot assign more issues")
        for item in items:
            print(f"    - #{item['number']}: {item['title'][:60]}...")
    print()

print(f"\n=== Ready to assign {len(assignments_to_make)} issues ===")
print("\nAssignments to make:")
for issue_num, user in assignments_to_make:
    print(f"  #{issue_num} → {user}")

# Confirm before proceeding
print("\nProceed with assignments? (y/n): ", end='')
response = input().strip().lower()

if response == 'y':
    print("\nMaking assignments...")
    for issue_num, user in assignments_to_make:
        try:
            result = subprocess.run(
                ['gh', 'issue', 'edit', str(issue_num), '--add-assignee', user, '--repo', 'utksh1/SecuScan'],
                capture_output=True,
                text=True,
                check=True
            )
            print(f"✓ Assigned #{issue_num} to {user}")
        except subprocess.CalledProcessError as e:
            print(f"✗ Failed to assign #{issue_num} to {user}: {e.stderr}")
else:
    print("Cancelled.")
