import re

import pytest

from backend.secuscan.routes import build_report_filename


@pytest.mark.parametrize(
    ("task", "expected"),
    [
        (
            {
                "tool_name": "Nikto Scanner",
                "target": "https://example.com/admin?x=1",
                "created_at": "2026-05-14T10:30:00",
            },
            "secuscan_nikto-scanner_example-com_2026-05-14.html",
        ),
        (
            {
                "tool_name": "../../nmap\\scanner",
                "target": "../etc/passwd",
                "created_at": "2026-05-14",
            },
            "secuscan_nmap-scanner_target_2026-05-14.html",
        ),
        (
            {
                "tool_name": "shell; rm -rf /",
                "target": "$(whoami) && cat /etc/passwd",
                "created_at": "not-a-date",
            },
            "secuscan_shell-rm-rf_whoami-cat_report.html",
        ),
        (
            {
                "tool_name": "測試工具",
                "target": "例え.テスト",
                "created_at": "",
            },
            "secuscan_scan_target_report.html",
        ),
        (
            {
                "tool_name": "",
                "plugin_id": "",
                "target": "",
                "created_at": "",
            },
            "secuscan_scan_target_report.html",
        ),
    ],
)
def test_build_report_filename_sanitizes_unsafe_parts(task, expected):
    filename = build_report_filename(task, "html")

    assert filename == expected
    assert "/" not in filename
    assert "\\" not in filename
    assert ".." not in filename
    assert re.fullmatch(r"[a-z0-9_.-]+", filename)


def test_build_report_filename_preserves_requested_extension():
    filename = build_report_filename(
        {
            "tool_name": "HTTP Inspector",
            "target": "https://example.com",
            "created_at": "2026-05-14T10:30:00",
        },
        "sarif",
    )

    assert filename == "secuscan_http-inspector_example-com_2026-05-14.sarif"
