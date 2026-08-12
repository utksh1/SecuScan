#!/usr/bin/env python3
"""
Generate a visual summary of discovered bugs.
"""

import sys
from pathlib import Path
from collections import Counter

sys.path.insert(0, str(Path(__file__).parent))
from issues_data import ISSUES


def analyze_bugs():
    """Analyze and display bug statistics."""

    # Count by category
    by_type = Counter()
    by_area = Counter()
    by_priority = Counter()
    by_level = Counter()

    security_issues = []
    good_first_issues = []

    for idx, issue in enumerate(ISSUES):
        by_type[issue['type']] += 1
        by_area[issue['area']] += 1
        by_priority[issue['priority']] += 1
        by_level[issue.get('level', 'level:intermediate')] += 1

        if 'security' in issue['type']:
            security_issues.append((idx, issue['title']))

        if issue.get('gfi'):
            good_first_issues.append((idx, issue['title']))

    print("=" * 80)
    print("SecuScan Bug Analysis Summary".center(80))
    print("=" * 80)
    print()

    print(f"📊 TOTAL ISSUES DISCOVERED: {len(ISSUES)}")
    print()

    # By Type
    print("🔍 BY TYPE:")
    for bug_type, count in sorted(by_type.items(), key=lambda x: -x[1]):
        bar = "█" * (count // 2)
        print(f"  {bug_type:25} {count:3} {bar}")
    print()

    # By Area
    print("📁 BY AREA:")
    for area, count in sorted(by_area.items(), key=lambda x: -x[1]):
        bar = "█" * (count // 2)
        print(f"  {area:25} {count:3} {bar}")
    print()

    # By Priority
    print("⚠️  BY PRIORITY:")
    priority_order = ['priority:high', 'priority:medium', 'priority:low']
    for priority in priority_order:
        count = by_priority[priority]
        if count > 0:
            bar = "█" * (count // 2)
            emoji = "🔴" if "high" in priority else "🟡" if "medium" in priority else "🟢"
            print(f"  {emoji} {priority:25} {count:3} {bar}")
    print()

    # By Level
    print("🎯 BY DIFFICULTY LEVEL:")
    level_order = ['level:beginner', 'level:intermediate', 'level:advanced']
    for level in level_order:
        count = by_level.get(level, 0)
        if count > 0:
            bar = "█" * (count // 2)
            print(f"  {level:25} {count:3} {bar}")
    print()

    # Security Issues
    print(f"🔒 SECURITY ISSUES ({len(security_issues)} total):")
    for idx, title in security_issues[:10]:
        print(f"  #{idx:3} {title[:70]}")
    if len(security_issues) > 10:
        print(f"  ... and {len(security_issues) - 10} more")
    print()

    # Good First Issues
    print(f"🌟 GOOD FIRST ISSUES ({len(good_first_issues)} total):")
    for idx, title in good_first_issues[:10]:
        print(f"  #{idx:3} {title[:70]}")
    if len(good_first_issues) > 10:
        print(f"  ... and {len(good_first_issues) - 10} more")
    print()

    # Top 10 Critical
    print("🚨 TOP 10 CRITICAL ISSUES:")
    critical_indices = [0, 1, 2, 4, 6, 7, 10, 14, 15, 16]
    for idx in critical_indices:
        if idx < len(ISSUES):
            issue = ISSUES[idx]
            print(f"  #{idx:3} {issue['title'][:70]}")
    print()

    print("=" * 80)
    print("📄 Full report: DISCOVERED_BUGS_REPORT.md")
    print("🚀 Create issues: python scripts/create_github_issues.py --help")
    print("📋 Quick start: BUG_REPORT_QUICKSTART.md")
    print("=" * 80)


if __name__ == "__main__":
    analyze_bugs()
