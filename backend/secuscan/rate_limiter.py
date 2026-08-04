"""
backend/secuscan/rate_limiter.py

Redis-backed sliding window rate limiter for scan execution endpoints.

Algorithm: Sliding window counter using Redis INCR + EXPIRE.
- Per-IP counters stored as Redis keys with TTL.
- Two-tier limits: per-minute (burst protection) and per-hour (sustained limit).
- Returns HTTP 429 with Retry-After header when limits are exceeded.
- When Redis is unavailable, falls back to in-memory rate limiting and logs
  an ERROR, so a Redis outage does not take down the scan service entirely.

Key schema:
  rate_limit:scan:{ip}:minute:{window_start_minute}  → request count
  rate_limit:scan:{ip}:hour:{window_start_hour}      → request count

Fallback:
  In-memory dictionary is used when Redis is unreachable to maintain
  rate limiting coverage. A circuit breaker periodically attempts to
  reconnect to Redis.
"""

import logging
import time
from collections import defaultdict
from typing import Dict, List, Optional

import redis.asyncio as aioredis
from fastapi import HTTPException, Request, status

logger = logging.getLogger(__name__)


class RateLimitExceeded(HTTPException):
    """Raised when a rate limit is exceeded. Caught by a global exception handler."""


class ScanRateLimiter:
    """
    Sliding window rate limiter for scan execution endpoints.

    Usage:
        limiter = ScanRateLimiter(redis_client, rate_limit=5, rate_window=60,
                                   burst_limit=10, burst_window=3600)
        await limiter.check(request)   # raises HTTP 429 if limit exceeded
    """

    def __init__(
        self,
        redis_client: Optional[aioredis.Redis],
        rate_limit: int,
        rate_window: int,
        burst_limit: int,
        burst_window: int,
    ) -> None:
        self._redis = redis_client
        self._rate_limit = rate_limit  # e.g. 5 requests
        self._rate_window = rate_window  # e.g. per 60 seconds
        self._burst_limit = burst_limit  # e.g. 10 requests
        self._burst_window = burst_window  # e.g. per 3600 seconds
        self._redis_failed = False
        self._fallback_history: Dict[str, List[float]] = defaultdict(list)

    async def reset(self) -> None:
        """Clear in-memory fallback state and reset circuit breaker."""

        self._fallback_history.clear()
        self._redis_failed = False

    def _get_client_ip(self, request: Request) -> str:
        """
        Extract the real client IP.
        Checks X-Forwarded-For first (for reverse-proxy / Docker deployments),
        falls back to direct connection address.
        """
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # X-Forwarded-For can be a comma-separated list; take the first
            return forwarded_for.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    def _make_key(self, ip: str, window_type: str, window_value: int) -> str:
        """Build a namespaced Redis key for this IP and time window."""
        return f"rate_limit:scan:{ip}:{window_type}:{window_value}"

    async def _check_fallback(self, request: Request) -> None:
        """In-memory fallback rate limit check used when Redis is down."""
        ip = self._get_client_ip(request)
        now = time.time()

        minute_window = int(now // self._rate_window)
        hour_window = int(now // self._burst_window)

        bucket_min = f"{ip}:minute:{minute_window}"
        bucket_hr = f"{ip}:hour:{hour_window}"

        # Clean stale entries
        cutoff = now - max(self._rate_window, self._burst_window)
        for key in list(self._fallback_history.keys()):
            self._fallback_history[key] = [
                ts for ts in self._fallback_history[key] if ts > cutoff
            ]
            if not self._fallback_history[key]:
                del self._fallback_history[key]

        # Check per-minute limit
        minute_count = len(self._fallback_history[bucket_min]) + 1
        if minute_count > self._rate_limit:
            retry_after = self._rate_window - (int(now) % self._rate_window)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "error": "rate_limit_exceeded",
                    "message": (
                        f"Scan rate limit exceeded: maximum {self._rate_limit} "
                        f"requests per {self._rate_window} seconds."
                    ),
                    "retry_after": retry_after,
                },
                headers={"Retry-After": str(retry_after)},
            )

        # Check per-hour limit
        hour_count = len(self._fallback_history[bucket_hr]) + 1
        if hour_count > self._burst_limit:
            retry_after = self._burst_window - (int(now) % self._burst_window)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "error": "burst_limit_exceeded",
                    "message": (
                        f"Hourly scan limit exceeded: maximum {self._burst_limit} "
                        f"requests per hour."
                    ),
                    "retry_after": retry_after,
                },
                headers={"Retry-After": str(retry_after)},
            )

        # Record the request
        self._fallback_history[bucket_min].append(now)
        self._fallback_history[bucket_hr].append(now)

    async def check(self, request: Request) -> None:
        """
        Check rate limits for the incoming request.
        Raises HTTP 429 if either the per-minute or per-hour limit is exceeded.
        Falls back to in-memory rate limiting if Redis is unavailable.

        Args:
            request: The incoming FastAPI request object.

        Raises:
            HTTPException: 429 Too Many Requests with Retry-After header.
        """
        # If rate limiting is disabled (limit set to 0), pass through immediately
        if self._rate_limit == 0:
            return

        # If Redis is not configured, use in-memory fallback
        if self._redis is None:
            logger.warning(
                "ScanRateLimiter: Redis client is None — using in-memory fallback. "
                "Configure REDIS_URL to enable Redis-backed rate limiting."
            )
            return await self._check_fallback(request)

        ip = self._get_client_ip(request)
        now = int(time.time())

        # If Redis previously failed, try to reconnect (circuit breaker)
        if self._redis_failed:
            try:
                await self._redis.ping()
                self._redis_failed = False
                logger.info("ScanRateLimiter: Redis connection restored.")
            except Exception:
                logger.error(
                    "ScanRateLimiter: Redis still unreachable, using in-memory fallback."
                )
                return await self._check_fallback(request)

        try:
            # ── Tier 1: Per-minute limit (burst protection) ──────────────────
            minute_window = now // self._rate_window
            minute_key = self._make_key(ip, "minute", minute_window)

            pipe = self._redis.pipeline()
            pipe.incr(minute_key)
            pipe.expire(minute_key, self._rate_window * 2)  # 2x TTL for safety
            results = await pipe.execute()
            minute_count = results[0]

            if minute_count > self._rate_limit:
                retry_after = self._rate_window - (now % self._rate_window)
                logger.warning(
                    "Rate limit exceeded (per-minute): ip=%s count=%d limit=%d",
                    ip,
                    minute_count,
                    self._rate_limit,
                )
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail={
                        "error": "rate_limit_exceeded",
                        "message": (
                            f"Scan rate limit exceeded: maximum {self._rate_limit} "
                            f"requests per {self._rate_window} seconds."
                        ),
                        "retry_after": retry_after,
                    },
                    headers={"Retry-After": str(retry_after)},
                )

            # ── Tier 2: Per-hour limit (sustained abuse protection) ──────────
            hour_window = now // self._burst_window
            hour_key = self._make_key(ip, "hour", hour_window)

            pipe2 = self._redis.pipeline()
            pipe2.incr(hour_key)
            pipe2.expire(hour_key, self._burst_window * 2)
            results2 = await pipe2.execute()
            hour_count = results2[0]

            if hour_count > self._burst_limit:
                retry_after = self._burst_window - (now % self._burst_window)
                logger.warning(
                    "Rate limit exceeded (per-hour): ip=%s count=%d limit=%d",
                    ip,
                    hour_count,
                    self._burst_limit,
                )
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail={
                        "error": "burst_limit_exceeded",
                        "message": (
                            f"Hourly scan limit exceeded: maximum {self._burst_limit} "
                            f"requests per hour."
                        ),
                        "retry_after": retry_after,
                    },
                    headers={"Retry-After": str(retry_after)},
                )

        except HTTPException:
            # Re-raise 429s — don't swallow them in the Redis error handler
            raise
        except Exception as exc:
            # Redis connection error, timeout, etc. — fail over, log, continue
            self._redis_failed = True
            logger.error(
                "ScanRateLimiter: Redis error (%s), switching to in-memory fallback.",
                exc,
            )
            return await self._check_fallback(request)


def make_scan_rate_limiter(
    redis_client: Optional[aioredis.Redis],
    rate_limit: int,
    rate_window: int,
    burst_limit: int,
    burst_window: int,
) -> ScanRateLimiter:
    """
    Factory function for creating a ScanRateLimiter.
    Intended to be called once at app startup and reused across requests.
    """
    return ScanRateLimiter(
        redis_client=redis_client,
        rate_limit=rate_limit,
        rate_window=rate_window,
        burst_limit=burst_limit,
        burst_window=burst_window,
    )


async def check_scan_rate_limit(request: Request) -> None:
    """FastAPI dependency that checks scan rate limits for scan-triggering endpoints.

    Retrieves the ``ScanRateLimiter`` instance from ``request.app.state``
    (initialized during app startup) and delegates to its ``check`` method.
    """
    limiter = getattr(request.app.state, "scan_rate_limiter", None)
    if limiter:
        await limiter.check(request)
