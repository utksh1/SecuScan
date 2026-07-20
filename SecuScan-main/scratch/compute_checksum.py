import json
import hashlib
from pathlib import Path

def compute_plugin_digest(metadata_file: Path, parser_file: Path) -> str:
    metadata = json.loads(metadata_file.read_text(encoding="utf-8"))
    metadata.pop("checksum", None)
    metadata.pop("signature", None)
    metadata_canonical = json.dumps(metadata, sort_keys=True, separators=(",", ":"))
    metadata_digest = hashlib.sha256(metadata_canonical.encode("utf-8")).hexdigest()
    parser_digest = hashlib.sha256(parser_file.read_bytes()).hexdigest() if parser_file.exists() else ""
    return hashlib.sha256(f"{metadata_digest}:{parser_digest}".encode("utf-8")).hexdigest()

plugin_dir = Path("/Users/Utkarsh/Desktop/Projects/SecuScan/plugins/whois_lookup")
metadata_file = plugin_dir / "metadata.json"
parser_file = plugin_dir / "parser.py"

print(compute_plugin_digest(metadata_file, parser_file))
