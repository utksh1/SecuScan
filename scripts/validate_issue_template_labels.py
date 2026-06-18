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

REPO_ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_DIR = REPO_ROOT / ".github" / "ISSUE_TEMPLATE"

errors = []


def extract_front_matter(content):
    if not content.startswith("---"):
        return ""

    parts = content.split("---", 2)
    if len(parts) < 3:
        return ""

    return parts[1]


def parse_labels(raw_value):
    raw_value = raw_value.strip().strip("\"'")

    if raw_value.startswith("[") and raw_value.endswith("]"):
        raw_value = raw_value[1:-1]

    return [
        label.strip().strip("\"'")
        for label in raw_value.split(",")
        if label.strip()
    ]


def extract_labels_from_front_matter(front_matter):
    labels = []
    lines = front_matter.splitlines()

    for index, line in enumerate(lines):
        match = re.match(r"^labels:\s*(.*)$", line)

        if not match:
            continue

        value = match.group(1).strip()

        if value:
            labels.extend(parse_labels(value))
            continue

        for next_line in lines[index + 1:]:
            stripped = next_line.strip()

            if not stripped:
                continue

            if not stripped.startswith("-"):
                break

            labels.append(stripped[1:].strip().strip("\"'"))

    return labels


for template in list(TEMPLATE_DIR.glob("*.md")) + list(TEMPLATE_DIR.glob("*.yml")) + list(TEMPLATE_DIR.glob("*.yaml")):
    content = template.read_text(encoding="utf-8")
    front_matter = extract_front_matter(content)
    labels = extract_labels_from_front_matter(front_matter)

    for label in labels:
        if label not in VALID_LABELS:
            errors.append("{}: invalid label '{}'".format(template.relative_to(REPO_ROOT), label))

if errors:
    print("Invalid issue template labels found:")
    for error in errors:
        print("- {}".format(error))
    sys.exit(1)

print("All issue template labels are valid.")