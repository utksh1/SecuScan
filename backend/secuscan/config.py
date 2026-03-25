"""
Configuration management for SecuScan backend
"""

from pathlib import Path
from typing import List, Optional
from pydantic_settings import BaseSettings

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
    
    @property
    def base_url(self) -> str:
        """Full base URL for the API"""
        return f"http://{self.bind_address}:{self.bind_port}"
    
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
