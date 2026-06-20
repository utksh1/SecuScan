import pathlib
import re
import sys

HEADING_RE = re.compile(r"^#+\s+(.+)$")
LINK_RE = re.compile(r"\]\(([^)]+)\)")


def slugify(text):
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"\s+", "-", text)
    return text


def collect_anchors(md_file):
    anchors = set()

    for line in md_file.read_text(encoding="utf-8").splitlines():
        match = HEADING_RE.match(line)
        if match:
            anchors.add(slugify(match.group(1)))

    return anchors


def validate_file(md_file):
    content = md_file.read_text(encoding="utf-8")

    anchors = collect_anchors(md_file)

    failures = []

    for target in LINK_RE.findall(content):
        if not target.startswith("#"):
            continue

        anchor = target[1:]

        if anchor not in anchors:
            failures.append(anchor)

    return failures


def main():
    failed = False

    for md_file in pathlib.Path("docs").rglob("*.md"):
        missing = validate_file(md_file)

        for anchor in missing:
            print(f"ERROR: {md_file} -> missing anchor #{anchor}")
            failed = True

    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
