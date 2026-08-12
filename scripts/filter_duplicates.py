#!/usr/bin/env python3
"""
Compare discovered bugs with existing GitHub issues and remove duplicates.
"""

import re
import sys
from pathlib import Path
from difflib import SequenceMatcher

sys.path.insert(0, str(Path(__file__).parent))
from issues_data import ISSUES


def similarity(a: str, b: str) -> float:
    """Calculate similarity ratio between two strings."""
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def normalize_title(title: str) -> str:
    """Normalize title for comparison."""
    # Remove leading issue references like [#XX]
    title = re.sub(r'^\[#\d+\]\s*', '', title)
    # Remove common prefixes
    for prefix in ['Bug:', 'Feature:', 'Enhancement:', 'Critical:', 'Improvement:']:
        if title.startswith(prefix):
            title = title[len(prefix):].strip()
    return title.lower().strip()


def extract_issue_number(title: str) -> int:
    """Extract issue number from title like [#15]."""
    match = re.match(r'^\[#(\d+)\]', title)
    return int(match.group(1)) if match else None


def load_existing_issues(filepath: str) -> list:
    """Load existing GitHub issues."""
    issues = []
    with open(filepath, 'r') as f:
        for line in f:
            line = line.strip()
            if '|' in line:
                parts = line.split('|', 1)
                if len(parts) == 2:
                    number, title = parts
                    issues.append({
                        'number': int(number),
                        'title': title,
                        'normalized': normalize_title(title),
                        'referenced_idx': extract_issue_number(title)
                    })
    return issues


def find_matches(our_issues: list, existing_issues: list, threshold: float = 0.8):
    """Find matching issues between our list and existing GitHub issues."""
    matches = []
    unmatched = []

    for idx, our_issue in enumerate(our_issues):
        our_title = our_issue['title']
        our_normalized = normalize_title(our_title)

        best_match = None
        best_score = 0

        for existing in existing_issues:
            # Direct index match (issues created with [#XX] prefix)
            if existing['referenced_idx'] == idx:
                best_match = existing
                best_score = 1.0
                break

            # Title similarity match
            score = similarity(our_normalized, existing['normalized'])
            if score > best_score:
                best_score = score
                best_match = existing

        if best_score >= threshold:
            matches.append({
                'our_idx': idx,
                'our_title': our_title,
                'github_number': best_match['number'],
                'github_title': best_match['title'],
                'score': best_score
            })
        else:
            unmatched.append({
                'idx': idx,
                'title': our_title,
                'type': our_issue['type'],
                'priority': our_issue['priority'],
                'area': our_issue['area']
            })

    return matches, unmatched


def main():
    print("=" * 80)
    print("Comparing Discovered Bugs with Existing GitHub Issues".center(80))
    print("=" * 80)
    print()

    # Load existing issues
    existing_file = '/tmp/open_issues.txt'
    try:
        existing = load_existing_issues(existing_file)
        print(f"✓ Loaded {len(existing)} existing GitHub issues")
    except Exception as e:
        print(f"✗ Error loading existing issues: {e}")
        sys.exit(1)

    # Find matches
    print(f"✓ Analyzing {len(ISSUES)} discovered issues...")
    matches, unmatched = find_matches(ISSUES, existing, threshold=0.75)

    print()
    print("=" * 80)
    print(f"📊 RESULTS")
    print("=" * 80)
    print(f"Total discovered:     {len(ISSUES)}")
    print(f"Already on GitHub:    {len(matches)} ({len(matches)/len(ISSUES)*100:.1f}%)")
    print(f"New/Unmatched:        {len(unmatched)} ({len(unmatched)/len(ISSUES)*100:.1f}%)")
    print()

    # Show matches
    if matches:
        print("=" * 80)
        print(f"✓ MATCHED ISSUES (Already on GitHub)")
        print("=" * 80)
        for match in sorted(matches, key=lambda x: x['our_idx']):
            print(f"\n#{match['our_idx']:3} → GH #{match['github_number']} (similarity: {match['score']:.2f})")
            print(f"  Our:    {match['our_title'][:70]}")
            print(f"  GitHub: {match['github_title'][:70]}")

    # Show unmatched
    if unmatched:
        print()
        print("=" * 80)
        print(f"🆕 UNMATCHED ISSUES (Not yet on GitHub)")
        print("=" * 80)

        # Group by priority
        by_priority = {'priority:high': [], 'priority:medium': [], 'priority:low': []}
        for item in unmatched:
            priority = item['priority']
            by_priority[priority].append(item)

        for priority in ['priority:high', 'priority:medium', 'priority:low']:
            items = by_priority[priority]
            if items:
                emoji = "🔴" if "high" in priority else "🟡" if "medium" in priority else "🟢"
                print(f"\n{emoji} {priority.upper()} ({len(items)} issues)")
                for item in sorted(items, key=lambda x: x['idx']):
                    print(f"  #{item['idx']:3} [{item['area']:15}] {item['title'][:55]}")

    # Save unmatched to file
    output_file = Path(__file__).parent / 'unmatched_issues.txt'
    with open(output_file, 'w') as f:
        f.write("# Unmatched Issues (Not yet on GitHub)\n")
        f.write(f"# Total: {len(unmatched)} issues\n\n")
        for item in sorted(unmatched, key=lambda x: x['idx']):
            f.write(f"{item['idx']}|{item['priority']}|{item['area']}|{item['title']}\n")

    print()
    print("=" * 80)
    print(f"✓ Unmatched issues saved to: {output_file}")
    print("=" * 80)
    print()

    # Summary for creating issues
    if unmatched:
        print("🚀 TO CREATE REMAINING ISSUES:")
        print()

        # Get unmatched indices
        unmatched_indices = [item['idx'] for item in unmatched]

        print("# Create high priority unmatched issues:")
        high_priority_indices = [item['idx'] for item in unmatched if item['priority'] == 'priority:high']
        if high_priority_indices:
            indices_str = ','.join(map(str, high_priority_indices))
            print(f"python3 scripts/create_github_issues.py --issue {high_priority_indices[0]}")
            print(f"# (Issues: {', '.join(f'#{i}' for i in high_priority_indices)})")

        print()
        print("# Create all unmatched issues:")
        print(f"# Total: {len(unmatched)} issues")
        print(f"# Run create_github_issues.py for indices: {', '.join(map(str, sorted(unmatched_indices)[:10]))}...")


if __name__ == "__main__":
    main()
