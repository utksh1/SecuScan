"""
Configuration management for SecuScan backend
"""

from pathlib import Path
from typing import Any, List, Optional
from pydantic import field_validator
from pydantic_settings import BaseSettings
import base64
import hashlib
import os

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
    knowledgebase_dir: str = str(PROJECT_ROOT / "data" / "knowledgebase")

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
    enforce_parser_integrity: bool = True
    parser_hash_algorithm: str = "sha256"
    vault_key: Optional[str] = None
    denied_capabilities: List[str] = []
    admin_api_key: Optional[str] = None

    # Network Policy Configuration
    network_allowlist: List[str] = []  # IPs/networks to allow (CIDR); empty = deny all egress
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

    scan_rate_limit: int = int(os.environ.get("SCAN_RATE_LIMIT", "5"))
    scan_rate_window: int = int(os.environ.get("SCAN_RATE_WINDOW_SECONDS", "60"))
    scan_burst_limit: int = int(os.environ.get("SCAN_BURST_LIMIT", "10"))
    scan_burst_window: int = int(os.environ.get("SCAN_BURST_WINDOW_SECONDS", "3600"))

    # Endpoint rate limiting buckets
    rate_limit_task_start_limit: int = 50
    rate_limit_task_start_window: int = 3600

    rate_limit_vault_limit: int = 15
    rate_limit_vault_window: int = 60

    rate_limit_report_download_limit: int = 30
    rate_limit_report_download_window: int = 60

    rate_limit_read_heavy_limit: int = 100
    rate_limit_read_heavy_window: int = 60

    # Scheduler tick: one trigger per 10 seconds allows legitimate external
    # callers while preventing a tight loop from forcing continuous workflow
    # execution and exhausting scan quotas.
    rate_limit_scheduler_tick_limit: int = 1
    rate_limit_scheduler_tick_window: int = 10

    trusted_proxies: List[str] = ["127.0.0.1", "::1"]

    # Sandbox
    docker_enabled: bool = False
    sandbox_timeout: int = 600  # seconds
    sandbox_cpu_quota: float = 0.5
    sandbox_memory_mb: int = 512
    sandbox_max_output_bytes: int = 5_242_880  # 5 MB
    sandbox_allow_network: bool = True
    docker_network: str = "restricted"  # Docker network name for sandboxed containers

    # Task-start payload limits (tunable via env vars)
    task_start_max_body_bytes: int = 64_000       # 64 KB total JSON body
    task_start_max_field_length: int = 1_000      # max chars per string input value
    task_start_max_array_length: int = 50         # max items in any list/multiselect input

    # Parser sandbox limits
    parser_sandbox_timeout_seconds: int = 30
    parser_sandbox_max_output_bytes: int = 8 * 1024 * 1024  # 8 MB

    # Workflow Configuration
    workflow_min_interval_seconds: int = 60

    # Notification SSRF Protection
    notification_ssrf_enabled: bool = True
    notification_allowed_ip_ranges: List[str] = []
    notification_blocked_ip_ranges: List[str] = [
        "169.254.169.254/32",
        "169.254.0.0/16",
        "127.0.0.0/8",
        "10.0.0.0/8",
        "172.16.0.0/12",
        "192.168.0.0/16",
        "100.64.0.0/10",
        "fc00::/7",
        "fe80::/10",
        "::1/128",
        "224.0.0.0/4",
        "ff00::/8",
        "0.0.0.0/8",
    ]
    notification_max_redirects: int = 0
    notification_allowed_ports: List[int] = [80, 443, 8080, 8443]

    # Logging
    log_level: str = "INFO"
    log_file: str = str(PROJECT_ROOT / "logs" / "secuscan.log")

    # AI Executive Summary (opt-in — feature off by default)
    ai_summary_enabled: bool = False
    ai_summary_api_key: str = ""
    ai_summary_base_url: str = ""
    ai_summary_model: str = "gpt-4o-mini"

    # SMTP Configuration for Email Notifications
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_username: Optional[str] = None
    smtp_password: Optional[str] = None
    smtp_from_email: str = "noreply@secuscan.io"
    smtp_use_tls: bool = True

    # Slack Webhook Configuration
    slack_webhook_url: Optional[str] = None

    # Public base URL used to build absolute links (e.g. report links) in
    # outbound notifications. Leave blank to emit relative paths.
    public_base_url: str = ""

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
        "notification_allowed_ip_ranges",
        "notification_blocked_ip_ranges",
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

    def ensure_directories(self) -> None:
        """Create necessary directories if they don't exist"""
        for directory in [
            self.raw_output_dir,
            self.reports_dir,
            self.wordlists_dir,
            self.knowledgebase_dir,
            Path(self.log_file).parent,
        ]:
            Path(directory).mkdir(parents=True, exist_ok=True)

        # Create gitkeep files
        (Path(self.raw_output_dir) / ".gitkeep").touch()
        (Path(self.reports_dir) / ".gitkeep").touch()

# Global settings instance
settings = Settings()
