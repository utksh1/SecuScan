from pathlib import Path
import re
import sys

VALID_LABELS = {
    "type:bug",
    "type:feature",
    "type:docs",
    "type:devops",
    "type:security",
    "type:testing",
    "type:performance",
    "type:refactor",
    "area:ci",
    "area:docs",
    "area:backend",
    "area:frontend",
    "priority:low",
    "priority:medium",
    "priority:high",
    "level:beginner",
    "level:intermediate",
    "level:advanced",
}

TEMPLATE_DIR = Path(".github/ISSUE_TEMPLATE")

errors = []

for template in TEMPLATE_DIR.glob("*.md"):
    content = template.read_text(encoding="utf-8")
    match = re.search(r"^labels:\s*(.+)$", content, re.MULTILINE)

    if not match:
        continue

    labels = [label.strip() for label in match.group(1).split(",") if label.strip()]

    for label in labels:
        if label not in VALID_LABELS:
            errors.append(f"{template}: invalid label '{label}'")

if errors:
    print("Invalid issue template labels found:")
    for error in errors:
        print(f"- {error}")
    sys.exit(1)

print("All issue template labels are valid.")