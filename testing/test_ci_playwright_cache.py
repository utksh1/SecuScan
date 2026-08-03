from pathlib import Path


def test_ci_workflow_caches_playwright_browsers_by_version():
    workflow = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")

    assert "Resolve Playwright version" in workflow
    assert "actions/cache@v4" in workflow
    assert "~/.cache/ms-playwright" in workflow
    assert "npx playwright install --with-deps chromium" in workflow
    assert "steps.playwright-version.outputs.version" in workflow