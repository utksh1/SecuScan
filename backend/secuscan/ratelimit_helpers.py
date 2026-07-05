"""
Redis key-builder helpers for ScanRateLimiter.

Extracted from rate_limiter.py so _make_key can be unit-tested without
pulling in the redis.asyncio / fastapi import chain.

Public API
----------
RateLimiterKeyBuilder.make_key(ip: str, window_type: str, window_value: int) -> str
    Builds the namespaced Redis key for a per-IP rate-limit bucket.

Key format: ``rate_limit:scan:{ip}:{window_type}:{window_value}``
"""

from __future__ import annotations


class RateLimiterKeyBuilder:
    """Pure key-formatter for ScanRateLimiter Redis keys."""

    @staticmethod
    def make_key(ip: str, window_type: str, window_value: int) -> str:
        """Build a namespaced Redis key for this IP and time window.

        Args:
            ip:          Client IP address (e.g. "192.168.1.1").
            window_type: Time-window label, typically ``"minute"`` or ``"hour"``.
            window_value: Unix timestamp of the window start (seconds).

        Returns:
            Redis key string of the form:
            ``rate_limit:scan:{ip}:{window_type}:{window_value}``
        """
        return f"rate_limit:scan:{ip}:{window_type}:{window_value}"
