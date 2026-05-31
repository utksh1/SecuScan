import json
from pathlib import Path
from datetime import datetime


ROOT = Path(__file__).resolve().parents[1]
PLUGIN_DIR = ROOT / "plugins"
TEST_DIR = ROOT / "tests"
REPORT_DIR = ROOT / "reports"


def discover_plugins():
    plugins = []

    if not PLUGIN_DIR.exists():
        return plugins

    for file in PLUGIN_DIR.rglob("*.py"):
        if file.name.startswith("__"):
            continue

        content = file.read_text(encoding="utf-8", errors="ignore")
        relative_path = file.relative_to(ROOT)

        plugin_info = {
            "name": file.stem,
            "path": str(relative_path),
            "has_parser": "parse" in content.lower(),
            "has_tests": has_test_for_plugin(file.stem),
            "category": infer_category(file),
        }

        plugins.append(plugin_info)

    return plugins


def has_test_for_plugin(plugin_name):
    if not TEST_DIR.exists():
        return False

    for test_file in TEST_DIR.rglob("test_*.py"):
        content = test_file.read_text(encoding="utf-8", errors="ignore").lower()
        if plugin_name.lower() in content:
            return True

    return False


def infer_category(file_path):
    parts = file_path.parts
    if "plugins" in parts:
        index = parts.index("plugins")
        if len(parts) > index + 1:
            return parts[index + 1]
    return "uncategorized"


def build_report(plugins):
    total = len(plugins)
    with_parsers = sum(1 for plugin in plugins if plugin["has_parser"])
    with_tests = sum(1 for plugin in plugins if plugin["has_tests"])

    categories = {}
    for plugin in plugins:
        categories.setdefault(plugin["category"], 0)
        categories[plugin["category"]] += 1

    return {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "summary": {
            "total_plugins": total,
            "plugins_with_parsers": with_parsers,
            "plugins_without_parsers": total - with_parsers,
            "plugins_with_tests": with_tests,
            "plugins_without_tests": total - with_tests,
        },
        "categories": categories,
        "plugins": plugins,
    }


def write_json_report(report):
    REPORT_DIR.mkdir(exist_ok=True)
    output_path = REPORT_DIR / "plugin_health_report.json"

    with output_path.open("w", encoding="utf-8") as file:
        json.dump(report, file, indent=2)

    return output_path


def write_markdown_report(report):
    REPORT_DIR.mkdir(exist_ok=True)
    output_path = REPORT_DIR / "plugin_health_report.md"

    summary = report["summary"]

    lines = [
        "# Plugin Health & Coverage Report",
        "",
        f"Generated at: `{report['generated_at']}`",
        "",
        "## Summary",
        "",
        f"- Total plugins: {summary['total_plugins']}",
        f"- Plugins with parsers: {summary['plugins_with_parsers']}",
        f"- Plugins without parsers: {summary['plugins_without_parsers']}",
        f"- Plugins with tests: {summary['plugins_with_tests']}",
        f"- Plugins without tests: {summary['plugins_without_tests']}",
        "",
        "## Category Distribution",
        "",
    ]

    for category, count in sorted(report["categories"].items()):
        lines.append(f"- {category}: {count}")

    lines.extend([
        "",
        "## Plugin Details",
        "",
        "| Plugin | Category | Parser | Tests | Path |",
        "|---|---|---|---|---|",
    ])

    for plugin in sorted(report["plugins"], key=lambda item: item["name"]):
        parser_status = "Yes" if plugin["has_parser"] else "No"
        test_status = "Yes" if plugin["has_tests"] else "No"

        lines.append(
            f"| {plugin['name']} | {plugin['category']} | {parser_status} | {test_status} | `{plugin['path']}` |"
        )

    output_path.write_text("\n".join(lines), encoding="utf-8")
    return output_path


def main():
    plugins = discover_plugins()
    report = build_report(plugins)

    json_path = write_json_report(report)
    markdown_path = write_markdown_report(report)

    print(f"Plugin health JSON report generated: {json_path}")
    print(f"Plugin health Markdown report generated: {markdown_path}")


if __name__ == "__main__":
    main()
