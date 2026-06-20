import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLUGIN_ROOT = ROOT / "plugins"


def safe_relative_path(path, base):
    try:
        return str(path.relative_to(base))
    except ValueError:
        return str(path)


def discover_plugins(plugin_root=PLUGIN_ROOT):
    plugins = []
    plugin_root = Path(plugin_root)

    if not plugin_root.exists():
        return plugins

    for metadata_file in plugin_root.rglob("metadata.json"):
        plugin_dir = metadata_file.parent
        parser_file = plugin_dir / "parser.py"

        try:
            metadata = json.loads(metadata_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            metadata = {}

        plugins.append(
            {
                "name": metadata.get("name", plugin_dir.name),
                "path": safe_relative_path(plugin_dir, plugin_root.parent),
                "metadata_path": safe_relative_path(metadata_file, plugin_root.parent),
                "has_metadata": True,
                "has_parser": parser_file.exists(),
                "category": metadata.get("category", "uncategorized"),
                "description": metadata.get("description", ""),
            }
        )

    return sorted(plugins, key=lambda item: item["name"])


def build_report(plugins):
    total = len(plugins)
    with_parser = sum(1 for plugin in plugins if plugin["has_parser"])

    categories = {}
    for plugin in plugins:
        category = plugin["category"]
        categories[category] = categories.get(category, 0) + 1

    return {
        "summary": {
            "total_plugins": total,
            "plugins_with_parser": with_parser,
            "plugins_without_parser": total - with_parser,
        },
        "categories": categories,
        "plugins": plugins,
    }


def format_markdown(report):
    summary = report["summary"]

    lines = [
        "# Plugin Health & Coverage Report",
        "",
        "## Summary",
        "",
        f"- Total plugins: {summary['total_plugins']}",
        f"- Plugins with parser.py: {summary['plugins_with_parser']}",
        f"- Plugins without parser.py: {summary['plugins_without_parser']}",
        "",
        "## Categories",
        "",
    ]

    for category, count in sorted(report["categories"].items()):
        lines.append(f"- {category}: {count}")

    lines.extend(
        [
            "",
            "## Plugin Details",
            "",
            "| Plugin | Category | Parser | Path |",
            "|---|---|---|---|",
        ]
    )

    for plugin in report["plugins"]:
        parser_status = "Yes" if plugin["has_parser"] else "No"
        lines.append(
            f"| {plugin['name']} | {plugin['category']} | {parser_status} | `{plugin['path']}` |"
        )

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Generate plugin health report from metadata.json/parser.py plugin directories."
    )
    parser.add_argument("--format", choices=["json", "markdown"], default="markdown")
    parser.add_argument("--output", type=Path)

    args = parser.parse_args()

    report = build_report(discover_plugins())
    content = (
        json.dumps(report, indent=2)
        if args.format == "json"
        else format_markdown(report)
    )

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(content, encoding="utf-8")
    else:
        print(content)


if __name__ == "__main__":
    main()
