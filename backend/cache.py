"""
In-memory cache helpers for API responses.
"""

import json
from typing import Any, Optional, Dict
import time

from .config import settings


class CacheClient:
    """In-memory dictionary based cache client."""

    def __init__(self, url: Optional[str] = None):
        self.url = url
        self._data: Dict[str, Any] = {}
        self._expires: Dict[str, float] = {}

    async def connect(self):
        """No connection needed for in-memory cache."""
        pass

    async def disconnect(self):
        """Clear cache on disconnect."""
        self._data.clear()
        self._expires.clear()

    async def get_json(self, key: str) -> Optional[Any]:
        """Retrieve and parse JSON from memory, respecting TTL."""
        now = time.time()
        expiry = self._expires.get(key)
        
        if expiry and now > expiry:
            # Clean up expired item
            self._data.pop(key, None)
            self._expires.pop(key, None)
            return None
            
        return self._data.get(key)

    async def set_json(self, key: str, value: Any, ttl: Optional[int] = None):
        """Store value in memory with optional TTL."""
        self._data[key] = value
        actual_ttl = ttl or settings.cache_ttl_seconds
        self._expires[key] = time.time() + actual_ttl

    async def delete_prefix(self, prefix: str):
        """Delete all keys starting with prefix."""
        to_delete = [k for k in self._data.keys() if k.startswith(prefix)]
        for k in to_delete:
            self._data.pop(k, None)
            self._expires.pop(k, None)


# Global cache instance
cache: Optional[CacheClient] = None


async def init_cache(url: Optional[str] = None) -> CacheClient:
    """Initialize the global cache instance."""
    global cache
    cache = CacheClient(url)
    await cache.connect()
    return cache


async def get_cache() -> CacheClient:
    """Get the global cache instance."""
    if cache is None:
        raise RuntimeError("Cache not initialized")
    return cache
