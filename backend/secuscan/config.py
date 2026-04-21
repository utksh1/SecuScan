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
    require_consent: bool = True
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
    
    # Rate Limiting
    max_concurrent_tasks: int = 3
    max_tasks_per_hour: int = 50
    max_requests_per_minute: int = 100
    
    # Sandbox
    docker_enabled: bool = False
    sandbox_timeout: int = 600  # seconds
    sandbox_cpu_quota: float = 0.5
    sandbox_memory_mb: int = 512
    
    # Logging
    log_level: str = "INFO"
    log_file: str = str(PROJECT_ROOT / "logs" / "secuscan.log")
    
    class Config:
        env_prefix = "SECUSCAN_"
        case_sensitive = False

    @field_validator("cors_allowed_origins", "cors_allowed_methods", "cors_allowed_headers", mode="before")
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
        """Return a deterministic 32-byte key for credential vault encryption."""
        seed = self.vault_key or self.plugin_signature_key or "secuscan-dev-key"
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
