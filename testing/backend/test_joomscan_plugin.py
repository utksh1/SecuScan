import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
PLUGIN_DIR = REPO_ROOT / "plugins" / "joomscan"


def test_joomscan_target_field_uses_url_validation_preset():
    data = json.loads((PLUGIN_DIR / "metadata.json").read_text(encoding="utf-8"))
    fields = {f["id"]: f for f in data["fields"]}

    target_validation = fields["target"].get("validation", {})

    assert target_validation.get("validation_type") == "url"
    assert target_validation.get("message") == "Must be a valid HTTP(S) URL"
    assert "pattern" not in target_validation
