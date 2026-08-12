"""
In-memory cache helpers for API responses.
"""

import json
from typing import Any, Optional, Dict
import time
import logging

from .config import settings

logger = logging.getLogger(__name__)

DEFAULT_MAX_ENTRIES = 10_000
SWEEP_EVICT_FRACTION = 0.25
OPPORTUNISTIC_SWEEP_INTERVAL = 50


class CacheClient:
    """In-memory dictionary based cache client with TTL, size limit, and LRU eviction."""

    def __init__(self, url: Optional[str] = None, max_entries: int = DEFAULT_MAX_ENTRIES):
        self.url = url
        self._data: Dict[str, Any] = {}
        self._expires: Dict[str, float] = {}
        self._access_order: Dict[str, float] = {}
        self.max_entries = max_entries
        self._write_count = 0


    async def disconnect(self):
        self._data.clear()
        self._expires.clear()
        self._access_order.clear()

    def _sweep_expired(self):
        now = time.time()
        keys = [k for k, exp in list(self._expires.items()) if exp <= now]
        for k in keys:
            self._data.pop(k, None)
            self._expires.pop(k, None)
            self._access_order.pop(k, None)
        if keys:
            logger.debug("Swept %d expired keys", len(keys))

    def _evict_lru(self):
        """Evict the least recently used entries when over capacity."""
        if len(self._data) < self.max_entries:
            return
        sorted_keys = sorted(self._access_order, key=lambda k: self._access_order[k])
        evict_count = max(1, int(self.max_entries * SWEEP_EVICT_FRACTION))
        for k in sorted_keys[:evict_count]:
            self._data.pop(k, None)
            self._expires.pop(k, None)
            self._access_order.pop(k, None)

    async def get_json(self, key: str) -> Optional[Any]:
        """Retrieve and parse JSON from memory, respecting TTL."""
        now = time.time()
        expiry = self._expires.get(key)

        if expiry and now > expiry:
            self._data.pop(key, None)
            self._expires.pop(key, None)
            self._access_order.pop(key, None)
            return None

        if key in self._data:
            self._access_order[key] = now

        return self._data.get(key)

    async def set_json(self, key: str, value: Any, ttl: Optional[int] = None):
        """Store value in memory with optional TTL."""
        if len(self._data) >= self.max_entries and key not in self._data:
            self._evict_lru()

        self._data[key] = value
        actual_ttl = ttl or settings.cache_ttl_seconds
        self._expires[key] = time.time() + actual_ttl
        self._access_order[key] = time.time()
        self._write_count += 1

        if self._write_count % OPPORTUNISTIC_SWEEP_INTERVAL == 0:
            self._sweep_expired()

    async def delete_prefix(self, prefix: str):
        """Delete all keys starting with prefix."""
        to_delete = [k for k in self._data.keys() if k.startswith(prefix)]
        for k in to_delete:
            self._data.pop(k, None)
            self._expires.pop(k, None)
            self._access_order.pop(k, None)

    @property
    def size(self) -> int:
        return len(self._data)


# Global cache instance
cache: Optional[CacheClient] = None


async def init_cache(url: Optional[str] = None) -> CacheClient:
    """Initialize the global cache instance."""
    global cache
    cache = CacheClient(url)
    await cache.connect()
    return cache


async def invalidate_cache(*prefixes: str):
    """Clear caches by prefix."""
    global cache
    if cache is None:
        return
    for prefix in prefixes:
        await cache.delete_prefix(prefix)


async def get_cache() -> CacheClient:
    global cache
    if cache is None:
        cache = CacheClient()
    return cache


async def invalidate_view_cache():
    global cache
    if cache is not None:
        for prefix in ["summary:", "findings:", "reports:", "tasks:"]:
            await cache.delete_prefix(prefix)


async def invalidate_plugin_caches():
    global cache
    if cache is not None:
        for prefix in ["summary:", "plugins:"]:
            await cache.delete_prefix(prefix)
