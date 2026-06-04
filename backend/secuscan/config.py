"""
Configuration management for SecuScan backend
"""

from pathlib import Path
from typing import Any, List, Optional
from pydantic import field_validator
from pydantic_settings import BaseSettings
import base64
import hashlib

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # Server Configuration
    bind_address: str = "127.0.0.1"
    bind_port: int = 8000
    debug: bool = True

    # Primary data store
    database_path: str = str(PROJECT_ROOT / "data" / "secuscan.db")

    # Cache store (In-memory used when redis_url is None or Docker is disabled)
    redis_url: Optional[str] = None
    cache_ttl_seconds: int = 30

    # Storage
    data_dir: str = str(PROJECT_ROOT / "data")
    raw_output_dir: str = str(PROJECT_ROOT / "data" / "raw")
    reports_dir: str = str(PROJECT_ROOT / "data" / "reports")
    plugins_dir: str = str(PROJECT_ROOT.parent / "plugins")
    wordlists_dir: str = str(PROJECT_ROOT / "wordlists")

    # Security
    safe_mode_default: bool = True
    dns_resolution_timeout_seconds: float = 1.5
    dns_cache_ttl_seconds: int = 60
    dns_rebind_check: bool = True
    require_consent: bool = True
    allow_loopback_scans: bool = True
    allowed_networks: List[str] = ["127.0.0.1", "192.168.*.*", "10.*.*.*", "172.16.*.*"]
    cors_allowed_origins: List[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8080",
        "http://127.0.0.1:8080",
        "http://localhost:4173",
        "http://127.0.0.1:4173",
    ]
    cors_allowed_methods: List[str] = ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]
    cors_allowed_headers: List[str] = ["Content-Type", "Authorization", "Accept", "Origin"]
    cors_allow_credentials: bool = True
    plugin_signature_key: Optional[str] = None
    enforce_plugin_signatures: bool = False
    vault_key: Optional[str] = None
    vault_key_previous: Optional[str] = None
    denied_capabilities: List[str] = []
    admin_api_key: Optional[str] = None

    # Network Policy Configuration
    network_allowlist: List[str] = []  # IPs/networks to allow (CIDR)
    network_denylist: List[str] = [    # IPs/networks to deny (CIDR)
        "169.254.169.254/32",          # AWS metadata
        "169.254.0.0/16",              # Reserved/metadata
        "127.0.0.0/8",                 # Loopback (for remote execution)
        "10.0.0.0/8",                  # Private RFC 1918
        "172.16.0.0/12",               # Private RFC 1918
        "192.168.0.0/16",              # Private RFC 1918
        "100.64.0.0/10",               # Carrier-grade NAT (RFC 6598)
        "fc00::/7",                    # IPv6 Unique Local Address
        "fe80::/10",                   # IPv6 Link-local
        "::1/128",                     # IPv6 Loopback
    ]
    network_audit_log_file: str = str(PROJECT_ROOT / "logs" / "network.audit.log")
    network_audit_retention_days: int = 90
    enforce_network_policy: bool = True
    network_policy_failure_mode: str = "block"  # "block" or "log_only"

    # Rate Limiting
    max_concurrent_tasks: int = 3
    max_tasks_per_hour: int = 50
    max_requests_per_minute: int = 100

    # Endpoint rate limiting buckets
    rate_limit_task_start_limit: int = 50
    rate_limit_task_start_window: int = 3600

    rate_limit_vault_limit: int = 15
    rate_limit_vault_window: int = 60

    rate_limit_report_download_limit: int = 30
    rate_limit_report_download_window: int = 60

    rate_limit_read_heavy_limit: int = 100
    rate_limit_read_heavy_window: int = 60

    trusted_proxies: List[str] = ["127.0.0.1", "::1"]

    # Sandbox
    docker_enabled: bool = False
    sandbox_timeout: int = 600  # seconds
    sandbox_cpu_quota: float = 0.5
    sandbox_memory_mb: int = 512
    docker_network: str = "restricted"  # Docker network name for sandboxed containers

    # Task-start payload limits (tunable via env vars)
    task_start_max_body_bytes: int = 64_000       # 64 KB total JSON body
    task_start_max_field_length: int = 1_000      # max chars per string input value
    task_start_max_array_length: int = 50         # max items in any list/multiselect input

    # Parser sandbox limits
    parser_sandbox_timeout_seconds: int = 30
    parser_sandbox_max_output_bytes: int = 8 * 1024 * 1024  # 8 MB

    # Logging
    log_level: str = "INFO"
    log_file: str = str(PROJECT_ROOT / "logs" / "secuscan.log")

    class Config:
        env_prefix = "SECUSCAN_"
        case_sensitive = False

    @field_validator(
        "cors_allowed_origins",
        "cors_allowed_methods",
        "cors_allowed_headers",
        "trusted_proxies",
        "network_allowlist",
        "network_denylist",
        mode="before",
    )
    @classmethod
    def parse_csv_or_list(cls, value: Any) -> Any:
        """Allow comma-separated env values in addition to JSON arrays."""
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @property
    def base_url(self) -> str:
        """Full base URL for the API"""
        return f"http://{self.bind_address}:{self.bind_port}"

    @property
    def resolved_vault_key(self) -> bytes:
        """Return a deterministic 32-byte key for credential vault encryption.

        Raises RuntimeError when neither SECUSCAN_VAULT_KEY nor
        SECUSCAN_PLUGIN_SIGNATURE_KEY is set, rather than falling back to the
        insecure hardcoded string that was present in earlier versions.
        """
        seed = self.vault_key or self.plugin_signature_key
        if not seed:
            raise RuntimeError(
                "SECUSCAN_VAULT_KEY is not set. "
                "Set a strong random value in your environment or .env file before "
                "starting the server. "
                "Example: python -c \"import secrets; print(secrets.token_hex(32))\""
            )
        digest = hashlib.sha256(seed.encode("utf-8")).digest()
        return base64.urlsafe_b64encode(digest)

    @property
    def resolved_vault_key_previous(self) -> Optional[bytes]:
        """Return deterministic 32-byte key for previous vault key if present.

        Returns None when no previous key is configured.
        """
        seed = self.vault_key_previous or self.plugin_signature_key
        if not seed:
            return None
        digest = hashlib.sha256(seed.encode("utf-8")).digest()
        return base64.urlsafe_b64encode(digest)

    def ensure_directories(self) -> None:
        """Create necessary directories if they don't exist"""
        for directory in [
            self.raw_output_dir,
            self.reports_dir,
            self.wordlists_dir,
            Path(self.log_file).parent,
        ]:
            Path(directory).mkdir(parents=True, exist_ok=True)

        # Create gitkeep files
        (Path(self.raw_output_dir) / ".gitkeep").touch()
        (Path(self.reports_dir) / ".gitkeep").touch()

# Global settings instance
settings = Settings()
