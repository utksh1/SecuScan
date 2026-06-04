from datetime import datetime, timedelta
from fastapi import HTTPException, Request, status
from collections import defaultdict
import asyncio

class RateLimiter:
    def __init__(self, requests_per_minute=10):
        self.requests_per_minute = requests_per_minute
        self.requests = defaultdict(list)
        self.cleanup_task = None

    async def check_rate_limit(self, key: str) -> bool:
        """Check if request exceeds rate limit"""
        now = datetime.now()
        minute_ago = now - timedelta(minutes=1)

        # Clean old requests
        self.requests[key] = [
            req_time for req_time in self.requests[key]
            if req_time > minute_ago
        ]

        if len(self.requests[key]) >= self.requests_per_minute:
            return False

        self.requests[key].append(now)
        return True

    async def enforce_limit(self, key: str, limit: int = None):
        """Raise HTTPException if rate limit exceeded"""
        limit = limit or self.requests_per_minute
        if not await self.check_rate_limit(key):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded: max {limit} requests per minute"
            )

scheduler_limiter = RateLimiter(requests_per_minute=5)

async def rate_limit_scheduler(request: Request):
    """Dependency to rate limit scheduler endpoints"""
    user_id = request.user.id if hasattr(request, 'user') else 'anonymous'
    await scheduler_limiter.enforce_limit(f"scheduler:{user_id}", limit=5)
