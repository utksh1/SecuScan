from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class BaseScanner(ABC):
    """
    Abstract base class for modular security scanners.
    Each scanner orchestrates one or more CLI tools to achieve a higher-level goal.
    """

    def __init__(self, task_id: str, db: Any):
        self.task_id = task_id
        self.db = db
        self.start_time = datetime.now()
        self._progress = 0.0

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable name of the scanner"""
        pass

    @property
    @abstractmethod
    def category(self) -> str:
        """Scanner category (e.g., Recon, Web, Network)"""
        pass

    @abstractmethod
    async def run(self, target: str, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the scanning logic.
        
        Returns:
            Dictionary containing findings, summary, and other structured data.
        """
        pass

    def update_progress(self, progress: float):
        """Update the scan progress (0.0 to 1.0)"""
        self._progress = min(1.0, max(0.0, progress))
        logger.debug(f"Task {self.task_id} progress: {self._progress * 100:.1f}%")

    def get_progress(self) -> float:
        return self._progress

    def normalize_severity(self, severity: str) -> str:
        """Standardize severity strings across different tools."""
        s = str(severity).lower()
        mapping = {
            "critical": "critical",
            "high": "high",
            "medium": "medium",
            "moderate": "medium",
            "low": "low",
            "info": "info",
            "informational": "info",
            "note": "info"
        }
        return mapping.get(s, "info")
