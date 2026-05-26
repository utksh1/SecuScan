"""
Plugin execution telemetry for slow-scan diagnostics.
"""

from dataclasses import dataclass, field
from typing import Optional
import logging

logger = logging.getLogger(__name__)


@dataclass
class PluginTelemetry:
    plugin_name: str
    duration_seconds: float = 0.0
    exit_code: Optional[int] = None
    output_size_bytes: int = 0
    parser_time_seconds: float = 0.0
    timed_out: bool = False
    timeout_reason: Optional[str] = None
    resource_hints: dict = field(default_factory=dict)
    parser_error: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "plugin_name":         self.plugin_name,
            "duration_seconds":    round(self.duration_seconds, 3),
            "exit_code":           self.exit_code,
            "output_size_bytes":   self.output_size_bytes,
            "parser_time_seconds": round(self.parser_time_seconds, 3),
            "timed_out":           self.timed_out,
            "timeout_reason":      self.timeout_reason,
            "resource_hints":      self.resource_hints,
            "parser_error":        self.parser_error,
        }

    def log(self, task_id: str):
        logger.info(
            "plugin_telemetry task_id=%s plugin=%s duration=%.3fs "
            "exit_code=%s output_bytes=%d parser_time=%.3fs "
            "timed_out=%s timeout_reason=%s parser_error=%s",
            task_id,
            self.plugin_name,
            self.duration_seconds,
            self.exit_code,
            self.output_size_bytes,
            self.parser_time_seconds,
            self.timed_out,
            self.timeout_reason,
            self.parser_error,
        )

