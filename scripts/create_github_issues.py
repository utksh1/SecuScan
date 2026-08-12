#!/usr/bin/env python3
"""
Script to create GitHub issues from the comprehensive bug list.

Usage:
    # Dry run (preview issues)
    python scripts/create_github_issues.py --dry-run

    # Create first 10 issues
    python scripts/create_github_issues.py --batch 1 --limit 10

    # Create specific issue by index
    python scripts/create_github_issues.py --issue 0

    # Create all critical security issues
    python scripts/create_github_issues.py --priority high --type security

Requirements:
    pip install PyGithub
    export GITHUB_TOKEN="your_personal_access_token"
"""

import os
import sys
from pathlib import Path

# Add parent directory to path to import issues_data
sys.path.insert(0, str(Path(__file__).parent))
from issues_data import ISSUES, build_type_labels

try:
    from github import Github
except ImportError:
    print("ERROR: PyGithub not installed. Run: pip install PyGithub")
    sys.exit(1)


def format_issue_body(issue: dict) -> str:
    """Format issue body with metadata and content."""
    body = issue["body"]

    # Add metadata footer
    footer = "\n\n---\n\n"
    footer += f"**Type:** {issue['type']}\n"
    footer += f"**Area:** {issue['area']}\n"
    footer += f"**Priority:** {issue['priority']}\n"
    footer += f"**Level:** {issue.get('level', 'level:intermediate')}\n"

    if issue.get('gfi'):
        footer += "\n_This issue is marked as **good first issue** - great for new contributors!_\n"

    return body + footer


def get_labels_for_issue(issue: dict) -> list:
    """Extract all labels for an issue."""
    labels = []

    # Add all type labels (security issues get both type:security and type:bug)
    labels.extend(build_type_labels(issue))

    # Add area label
    labels.append(issue["area"])

    # Add priority label
    labels.append(issue["priority"])

    # Add level label
    labels.append(issue.get("level", "level:intermediate"))

    # Add good first issue if applicable
    if issue.get("gfi"):
        labels.append("good first issue")

    return labels


def filter_issues(issues: list, priority: str = None, issue_type: str = None, area: str = None) -> list:
    """Filter issues by criteria."""
    filtered = issues

    if priority:
        filtered = [i for i in filtered if priority in i.get("priority", "")]

    if issue_type:
        filtered = [i for i in filtered if issue_type in i.get("type", "")]

    if area:
        filtered = [i for i in filtered if area in i.get("area", "")]

    return filtered


def create_github_issue(repo, issue: dict, dry_run: bool = False):
    """Create a single GitHub issue."""
    title = issue["title"]
    body = format_issue_body(issue)
    labels = get_labels_for_issue(issue)

    if dry_run:
        print("\n" + "="*80)
        print(f"TITLE: {title}")
        print(f"LABELS: {', '.join(labels)}")
        print(f"\nBODY:\n{body}")
        print("="*80)
        return None

    try:
        created_issue = repo.create_issue(
            title=title,
            body=body,
            labels=labels
        )
        print(f"✓ Created issue #{created_issue.number}: {title}")
        return created_issue
    except Exception as e:
        print(f"✗ Failed to create issue '{title}': {e}")
        return None


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Create GitHub issues from bug report")
    parser.add_argument("--dry-run", action="store_true", help="Preview issues without creating")
    parser.add_argument("--limit", type=int, help="Limit number of issues to create")
    parser.add_argument("--issue", type=int, help="Create specific issue by index")
    parser.add_argument("--priority", choices=["high", "medium", "low"], help="Filter by priority")
    parser.add_argument("--type", choices=["bug", "security", "feature", "refactor", "performance"],
                        help="Filter by type")
    parser.add_argument("--area", choices=["backend", "frontend", "plugins"], help="Filter by area")
    parser.add_argument("--repo", default="utksh1/SecuScan", help="GitHub repo (owner/name)")
    parser.add_argument("--start-from", type=int, default=0, help="Start from issue index")

    args = parser.parse_args()

    # Get GitHub token
    token = os.environ.get("GITHUB_TOKEN")
    if not token and not args.dry_run:
        print("ERROR: GITHUB_TOKEN environment variable not set")
        print("Export your token: export GITHUB_TOKEN='your_token'")
        sys.exit(1)

    # Initialize GitHub client
    if not args.dry_run:
        g = Github(token)
        try:
            repo = g.get_repo(args.repo)
            print(f"Connected to repository: {repo.full_name}")
        except Exception as e:
            print(f"ERROR: Failed to access repository {args.repo}: {e}")
            sys.exit(1)
    else:
        repo = None

    # Filter issues
    issues_to_create = ISSUES

    if args.issue is not None:
        if 0 <= args.issue < len(ISSUES):
            issues_to_create = [ISSUES[args.issue]]
        else:
            print(f"ERROR: Issue index {args.issue} out of range (0-{len(ISSUES)-1})")
            sys.exit(1)
    else:
        issues_to_create = filter_issues(ISSUES, args.priority, args.type, args.area)
        issues_to_create = issues_to_create[args.start_from:]

        if args.limit:
            issues_to_create = issues_to_create[:args.limit]

    # Display summary
    print(f"\n{'DRY RUN - ' if args.dry_run else ''}Creating {len(issues_to_create)} issues...")

    if not args.dry_run:
        confirm = input(f"Create {len(issues_to_create)} issues on {args.repo}? (yes/no): ")
        if confirm.lower() != "yes":
            print("Cancelled.")
            sys.exit(0)

    # Create issues
    created = []
    for idx, issue in enumerate(issues_to_create):
        original_idx = ISSUES.index(issue)
        print(f"\n[{idx+1}/{len(issues_to_create)}] Issue #{original_idx}: {issue['title'][:60]}...")

        result = create_github_issue(repo, issue, args.dry_run)
        if result:
            created.append(result)

    # Summary
    print(f"\n{'='*80}")
    if args.dry_run:
        print(f"DRY RUN: Would create {len(issues_to_create)} issues")
    else:
        print(f"Successfully created {len(created)}/{len(issues_to_create)} issues")
        if created:
            print(f"\nCreated issues: #{created[0].number} - #{created[-1].number}")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    main()
