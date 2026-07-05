"""
Import-safe rate limiter helpers extracted from backend/secuscan/rate_limiter.py.

This module provides pure helper functions without requiring redis or FastAPI.
"""


class RateLimiterKeyBuilder:
    """Builds Redis key strings for rate limiting."""

    @staticmethod
    def make_key(ip: str, window_type: str, window_value: int) -> str:
        """Build a namespaced Redis key for this IP and time window."""
        return f"rate_limit:scan:{ip}:{window_type}:{window_value}"
