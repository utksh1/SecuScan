from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from datetime import datetime
import asyncio
import logging
import time

from ..telemetry import PluginTelemetry

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
        self.telemetry: Optional[PluginTelemetry] = None

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
            "note": "info",
        }
        return mapping.get(s, "info")

    async def _execute_command_timed(
        self,
        command: list,
        timeout: int = 300,
    ) -> tuple:
        """
        Run a subprocess command and return
        (output, exit_code, timed_out, timeout_reason, output_size_bytes).
        Populates self.telemetry automatically.

        Uses process.communicate() so stdout and stderr are collected together.
        On TimeoutError: kills the process and calls wait() exactly once —
        communicate() never completed, so there is no double-wait.
        """
        if self.telemetry is None:
            self.telemetry = PluginTelemetry(plugin_name=self.name)

        start = time.monotonic()
        timed_out = False
        timeout_reason = None
        output = ""
        exit_code = -1

        try:
            process = await asyncio.create_subprocess_exec(
                *command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )
            try:
                stdout, _ = await asyncio.wait_for(
                    process.communicate(), timeout=timeout
                )
                output = stdout.decode("utf-8", errors="replace")
                exit_code = process.returncode if process.returncode is not None else 0

            except asyncio.TimeoutError:
                # communicate() raised before finishing — process has not been
                # waited yet.  Kill then wait exactly once.
                process.kill()
                await process.wait()
                timed_out = True
                timeout_reason = f"Hard limit of {timeout}s exceeded"
                exit_code = -1

        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.error("Scanner command failed: %s", exc)
            output = f"Execution error: {exc}"
            exit_code = -1

        elapsed = time.monotonic() - start
        output_size = len(output.encode("utf-8", errors="replace"))

        self.telemetry.duration_seconds += elapsed
        self.telemetry.exit_code = exit_code
        self.telemetry.output_size_bytes += output_size
        self.telemetry.timed_out = timed_out
        self.telemetry.timeout_reason = timeout_reason

        return output, exit_code, timed_out, timeout_reason, output_size
