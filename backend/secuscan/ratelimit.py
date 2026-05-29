"""
Rate limiting for task execution and endpoints
"""

from collections import defaultdict
from datetime import datetime, timedelta
from typing import Tuple, Dict, List
import asyncio

from fastapi import Request, Response, HTTPException
from .config import settings


class RateLimiter:
    """Rate limiter for controlling task execution frequency"""

    def __init__(self):
        self.task_history: Dict[str, List[datetime]] = defaultdict(list)
        self.lock = asyncio.Lock()

    async def can_execute(
        self,
        plugin_id: str,
        max_per_hour: int = 50,
        client_id: str = "global",
    ) -> Tuple[bool, str]:
        """
        Check if a task can be executed based on rate limits.

        Each (client_id, plugin_id) pair has its own independent quota so
        one client exhausting their limit does not block other clients from
        running the same plugin.

        Args:
            plugin_id: Plugin identifier
            max_per_hour: Maximum tasks per hour for this (client, plugin) pair
            client_id: Opaque client identifier (IP, API key, user ID, etc.).
                       Defaults to ``"global"`` for backwards-compatible callers
                       that do not supply a client identity.

        Returns:
            Tuple of (allowed, error_message)
        """
        bucket = f"{client_id}:{plugin_id}"

        async with self.lock:
            now = datetime.now()
            hour_ago = now - timedelta(hours=1)

            # Clean old entries for this bucket
            self.task_history[bucket] = [
                ts for ts in self.task_history[bucket]
                if ts > hour_ago
            ]

            recent_count = len(self.task_history[bucket])

            if recent_count >= max_per_hour:
                return False, f"Rate limit exceeded: {recent_count}/{max_per_hour} per hour"

            # Record this execution
            self.task_history[bucket].append(now)
            return True, ""

    async def reset(self, plugin_id: str = None):
        """Reset rate limits for a plugin (all clients) or all buckets"""
        async with self.lock:
            if plugin_id:
                # Remove every bucket that ends with :<plugin_id>
                keys_to_clear = [k for k in self.task_history if k.endswith(f":{plugin_id}")]
                for k in keys_to_clear:
                    self.task_history[k] = []
            else:
                self.task_history.clear()


class ConcurrentTaskLimiter:
    """Limits concurrent task execution"""

    def __init__(self, max_concurrent: int = 3):
        self.max_concurrent = max_concurrent
        self.running_tasks: List[str] = []
        self.lock = asyncio.Lock()

    async def acquire(self, task_id: str) -> Tuple[bool, str]:
        """
        Try to acquire a slot for task execution.

        Args:
            task_id: Task identifier

        Returns:
            Tuple of (acquired, error_message)
        """
        async with self.lock:
            if len(self.running_tasks) >= self.max_concurrent:
                return False, f"Maximum concurrent tasks ({self.max_concurrent}) reached"

            self.running_tasks.append(task_id)
            return True, ""

    async def release(self, task_id: str):
        """Release a task slot"""
        async with self.lock:
            if task_id in self.running_tasks:
                self.running_tasks.remove(task_id)

    async def get_available_slots(self) -> int:
        """Get number of available execution slots"""
        async with self.lock:
            return self.max_concurrent - len(self.running_tasks)


def resolve_client_identity(request: Request) -> str:
    """
    Resolves client identity in priority order:
    1. API Key: Check standard headers X-API-Key/X-Api-Key, or Authorization bearer/basic token
    2. Authenticated User: Check X-User-ID or request.state.user_id / request.state.user.id / request.state.user
    3. Client IP: Connection IP, respecting X-Forwarded-For *only* if the connection IP is a trusted proxy.
    """
    # 1. API Key Check
    for key_header in ("x-api-key", "x-key"):
        if value := request.headers.get(key_header):
            return f"apikey:{value}"

    if auth_header := request.headers.get("authorization"):
        # Strip scheme (Bearer/Basic/Token) to get raw key value
        if " " in auth_header:
            _, token = auth_header.split(" ", 1)
            return f"apikey:{token}"
        return f"apikey:{auth_header}"

    # 2. Authenticated User Check
    if user_id_header := request.headers.get("x-user-id"):
        return f"user:{user_id_header}"

    if hasattr(request, "state"):
        if hasattr(request.state, "user_id") and request.state.user_id:
            return f"user:{request.state.user_id}"
        if hasattr(request.state, "user"):
            user = request.state.user
            if isinstance(user, dict) and "id" in user:
                return f"user:{user['id']}"
            if hasattr(user, "id") and getattr(user, "id"):
                return f"user:{getattr(user, 'id')}"
            if isinstance(user, str) and user:
                return f"user:{user}"

    # 3. Client IP Check (with trusted proxy support)
    client_ip = request.client.host if request.client else "127.0.0.1"

    if client_ip in settings.trusted_proxies and "x-forwarded-for" in request.headers:
        xff = request.headers["x-forwarded-for"]
        # The first IP in X-Forwarded-For is the real client IP
        if ips := [ip.strip() for ip in xff.split(",") if ip.strip()]:
            client_ip = ips[0]

    return f"ip:{client_ip}"


class EndpointRateLimiter:
    """
    Sliding window rate limiter applied as a FastAPI dependency.
    """
    def __init__(self, bucket_name: str, limit: int, window_seconds: int):
        self.bucket_name = bucket_name
        self.limit = limit
        self.window_seconds = window_seconds
        self.history: Dict[str, List[datetime]] = defaultdict(list)
        self.lock = asyncio.Lock()

    async def __call__(self, request: Request, response: Response):
        identity = resolve_client_identity(request)

        async with self.lock:
            now = datetime.now()
            cutoff = now - timedelta(seconds=self.window_seconds)

            # Filter history to keep only timestamps within the sliding window
            self.history[identity] = [ts for ts in self.history[identity] if ts > cutoff]

            recent_count = len(self.history[identity])

            if recent_count >= self.limit:
                # Calculate Retry-After based on the oldest request in the current window
                oldest_ts = self.history[identity][0]
                reset_at = oldest_ts + timedelta(seconds=self.window_seconds)
                retry_after = max(1, int((reset_at - now).total_seconds()))

                raise HTTPException(
                    status_code=429,
                    detail=f"Rate limit exceeded for {self.bucket_name}. Limit is {self.limit} requests per {self.window_seconds} seconds.",
                    headers={
                        "Retry-After": str(retry_after),
                        "X-RateLimit-Limit": str(self.limit),
                        "X-RateLimit-Remaining": "0",
                        "X-RateLimit-Reset": str(retry_after),
                    }
                )

            # Record the new request
            self.history[identity].append(now)

            # Set response headers
            remaining = self.limit - len(self.history[identity])
            first_ts = self.history[identity][0]
            reset_in = max(1, int((first_ts + timedelta(seconds=self.window_seconds) - now).total_seconds()))

            response.headers["X-RateLimit-Limit"] = str(self.limit)
            response.headers["X-RateLimit-Remaining"] = str(remaining)
            response.headers["X-RateLimit-Reset"] = str(reset_in)

    async def reset(self):
        """Clear all rate limiting history for this bucket."""
        async with self.lock:
            self.history.clear()


# Global instances
rate_limiter = RateLimiter()
concurrent_limiter = ConcurrentTaskLimiter()

# Route-specific limiters
task_start_limiter = EndpointRateLimiter(
    bucket_name="task_start",
    limit=settings.rate_limit_task_start_limit,
    window_seconds=settings.rate_limit_task_start_window
)

vault_limiter = EndpointRateLimiter(
    bucket_name="vault",
    limit=settings.rate_limit_vault_limit,
    window_seconds=settings.rate_limit_vault_window
)

report_download_limiter = EndpointRateLimiter(
    bucket_name="report_download",
    limit=settings.rate_limit_report_download_limit,
    window_seconds=settings.rate_limit_report_download_window
)

read_heavy_limiter = EndpointRateLimiter(
    bucket_name="read_heavy",
    limit=settings.rate_limit_read_heavy_limit,
    window_seconds=settings.rate_limit_read_heavy_window
)


async def reset_all_endpoint_limiters():
    """Reset rate limiting history for all route-specific buckets."""
    await task_start_limiter.reset()
    await vault_limiter.reset()
    await report_download_limiter.reset()
    await read_heavy_limiter.reset()
