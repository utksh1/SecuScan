#!/usr/bin/env python3
"""
Enhance existing GitHub issues with comprehensive analysis.

Adds detailed comments to existing GitHub issues using gh CLI.

Usage:
    python3 scripts/enhance_github_issues.py --dry-run --limit 2
    python3 scripts/enhance_github_issues.py --issue 14
    python3 scripts/enhance_github_issues.py --priority high --type security
"""

import os
import sys
import json
import subprocess
import time
import tempfile
from pathlib import Path
from typing import Optional, List

sys.path.insert(0, str(Path(__file__).parent))
from issues_data import ISSUES

# Mapping from internal issue index to GitHub issue number (from filter_duplicates.py)
ISSUE_MAPPING = {
    0: 1826, 1: 1826, 2: 1863, 3: 1865, 4: 1867, 5: 1870,
    6: 1872, 7: 1874, 8: 1876, 9: 1878, 10: 1880, 11: 1881,
    12: 1883, 13: 1884, 14: 1886, 15: 1974, 16: 1887, 17: 1888,
    18: 1889, 19: 1890, 20: 1890, 21: 1976, 22: 1891, 23: 1892,
    24: 1893, 25: 1894, 26: 1895, 27: 1896, 28: 1897, 29: 1898,
    30: 1899, 31: 1900, 32: 1901, 33: 1902, 34: 1903, 35: 1904,
    36: 1905, 37: 1906, 38: 1907, 39: 1908, 40: 1909, 41: 1910,
    42: 1911, 43: 1912, 44: 1913, 45: 1914, 46: 1915, 47: 1916,
    48: 1917, 49: 1918, 50: 1919, 51: 1920, 52: 1921, 53: 1827,
    54: 1828, 55: 1829, 56: 1830, 57: 1831, 58: 1832, 59: 1833,
    60: 1834, 61: 1835, 62: 1836, 63: 1837, 64: 1838, 65: 1839,
    66: 1840, 67: 1841, 68: 1842, 69: 1843, 70: 1844, 71: 1845,
    72: 1846, 73: 1847, 74: 1848, 75: 1849, 76: 1850, 77: 1851,
    78: 1852, 79: 1853, 80: 1854, 81: 1855, 82: 1856, 83: 1857,
    84: 1858, 85: 1859, 86: 1860, 87: 1862, 88: 1864, 89: 1866,
    90: 1868, 91: 1869, 92: 1871, 93: 1873, 94: 1875, 95: 1877,
    96: 1879, 97: 1882, 98: 1967, 99: 1885, 100: 1969,
}

ENHANCEMENT_MARKER = "<!-- Enhanced by comprehensive security audit 2026-07-09 -->"


def check_if_enhanced(gh_issue_num: int, repo: str) -> bool:
    """Check if issue already has enhancement comment."""
    try:
        result = subprocess.run(
            ["gh", "issue", "view", str(gh_issue_num), "--repo", repo, "--json", "comments"],
            capture_output=True, text=True, check=True
        )
        data = json.loads(result.stdout)
        for comment in data.get("comments", []):
            if ENHANCEMENT_MARKER in comment.get("body", ""):
                return True
        return False
    except Exception:
        return False


def format_enhancement(internal_id: int) -> str:
    """Format enhancement comment."""
    issue = ISSUES[internal_id]
    body = issue['body']

    comment = f"""{ENHANCEMENT_MARKER}

## 🔍 Enhanced Analysis

### Issue Classification
- **Type:** `{issue.get('type', 'type:bug')}`
- **Priority:** `{issue.get('priority', 'priority:medium')}`
- **Area:** `{issue.get('area', 'area:backend')}`
- **Difficulty:** `{issue.get('level', 'level:intermediate')}`
"""

    if issue.get('gfi'):
        comment += "- **Good First Issue:** ✅ Yes - Great for new contributors!\n"

    comment += f"\n### Detailed Analysis\n\n{body}\n\n"

    # Add type-specific sections
    if 'security' in issue.get('type', ''):
        comment += """### Security Considerations

**For Developers:**
1. Review the vulnerability and understand the attack vector
2. Implement the suggested fix with proper security testing
3. Add tests to prevent regression
4. Look for similar patterns in the codebase

**For Security Team:**
1. Assess the risk in your deployment context
2. Consider temporary mitigations if needed
3. Review related security patterns

"""

    comment += """### Implementation Checklist
- [ ] Understand the root cause
- [ ] Implement the recommended fix
- [ ] Add/update tests
- [ ] Update documentation if needed
- [ ] Check for similar patterns elsewhere

---
*Enhanced analysis from comprehensive security audit - 2026-07-09*
"""

    return comment


def post_comment(gh_issue_num: int, comment: str, repo: str, dry_run: bool = False) -> bool:
    """Post enhancement comment to GitHub issue."""
    if dry_run:
        print(f"\n{'='*80}")
        print(f"DRY RUN: Would post to issue #{gh_issue_num}")
        print(f"{'='*80}")
        print(comment[:500] + "..." if len(comment) > 500 else comment)
        print(f"{'='*80}\n")
        return True

    try:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write(comment)
            temp_file = f.name

        subprocess.run(
            ["gh", "issue", "comment", str(gh_issue_num), "--body-file", temp_file, "--repo", repo],
            capture_output=True, text=True, check=True
        )
        os.unlink(temp_file)
        print(f"✓ Enhanced issue #{gh_issue_num}")
        return True
    except Exception as e:
        print(f"✗ Failed to enhance issue #{gh_issue_num}: {e}")
        return False


def filter_issues(issues: List[int], priority=None, issue_type=None, area=None) -> List[int]:
    """Filter issues by criteria."""
    filtered = []
    for i in issues:
        if i >= len(ISSUES):
            continue
        issue = ISSUES[i]
        if priority and priority not in issue.get("priority", ""):
            continue
        if issue_type and issue_type not in issue.get("type", ""):
            continue
        if area and area not in issue.get("area", ""):
            continue
        filtered.append(i)
    return filtered


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Enhance GitHub issues")
    parser.add_argument("--dry-run", action="store_true", help="Preview only")
    parser.add_argument("--issue", type=int, help="Enhance specific issue (internal ID)")
    parser.add_argument("--limit", type=int, help="Limit number of issues")
    parser.add_argument("--priority", choices=["high", "medium", "low"])
    parser.add_argument("--type", choices=["security", "bug", "feature", "refactor", "performance"])
    parser.add_argument("--area", choices=["backend", "frontend", "plugins"])
    parser.add_argument("--repo", default="utksh1/SecuScan")
    parser.add_argument("--all", action="store_true", help="Enhance all issues")
    parser.add_argument("--delay", type=float, default=1.0, help="Delay between requests")

    args = parser.parse_args()

    if args.issue is not None:
        issues_to_enhance = [args.issue] if 0 <= args.issue < len(ISSUES) else []
    else:
        issues_to_enhance = list(ISSUE_MAPPING.keys())
        issues_to_enhance = filter_issues(issues_to_enhance, args.priority, args.type, args.area)
        if args.limit:
            issues_to_enhance = issues_to_enhance[:args.limit]

    print(f"\n{'='*80}")
    print(f"{'DRY RUN - ' if args.dry_run else ''}Enhancing {len(issues_to_enhance)} issues")
    print(f"{'='*80}\n")

    if not args.dry_run and not args.all and len(issues_to_enhance) > 5:
        confirm = input(f"Enhance {len(issues_to_enhance)} issues? (yes/no): ")
        if confirm.lower() != "yes":
            print("Cancelled.")
            return

    enhanced = []
    skipped = []

    for idx, internal_id in enumerate(issues_to_enhance):
        gh_num = ISSUE_MAPPING.get(internal_id)
        if not gh_num:
            skipped.append(internal_id)
            continue

        print(f"[{idx+1}/{len(issues_to_enhance)}] Internal #{internal_id} → GH #{gh_num}")

        if not args.dry_run and check_if_enhanced(gh_num, args.repo):
            print(f"  ℹ Already enhanced, skipping")
            skipped.append(internal_id)
            continue

        comment = format_enhancement(internal_id)
        if post_comment(gh_num, comment, args.repo, args.dry_run):
            enhanced.append(internal_id)

        if not args.dry_run and idx < len(issues_to_enhance) - 1:
            time.sleep(args.delay)

    print(f"\n{'='*80}")
    print(f"{'DRY RUN: Would enhance' if args.dry_run else 'Enhanced'}: {len(enhanced)}")
    if skipped:
        print(f"Skipped: {len(skipped)}")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    main()
