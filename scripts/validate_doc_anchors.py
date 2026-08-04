import pathlib
import re
import sys
from dataclasses import dataclass
from urllib.parse import urlsplit

HEADING_RE = re.compile(r"^#+\s+(.+)$")
LINK_RE = re.compile(r"(?<!\!)\[[^\]]*\]\(([^)]+)\)")
LEGACY_LINK_RE = re.compile(r"\]\(([^)]+)\)")
EXTERNAL_SCHEMES = {"http", "https", "mailto", "tel", "javascript"}


@dataclass(frozen=True)
class LinkIssue:
    target: str
    missing_file: bool = False
    missing_anchor: str | None = None


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


def is_external_link(target):
    return urlsplit(target).scheme in EXTERNAL_SCHEMES


def normalize_link_target(target):
    target = target.strip()

    if not target:
        return ""

    if target.startswith("<") and ">" in target:
        return target[1 : target.index(">")].strip()

    parts = target.split()
    return parts[0] if parts else ""


def split_link_target(target):
    relative_target, _, anchor = target.partition("#")
    return relative_target, anchor


def resolve_link_path(md_file, relative_target):
    return (md_file.parent / relative_target).resolve()


def validate_same_file_anchors(md_file):
    content = md_file.read_text(encoding="utf-8")
    anchors = collect_anchors(md_file)
    failures = []

    for target in LEGACY_LINK_RE.findall(content):
        if not target.startswith("#"):
            continue

        anchor = target[1:]

        if anchor not in anchors:
            failures.append(anchor)

    return failures


def validate_file(md_file):
    return validate_same_file_anchors(md_file)


def validate_markdown_references(md_file, anchors_cache):
    content = md_file.read_text(encoding="utf-8")
    failures = []
    current_file_anchors = None

    for target in LINK_RE.findall(content):
        target = normalize_link_target(target)

        if not target or is_external_link(target):
            continue

        if target.startswith("#"):
            anchor = target[1:]

            if current_file_anchors is None:
                current_file_anchors = collect_anchors(md_file)

            if anchor not in current_file_anchors:
                failures.append(LinkIssue(target=target, missing_anchor=anchor))

            continue

        relative_target, anchor = split_link_target(target)

        if not relative_target.lower().endswith(".md"):
            continue

        target_file = resolve_link_path(md_file, relative_target)

        if not target_file.exists():
            failures.append(LinkIssue(target=relative_target, missing_file=True))
            continue

        if anchor:
            target_anchors = anchors_cache.get(target_file)

            if target_anchors is None:
                target_anchors = collect_anchors(target_file)
                anchors_cache[target_file] = target_anchors

            if anchor not in target_anchors:
                failures.append(LinkIssue(target=relative_target, missing_anchor=anchor))

    return failures


def iter_documentation_files(repo_root):
    entry_points = [repo_root / "README.md", repo_root / "frontend" / "README.md"]

    for entry_point in entry_points:
        if entry_point.exists():
            yield entry_point

    docs_dir = repo_root / "docs"

    if docs_dir.exists():
        yield from docs_dir.rglob("*.md")


def format_link_issue(source_file, issue):
    if issue.missing_file:
        return "\n".join(
            [
                f"ERROR: {source_file}",
                "Broken markdown link:",
                issue.target,
            ]
        )

    if issue.missing_anchor:
        return "\n".join(
            [
                f"ERROR: {source_file}",
                f"{issue.target} exists",
                "Missing anchor:",
                f"#{issue.missing_anchor}",
            ]
        )

    return f"ERROR: {source_file}\nBroken markdown link:\n{issue.target}"


def main():
    failed = False
    repo_root = pathlib.Path(__file__).resolve().parents[1]
    anchors_cache = {}

    for md_file in iter_documentation_files(repo_root):
        issues = validate_markdown_references(md_file, anchors_cache)
        source_file = md_file.relative_to(repo_root).as_posix()

        for issue in issues:
            print(format_link_issue(source_file, issue))
            failed = True

    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
