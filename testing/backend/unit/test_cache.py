"""
Unit tests for backend.secuscan.cache.CacheClient.

Covers:
- _sweep_expired removes keys whose TTL has passed
- _sweep_expired does not remove non-expired keys
- _evict_lru evicts least-recently-used entries when over capacity
- _evict_lru does nothing when under capacity
- get_json returns None for expired keys
- get_json updates access order when key is retrieved
- set_json stores value with correct TTL and triggers eviction when full
- delete_prefix removes all keys with the given prefix
- size property reflects the number of stored entries
- stats property reports size, max_entries, eviction_count, sweep_count
"""

import time

import pytest

from backend.secuscan.cache import CacheClient


def _future(seconds: int) -> float:
    """Return a unix timestamp *seconds* in the future."""
    return time.time() + seconds


class TestSweepExpired:
    def test_removes_expired_keys(self):
        """_sweep_expired deletes entries whose expiry time has passed."""
        client = CacheClient(max_entries=100)
        client._data["key1"] = "value1"
        client._expires["key1"] = time.time() - 1  # already expired
        client._access_order["key1"] = time.time()

        client._sweep_expired()

        assert "key1" not in client._data
        assert "key1" not in client._expires
        assert "key1" not in client._access_order
        assert client._sweep_count == 1

    def test_preserves_non_expired_keys(self):
        """_sweep_expired keeps entries whose expiry is still in the future."""
        client = CacheClient(max_entries=100)
        client._data["key1"] = "value1"
        client._expires["key1"] = time.time() + 3600  # expires in 1 hour
        client._access_order["key1"] = time.time()

        client._sweep_expired()

        assert "key1" in client._data
        assert client._sweep_count == 0


class TestEvictLru:
    def test_evicts_when_over_capacity(self):
        """_evict_lru removes the least-recently-used entries."""
        client = CacheClient(max_entries=3)
        # Insert entries with decreasing access times
        now = time.time()
        for i, key in enumerate(["a", "b", "c", "d"]):
            client._data[key] = f"val{i}"
            client._expires[key] = _future(3600)
            client._access_order[key] = now - (3 - i)

        client._evict_lru()

        # With max_entries=3, one entry should be evicted (the LRU one)
        assert len(client._data) == 3
        assert client._eviction_count >= 1
        # The oldest entry ("a") should have been evicted
        assert "a" not in client._data

    def test_does_nothing_when_under_capacity(self):
        """_evict_lru is a no-op when data size is below max_entries."""
        client = CacheClient(max_entries=10)
        client._data["key1"] = "value1"
        client._expires["key1"] = _future(3600)
        client._access_order["key1"] = time.time()

        client._evict_lru()

        assert "key1" in client._data
        assert client._eviction_count == 0


@pytest.mark.asyncio
class TestGetJson:
    async def test_returns_none_for_missing_key(self):
        client = CacheClient()
        result = await client.get_json("nonexistent")
        assert result is None

    async def test_returns_none_for_expired_key(self):
        """An expired key returns None and is cleaned up."""
        client = CacheClient()
        client._data["key1"] = {"x": 1}
        client._expires["key1"] = time.time() - 1
        client._access_order["key1"] = time.time() - 1

        result = await client.get_json("key1")

        assert result is None

    async def test_updates_access_order(self):
        """Retrieving a valid key updates its access timestamp."""
        client = CacheClient()
        old_time = time.time() - 100
        client._data["key1"] = "value1"
        client._expires["key1"] = _future(3600)
        client._access_order["key1"] = old_time

        await client.get_json("key1")

        assert client._access_order["key1"] > old_time

    async def test_returns_stored_value(self):
        """A valid key returns its stored value."""
        client = CacheClient()
        client._data["key1"] = {"x": 1, "y": 2}
        client._expires["key1"] = _future(3600)
        client._access_order["key1"] = time.time()

        result = await client.get_json("key1")

        assert result == {"x": 1, "y": 2}


@pytest.mark.asyncio
class TestSetJson:
    async def test_stores_value_with_ttl(self):
        """set_json stores the value and sets expiry based on TTL."""
        client = CacheClient()
        await client.set_json("key1", {"a": 1}, ttl=600)

        assert client._data["key1"] == {"a": 1}
        assert 590 < client._expires["key1"] - time.time() < 610

    async def test_uses_settings_ttl_when_ttl_not_provided(self, monkeypatch):
        """When ttl is None, settings.cache_ttl_seconds is used."""
        # Use a real Settings-like object for the override so we don't mutate the global.
        class FakeSettings:
            cache_ttl_seconds = 42

        client = CacheClient()
        monkeypatch.setattr("backend.secuscan.cache.settings", FakeSettings())

        await client.set_json("key1", "val", ttl=None)

        assert 40 < client._expires["key1"] - time.time() < 50

    async def test_triggers_eviction_when_full(self):
        """set_json calls _evict_lru when at capacity with a new key."""
        client = CacheClient(max_entries=2)
        await client.set_json("key1", "val1", ttl=3600)
        await client.set_json("key2", "val2", ttl=3600)
        # Now at capacity, adding a new key should evict
        await client.set_json("key3", "val3", ttl=3600)

        assert len(client._data) <= 2
        assert client._eviction_count >= 1


@pytest.mark.asyncio
class TestDeletePrefix:
    async def test_removes_matching_keys(self):
        """delete_prefix removes all keys that start with the given prefix."""
        client = CacheClient()
        client._data["api:users:1"] = "u1"
        client._data["api:users:2"] = "u2"
        client._data["api:posts:1"] = "p1"
        client._data["cache:stats"] = "s"

        await client.delete_prefix("api:users")

        assert "api:users:1" not in client._data
        assert "api:users:2" not in client._data
        assert "api:posts:1" in client._data
        assert "cache:stats" in client._data

    async def test_handles_empty_result(self):
        """delete_prefix on a prefix with no matches is a no-op."""
        client = CacheClient()
        client._data["key1"] = "val1"

        await client.delete_prefix("nonexistent")

        assert "key1" in client._data


class TestProperties:
    def test_size_returns_entry_count(self):
        client = CacheClient()
        client._data["key1"] = "val1"
        client._data["key2"] = "val2"
        assert client.size == 2

    def test_stats_includes_eviction_and_sweep_counts(self):
        client = CacheClient(max_entries=5)
        client._eviction_count = 3
        client._sweep_count = 7
        stats = client.stats
        assert stats["eviction_count"] == 3
        assert stats["sweep_count"] == 7
        assert stats["max_entries"] == 5
