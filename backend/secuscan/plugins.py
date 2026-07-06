"""
Plugin loader and management system
"""

import time
import json
import os
import re
from pathlib import Path
from typing import Any, Dict, Optional, List
import logging
import shutil
import hashlib
import hmac

from .models import PluginMetadata, PluginFieldType
from .config import settings
from .capabilities import validate_capability_list, ALL_CAPABILITIES
from .validation import sanitize_input

# Port specifications: one or more comma-separated port numbers or port ranges.
# Valid: "22", "80,443", "1-1000", "22,80,1000-2000"
# Invalid: "--", "1--2", ",,", "-80"
_PORT_SPEC_PATTERN = re.compile(r"^\d+(-\d+)?(,\d+(-\d+)?)*$")

# Internal control fields injected by the executor/routes layer that are not
# declared in individual plugin schemas.  Strip these before schema validation
# so plugins that don't declare them don't raise "Unknown field" errors.
_INTERNAL_CONTROL_FIELDS: frozenset = frozenset({
    "safe_mode",
    "consent_granted",
    "dry_run",
    "debug_mode",
})

logger = logging.getLogger(__name__)

_PLACEHOLDER_PLUGIN_IDS = frozenset({
    "zap_scanner",
    "sniper",
})

_NATIVE_PLUGIN_IDS = frozenset({
    "network_scanner",
    "api_scanner",
    "xss_exploiter",
    "web_scanner",
    "recon_scanner",
    "port_scanner",
})

_VALIDATION_PRESETS: Dict[str, Dict[str, Any]] = {
    "url": {
        "pattern": re.compile(r"^https?://[^\s/$.?#].[^\s]*$", re.IGNORECASE),
        "message": "Must be a valid URL starting with http:// or https://",
    },
    "hostname": {
        "pattern": re.compile(
            r"^(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)*[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?$"
        ),
        "message": "Must be a valid hostname (e.g. example.com or sub.example.com)",
    },
    "domain": {
        "pattern": re.compile(r"^(?!https?://)(?:[a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}$"),
        "message": "Must be a valid domain name without a scheme (e.g. example.com)",
    },
    "ipv4": {
        "pattern": re.compile(
            r"^(25[0-5]|2[0-4]\d|1\d{2}|[1-9]\d|\d)\.(25[0-5]|2[0-4]\d|1\d{2}|[1-9]\d|\d)\.(25[0-5]|2[0-4]\d|1\d{2}|[1-9]\d|\d)\.(25[0-5]|2[0-4]\d|1\d{2}|[1-9]\d|\d)$"
        ),
        "message": "Must be a valid IPv4 address (e.g. 192.168.1.1)",
    },
    "port": {
        "pattern": re.compile(
            r"^(6553[0-5]|655[0-2]\d|65[0-4]\d{2}|6[0-4]\d{3}|[1-5]\d{4}|[1-9]\d{0,3}|[1-9])$"
        ),
        "message": "Must be a valid port number between 1 and 65535",
    },
    "cidr": {
        "pattern": re.compile(
            r"^(25[0-5]|2[0-4]\d|1\d{2}|[1-9]\d|\d)(\.(25[0-5]|2[0-4]\d|1\d{2}|[1-9]\d|\d)){3}/(3[0-2]|[12]\d|[0-9])$"
        ),
        "message": "Must be a valid CIDR block (e.g. 192.168.1.0/24)",
    },
}

def _is_absolute_path(value: str) -> bool:
    """Check if a path is absolute regardless of the server OS.

    Handles Unix (/), Windows drive-letter (C:\\, C:/),
    and UNC (\\\\server\\share) absolute path styles.
    """
    if value.startswith("/"):
        return True
    if value.startswith("\\"):
        return True
    return bool(re.match(r'^[a-zA-Z]:[/\\]', value))

class PluginManager:
    """Manages plugin loading and validation"""

    def __init__(self, plugins_dir: str):
        self.plugins_dir = Path(plugins_dir)
        self.plugins: Dict[str, PluginMetadata] = {}

    async def load_plugins(self) -> int:
        """
        Load all plugins from the plugins directory.

        Returns:
            Number of successfully loaded plugins
        """
        if not self.plugins_dir.exists():
            logger.warning(f"Plugins directory does not exist: {self.plugins_dir}")
            self.plugins_dir.mkdir(parents=True, exist_ok=True)
            return 0

        loaded = 0

        # Scan for plugin directories
        for plugin_dir in self.plugins_dir.iterdir():
            if not plugin_dir.is_dir():
                continue

            metadata_file = plugin_dir / "metadata.json"
            if not metadata_file.exists():
                logger.warning(f"No metadata.json found in {plugin_dir}")
                continue

            try:
                plugin_meta = await self._load_plugin_metadata(metadata_file)

                # Validate plugin
                if await self._validate_plugin(plugin_meta, plugin_dir):
                    self.plugins[plugin_meta.id] = plugin_meta
                    loaded += 1
                    logger.info(f"✓ Loaded plugin: {plugin_meta.name} v{plugin_meta.version}")
                else:
                    logger.error(f"✗ Failed to validate plugin: {plugin_meta.id}")

            except Exception as e:
                logger.error(f"Failed to load plugin from {plugin_dir}: {e}")

        logger.info(f"Loaded {loaded} plugins")

        # Invalidate caches when plugin state changes
        try:
            from .cache import invalidate_plugin_caches
            await invalidate_plugin_caches()
        except Exception as e:
            logger.warning(f"Failed to invalidate plugin caches: {e}")

        return loaded

    async def _load_plugin_metadata(self, metadata_file: Path) -> PluginMetadata:
        """Load and parse plugin metadata JSON"""
        # Always read metadata as UTF-8 to avoid platform-dependent decoding issues
        with open(metadata_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        return PluginMetadata(**data)

    async def _validate_plugin(self, plugin: PluginMetadata, plugin_dir: Path) -> bool:
        """
        Validate plugin metadata and dependencies.

        Args:
            plugin: Plugin metadata
            plugin_dir: Plugin directory path

        Returns:
            True if plugin is valid
        """
        # Check required fields
        if not plugin.id or not plugin.name:
            logger.error("Plugin missing required fields: id or name")
            return False

        # Validate engine type
        if plugin.engine.get("type") not in ["cli", "python", "docker"]:
            logger.error(f"Invalid engine type: {plugin.engine.get('type')}")
            return False

        # Check binary exists for CLI plugins
        if plugin.engine.get("type") == "cli":
            binary = plugin.engine.get("binary")
            if binary and not shutil.which(binary):
                logger.warning(f"Binary not found in PATH: {binary}")
                # Don't fail - might be in a non-standard location or added later

        # Validate parser exists
        parser_file = plugin_dir / "parser.py"
        if plugin.output.get("parser") == "custom" and not parser_file.exists():
            logger.warning("Custom parser specified but parser.py not found")

        # Validate safety level
        safety_level = plugin.safety.get("level")
        if safety_level not in ["safe", "intrusive", "exploit"]:
            logger.error(f"Invalid safety level: {safety_level}")
            return False

        # Validate declared capabilities against the known set
        if plugin.capabilities is not None:
            try:
                validate_capability_list(plugin.capabilities, plugin.id)
            except ValueError as exc:
                logger.error("Invalid capabilities in plugin %s: %s", plugin.id, exc)
                return False

        if not self._verify_plugin_integrity(plugin, plugin_dir):
            return False

        return True

    def _verify_plugin_integrity(self, plugin: PluginMetadata, plugin_dir: Path) -> bool:
        """Verify plugin checksum/signature when available."""
        metadata_file = plugin_dir / "metadata.json"
        parser_file = plugin_dir / "parser.py"
        has_checksum = bool(plugin.checksum)
        has_signature = bool(plugin.signature)

        if not has_checksum and not has_signature and settings.enforce_plugin_signatures:
            logger.error("Plugin %s missing checksum/signature while enforcement is enabled", plugin.id)
            return False

        try:
            combined_digest = self.compute_plugin_digest(metadata_file, parser_file)
        except Exception as exc:
            logger.error("Failed to hash plugin files for %s: %s", plugin.id, exc)
            return False

        if has_checksum and plugin.checksum != combined_digest:
            logger.error("Checksum mismatch for plugin %s", plugin.id)
            return False

        if has_signature:
            if not settings.plugin_signature_key:
                if settings.enforce_plugin_signatures:
                    logger.error("SECUSCAN_PLUGIN_SIGNATURE_KEY required for verifying %s", plugin.id)
                    return False
                logger.warning("Skipping signature verification for %s: key not configured", plugin.id)
            else:
                expected_sig = hmac.new(
                    settings.plugin_signature_key.encode("utf-8"),
                    combined_digest.encode("utf-8"),
                    hashlib.sha256,
                ).hexdigest()
                if not hmac.compare_digest(expected_sig, plugin.signature):
                    logger.error("Signature mismatch for plugin %s", plugin.id)
                    return False

        return True

    @staticmethod
    def compute_plugin_digest(metadata_file: Path, parser_file: Path) -> str:
        """Compute deterministic plugin digest ignoring mutable checksum/signature fields."""
        metadata = json.loads(metadata_file.read_text(encoding="utf-8"))
        metadata.pop("checksum", None)
        metadata.pop("signature", None)
        metadata_canonical = json.dumps(metadata, sort_keys=True, separators=(",", ":"))
        metadata_digest = hashlib.sha256(metadata_canonical.encode("utf-8")).hexdigest()

        parser_digest = ""
        if parser_file.exists():
            parser_bytes = parser_file.read_bytes()
            parser_bytes_normalized = parser_bytes.replace(b"\r\n", b"\n")
            parser_digest = hashlib.sha256(parser_bytes_normalized).hexdigest()

        return hashlib.sha256(f"{metadata_digest}:{parser_digest}".encode("utf-8")).hexdigest()

    def verify_parser_at_exec_time(
        self, plugin: PluginMetadata, plugin_dir: Path
    ) -> bool:
        """Re-verify plugin digest immediately before executing parser.py.

        This closes the TOCTOU window between startup integrity check and
        actual code execution: the file could be replaced on disk after the
        initial load-time validation.

        Returns True when execution should proceed, False when it must be
        blocked.
        """
        metadata_file = plugin_dir / "metadata.json"
        parser_file = plugin_dir / "parser.py"

        if not plugin.checksum:
            if settings.enforce_parser_integrity:
                logger.error(
                    "Refusing to execute parser for plugin %s: no checksum present "
                    "and parser integrity enforcement is enabled",
                    plugin.id,
                )
                return False
            logger.warning(
                "Executing unverified parser for plugin %s: checksum not set",
                plugin.id,
            )
            return True

        try:
            current_digest = self.compute_plugin_digest(metadata_file, parser_file)
        except Exception as exc:
            logger.error(
                "Failed to compute digest for plugin %s at exec time: %s",
                plugin.id,
                exc,
            )
            return False

        if not hmac.compare_digest(current_digest, plugin.checksum):
            logger.error(
                "SECURITY: Parser integrity check failed for plugin %s — "
                "parser.py may have been tampered with after startup",
                plugin.id,
            )
            return False

        return True

    def get_plugin(self, plugin_id: str) -> Optional[PluginMetadata]:
        """Get plugin by ID"""
        return self.plugins.get(plugin_id)

    def list_plugins(self) -> List[Dict]:
        """List all loaded plugins"""
        plugins: List[Dict] = []
        for plugin in self.plugins.values():
            missing_binaries = self._get_missing_binaries(plugin)
            plugins.append(
                {
                    "id": plugin.id,
                    "name": plugin.name,
                    "description": plugin.description,
                    "category": plugin.category,
                    "safety_level": plugin.safety.get("level"),
                    "enabled": True,
                    "icon": plugin.icon,
                    "requires_consent": bool(plugin.safety.get("requires_consent", False)),
                    "consent_message": plugin.safety.get("consent_message"),
                    "capabilities": plugin.capabilities or [],
                    "implementation_status": self._resolve_implementation_status(plugin),
                    "supports_authenticated_crawling": bool(getattr(plugin, "supports_authenticated_crawling", False)),
                    "supports_session_reuse": bool(getattr(plugin, "supports_session_reuse", False)),
                    "availability": {
                        "runnable": len(missing_binaries) == 0,
                        "missing_binaries": missing_binaries,
                        "status": "available" if len(missing_binaries) == 0 else "unavailable",
                        "guidance": (
                            None
                            if len(missing_binaries) == 0
                            else (
                                f"Unavailable: Requires external binaries ({', '.join(missing_binaries)}). "
                                "Install required tools locally to enable this scanner."
                            )
                        ),
                    },
                }
            )
        return plugins

    def _get_missing_binaries(self, plugin: PluginMetadata) -> List[str]:
        """Resolve missing CLI binaries for runtime availability reporting."""
        required: List[str] = []

        if plugin.engine.get("type") == "cli":
            engine_binary = plugin.engine.get("binary")
            if engine_binary:
                required.append(engine_binary)

        if plugin.dependencies:
            for dep_binary in plugin.dependencies.get("binaries", []):
                if dep_binary:
                    required.append(dep_binary)

        # Preserve declaration order while removing duplicates.
        unique_required = list(dict.fromkeys(required))
        return [binary for binary in unique_required if shutil.which(binary) is None]

    def get_plugin_schema(self, plugin_id: str) -> Optional[Dict]:
        """Get full plugin schema for UI generation"""
        if plugin := self.get_plugin(plugin_id):
            return {
                "id": plugin.id,
                "name": plugin.name,
                "description": plugin.description,
                "fields": [f.model_dump() for f in plugin.fields],
                "presets": plugin.presets,
                "safety": plugin.safety,
                "implementation_status": self._resolve_implementation_status(plugin),
                "supports_authenticated_crawling": bool(getattr(plugin, "supports_authenticated_crawling", False)),
                "supports_session_reuse": bool(getattr(plugin, "supports_session_reuse", False)),
            }
        else:
            return None

    def _resolve_implementation_status(self, plugin: PluginMetadata) -> str:
        """Resolve implementation maturity without requiring every plugin to be edited."""
        explicit = getattr(plugin, "implementation_status", None)
        if explicit:
            return str(explicit)
        if plugin.id in _PLACEHOLDER_PLUGIN_IDS:
            return "placeholder"
        if plugin.id in _NATIVE_PLUGIN_IDS:
            return "native"
        return "integrated"

    def _interpolate(self, token: str, inputs: Dict) -> Optional[str]:
        """Interpolate variables in a token string using single-pass substitution.

        First validates that every required placeholder has a non-empty value,
        then performs a single ``re.sub`` pass to replace all placeholders at
        once.  This prevents a user-supplied value for one field from being
        re-interpreted as a placeholder for another field (sequential template
        injection).
        """
        if "{" not in token or "}" not in token:
            return token

        matches = re.findall(r"\{(\w+)(?::([^}]+))?\}", token)

        # Fail fast: if ANY required variable is missing, return None
        # (matching the original sequential behaviour).
        for var_name, default_value in matches:
            actual_default = default_value or None
            value = inputs.get(var_name, actual_default)
            if value is None or value == "":
                return None

        # All variables are present — single-pass substitution is safe.
        def _replacer(m: re.Match) -> str:
            var_name = m.group(1)
            default_value = m.group(2)
            actual_default = default_value or None
            value = inputs.get(var_name, actual_default)
            return sanitize_input(str(value))

        return re.sub(r"\{(\w+)(?::([^}]+))?\}", _replacer, token)

    def _with_field_defaults(self, plugin: PluginMetadata, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Fill omitted inputs from plugin field defaults."""
        normalized = dict(inputs)
        for field in plugin.fields:
            if field.id not in normalized or normalized[field.id] in (None, ""):
                if field.default not in (None, ""):
                    normalized[field.id] = field.default
        return normalized

    def _reject_path_traversal(self, value: str) -> None:
        """Raise ValueError if value contains parent-directory traversal components.

        Called for every STRING/TEXT field during schema validation to prevent
        ``../`` sequences from reaching external tools as file-path arguments,
        which would enable arbitrary file-read via path traversal.
        """
        normalized = value.replace("\\", os.sep).replace("/", os.sep)
        parts = normalized.split(os.sep)
        if ".." in parts:
            raise ValueError(
                f"Value {value!r} contains parent-directory traversal ('..'), "
                f"which is not allowed."
            )

    def _is_path_in_wordlists_dir(self, resolved: Path) -> bool:
        """Check that a resolved path is within the configured wordlists directory."""
        wordlists_dir = Path(settings.wordlists_dir).resolve()
        try:
            resolved.resolve().relative_to(wordlists_dir)
            return True
        except ValueError:
            return False

    def _resolve_wordlist_path(self, value: str) -> str:
        """Resolve plugin wordlist aliases and Linux-centric defaults to local project assets."""
        candidate = Path(os.path.expanduser(value))

        if _is_absolute_path(value):
            raise ValueError(
                f"Wordlist path must be relative, got absolute path: {value!r}"
            )

        self._reject_path_traversal(value)

        if candidate.exists():
            resolved = candidate.resolve()
            if not self._is_path_in_wordlists_dir(resolved):
                raise ValueError(
                    f"Wordlist path {value!r} resolves outside the allowed wordlists directory "
                    f"({settings.wordlists_dir}). Only paths within the wordlists directory "
                    f"are permitted by default."
                )
            return str(candidate)

        wordlists_dir = Path(settings.wordlists_dir)
        wordlists_resolved = wordlists_dir.resolve()

        alias_map = {
            "small": wordlists_dir / "small.txt",
            "medium": wordlists_dir / "medium.txt",
            "large": wordlists_dir / "large.txt",
        }

        lowered = value.lower()
        if lowered in alias_map and alias_map[lowered].exists():
            return str(alias_map[lowered])

        fallback_candidates = [
            wordlists_dir / value,
            wordlists_dir / candidate.name,
            wordlists_dir / "SecLists" / "Discovery" / "Web-Content" / candidate.name,
            wordlists_dir / "SecLists" / "Discovery" / "DNS" / candidate.name,
        ]

        if "dirb/common.txt" in lowered:
            fallback_candidates.insert(0, wordlists_dir / "common.txt")
        elif "discovery/web-content/common.txt" in lowered:
            fallback_candidates.insert(0, wordlists_dir / "common.txt")
        elif "discovery/dns/subdomains-top1million-110000.txt" in lowered:
            fallback_candidates.insert(0, wordlists_dir / "subdomains-top1million-110000.txt")

        for fallback in fallback_candidates:
            if fallback.exists():
                resolved = fallback.resolve()
                if wordlists_resolved not in resolved.parents and resolved != wordlists_resolved:
                    continue
                return str(fallback)

        # Before returning the raw value, verify it doesn't escape
        resolved_value = (wordlists_dir / value).resolve()
        if wordlists_resolved not in resolved_value.parents and resolved_value != wordlists_resolved:
            raise ValueError(
                f"Wordlist path {value!r} escapes the wordlists directory"
            )

        return value

    def _normalize_inputs(self, plugin: PluginMetadata, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize plugin inputs before command rendering."""
        normalized = self._with_field_defaults(plugin, inputs)
        wordlist_value = normalized.get("wordlist")
        if isinstance(wordlist_value, str) and wordlist_value.strip():
            normalized["wordlist"] = self._resolve_wordlist_path(wordlist_value.strip())
        return normalized

    def _reject_injected_args(self, field_id: str, value: str) -> None:
        """Raise ValueError if value looks like a flag injection attempt.

        Port fields are exempt from the leading-dash check but must match the
        numeric port-specification grammar.  All other string fields must not
        begin with a '-' character.
        """
        if field_id in ("ports", "port"):
            if value and not _PORT_SPEC_PATTERN.match(value):
                raise ValueError(
                    f"Invalid port specification {value!r}: "
                    "must be a number (80), range (1-1000), or comma-separated list (22,80,443)"
                )
            return
        if value.lstrip().startswith("-"):
            raise ValueError(
                f"Field '{field_id}' value must not begin with '-': {value!r}"
            )

    def _validate_inputs_against_schema(
        self, plugin: PluginMetadata, inputs: Dict[str, Any]
    ) -> None:
        """Validate caller-supplied inputs against the plugin's declared field schema.

        Internal control fields (safe_mode, consent_granted, etc.) are stripped
        before validation because they are injected by the executor layer and are
        never declared in individual plugin schemas.

        Raises ValueError with a descriptive message for the first violation found.
        """
        field_map = {f.id: f for f in plugin.fields}

        for field_id, raw_value in inputs.items():
            # Strip internal control fields — they are not part of the plugin schema
            if field_id in _INTERNAL_CONTROL_FIELDS or field_id.startswith("__"):
                continue

            field = field_map.get(field_id)
            if field is None:
                raise ValueError(
                    f"Unknown field {field_id!r} is not declared in plugin {plugin.id!r} schema"
                )

            # Skip None / empty values — defaults will be applied later by _with_field_defaults
            if raw_value is None or raw_value == "":
                continue

            if field.type == PluginFieldType.INTEGER:
                try:
                    int(raw_value)
                except (TypeError, ValueError):
                    raise ValueError(
                        f"Field '{field_id}' expects an integer; got {raw_value!r}"
                    )
                continue

            if field.type == PluginFieldType.BOOLEAN:
                if isinstance(raw_value, bool):
                    continue
                if isinstance(raw_value, str) and raw_value.lower() in ("true", "false", "1", "0"):
                    continue
                raise ValueError(
                    f"Field '{field_id}' expects a boolean; got {raw_value!r}"
                )

            if field.type == PluginFieldType.SELECT:
                allowed = [opt.get("value") for opt in (field.options or [])]
                if raw_value not in allowed:
                    raise ValueError(
                        f"Field '{field_id}' value {raw_value!r} is not in allowed "
                        f"values {allowed}"
                    )
                continue

            if field.type in (PluginFieldType.STRING, PluginFieldType.TEXT):
                value_str = str(raw_value)

                # Pattern / validation_type validation from field metadata
                validation = field.validation or {}
                validation_type = validation.get("validation_type")
                if validation_type and validation_type in _VALIDATION_PRESETS:
                    preset = _VALIDATION_PRESETS[validation_type]
                    if not preset["pattern"].match(value_str):
                        msg = validation.get("message", preset["message"])
                        raise ValueError(f"Field '{field_id}': {msg}")
                else:
                    pattern = validation.get("pattern")
                    if pattern and not re.match(pattern, value_str):
                        msg = validation.get("message", f"Value does not match pattern {pattern!r}")
                        raise ValueError(f"Field '{field_id}': {msg}")

                # Reject argv-level flag injection and filesystem path traversal
                self._reject_injected_args(field_id, value_str)
                self._reject_path_traversal(value_str)

    def build_command(self, plugin_id: str, inputs: Dict) -> Optional[List[str]]:
        """
        Build command from plugin template and user inputs.

        Args:
            plugin_id: Plugin identifier
            inputs: User input values

        Returns:
            Command as list of arguments
        """
        plugin = self.get_plugin(plugin_id)
        if not plugin:
            return None

        field_ids = {f.id for f in plugin.fields}
        inputs = {
            key: value
            for key, value in inputs.items()
            if (key not in _INTERNAL_CONTROL_FIELDS or key in field_ids) and not str(key).startswith("__")
        }

        # Validate before normalisation so SELECT checks run against raw user values
        self._validate_inputs_against_schema(plugin, inputs)
        inputs = self._normalize_inputs(plugin, inputs)
        command = []

        for token in plugin.command_template:
            # Handle conditionals:
            # --if:condition:then:value
            # --if:condition:then:value:else:fallback
            if token.startswith("--if:"):
                parts = token.split(":")
                if len(parts) >= 4 and parts[2] == "then":
                    condition_var = parts[1]

                    # Correctly identify then/else segments
                    try:
                        else_idx = parts.index("else")
                        then_parts = parts[3:else_idx]
                        else_parts = parts[else_idx+1:]
                    except ValueError:
                        then_parts = parts[3:]
                        else_parts = []

                    condition = inputs.get(condition_var, False)
                    # For booleans or non-empty existence
                    if isinstance(condition, str) and condition.lower() == "false":
                        condition = False

                    active_parts = then_parts if condition else else_parts

                    for part in active_parts:
                        if interpolated := self._interpolate(part, inputs):
                            command.append(interpolated)
                continue

            if interpolated := self._interpolate(token, inputs):
                command.append(interpolated)

        return command

# Global plugin manager instance
plugin_manager: Optional[PluginManager] = None

async def init_plugins(plugins_dir: str) -> PluginManager:
    """Initialize plugin manager and load plugins"""
    global plugin_manager
    plugin_manager = PluginManager(plugins_dir)
    await plugin_manager.load_plugins()
    return plugin_manager

def get_plugin_manager() -> PluginManager:
    """Get plugin manager instance"""
    if plugin_manager is None:
        raise RuntimeError("Plugin manager not initialized")
    return plugin_manager

def get_plugin_check_latency_ms() -> float:
    """Measure plugin enumeration latency in milliseconds."""
    manager = get_plugin_manager()

    start = time.perf_counter()
    manager.list_plugins()

    return round(
        (time.perf_counter() - start) * 1000,
        2,
    )
