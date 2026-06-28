"""
validate_doc_links.py

Checks every cross-file Markdown link in README.md, docs/*.md, CONTRIBUTING.md,
PLUGINS.md, and SECURITY.md to ensure:

  1. The target file exists on disk (relative to the source file).
  2. If the link includes a #fragment, the matching heading anchor exists in
     that target file (using the same GitHub-compatible slug as
     validate_doc_anchors.py).

Links to external URLs (http/https), bare in-page anchors (#heading), and
mailto: references are skipped.

Exit codes:
  0 — all links resolve cleanly
  1 — one or more broken links found; each error is printed to stdout so CI
      surfaces it in the build log.

Usage:
  python scripts/validate_doc_links.py
"""

from __future__ import annotations

import pathlib
import re
import sys

# ── Patterns ──────────────────────────────────────────────────────────────────

LINK_RE = re.compile(r"\[([^\]]*)\]\(([^)]+)\)")
HEADING_RE = re.compile(r"^#+\s+(.+)$", re.MULTILINE)

# ── Root files and directories to scan ────────────────────────────────────────

REPO_ROOT = pathlib.Path(__file__).parent.parent

ROOT_FILES = [
    REPO_ROOT / "README.md",
    REPO_ROOT / "CONTRIBUTING.md",
    REPO_ROOT / "PLUGINS.md",
    REPO_ROOT / "SECURITY.md",
]

DOCS_DIR = REPO_ROOT / "docs"

# ── Helpers ───────────────────────────────────────────────────────────────────


def slugify(text: str) -> str:
    """Reproduce GitHub's heading-to-anchor slug algorithm."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"\s+", "-", text)
    return text


def collect_anchors(md_file: pathlib.Path) -> set[str]:
    """Return the set of valid heading anchors for *md_file*."""
    return {
        slugify(m.group(1))
        for m in HEADING_RE.finditer(md_file.read_text(encoding="utf-8"))
    }


def source_files() -> list[pathlib.Path]:
    files: list[pathlib.Path] = []
    for p in ROOT_FILES:
        if p.exists():
            files.append(p)
    if DOCS_DIR.is_dir():
        files.extend(DOCS_DIR.rglob("*.md"))
    return files


# ── Core validation ───────────────────────────────────────────────────────────


def validate_file(md_file: pathlib.Path) -> list[str]:
    """
    Return a list of human-readable error strings for *md_file*.
    An empty list means the file is clean.
    """
    errors: list[str] = []
    content = md_file.read_text(encoding="utf-8")

    for _label, target in LINK_RE.findall(content):
        # Skip external URLs, in-page anchors, and mailto links
        if (
            target.startswith("http://")
            or target.startswith("https://")
            or target.startswith("#")
            or target.startswith("mailto:")
        ):
            continue

        # Split path from optional #fragment
        fragment: str | None = None
        path_part = target
        if "#" in target:
            path_part, fragment = target.split("#", 1)

        # Resolve the target path relative to the file that contains the link
        resolved = (md_file.parent / path_part).resolve()

        if not resolved.exists():
            errors.append(
                f"ERROR: {md_file.relative_to(REPO_ROOT)} -> broken link target"
                f" '{path_part}' (resolved: {resolved})"
            )
            continue

        # If there is a fragment and the target is a Markdown file, verify the anchor
        if fragment and resolved.suffix == ".md":
            anchors = collect_anchors(resolved)
            if fragment not in anchors:
                errors.append(
                    f"ERROR: {md_file.relative_to(REPO_ROOT)} -> anchor '#{fragment}'"
                    f" not found in '{resolved.relative_to(REPO_ROOT)}'"
                    f" (available: {sorted(anchors)[:8]}{'...' if len(anchors) > 8 else ''})"
                )

    return errors


# ── Entry point ───────────────────────────────────────────────────────────────


def main() -> None:
    files = source_files()
    if not files:
        print("WARNING: no Markdown files found to validate.")
        sys.exit(0)

    all_errors: list[str] = []
    for md_file in sorted(files):
        all_errors.extend(validate_file(md_file))

    if all_errors:
        for err in all_errors:
            print(err)
        print(f"\n{len(all_errors)} broken link(s) found.")
        sys.exit(1)

    print(f"OK: {len(files)} file(s) checked, all cross-file links resolve.")
    sys.exit(0)


if __name__ == "__main__":
    main()