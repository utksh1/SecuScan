"""
Unit tests for CacheClient synchronous members.

Tests the internal _sweep_expired, _evict_lru, size property, and stats
property directly against the real CacheClient class imported from
backend.secuscan.cache.
"""

import time
from backend.secuscan.cache import CacheClient


# ---------------------------------------------------------------------------
# _sweep_expired
# ---------------------------------------------------------------------------

def test_sweep_expired_removes_expired_keys():
    """Keys past their TTL are removed on sweep."""
    cache = CacheClient()
    # Manually set expiry in the past
    past = time.time() - 10
    cache._data["key1"] = "value1"
    cache._expires["key1"] = past
    cache._access_order["key1"] = past
    cache._data["key2"] = "value2"
    cache._expires["key2"] = past
    cache._access_order["key2"] = past
    # key3 is not expired
    cache._data["key3"] = "value3"
    cache._expires["key3"] = time.time() + 3600
    cache._access_order["key3"] = time.time()

    cache._sweep_expired()

    assert "key1" not in cache._data
    assert "key2" not in cache._data
    assert "key3" in cache._data
    assert cache._sweep_count == 2


def test_sweep_expired_with_no_expired_keys():
    """Sweep is a no-op when no keys are expired."""
    cache = CacheClient()
    future = time.time() + 3600
    cache._data["key1"] = "value1"
    cache._expires["key1"] = future
    cache._access_order["key1"] = time.time()

    cache._sweep_expired()

    assert "key1" in cache._data
    assert cache._sweep_count == 0


def test_sweep_expired_empty_cache():
    """Sweep on empty cache is safe."""
    cache = CacheClient()
    cache._sweep_expired()
    assert cache._sweep_count == 0


# ---------------------------------------------------------------------------
# _evict_lru
# ---------------------------------------------------------------------------

def test_evict_lru_removes_least_recently_used_entries():
    """When over capacity, LRU entries are evicted."""
    cache = CacheClient(max_entries=3)
    now = time.time()
    for i in range(3):
        cache._data[f"key{i}"] = f"value{i}"
        cache._expires[f"key{i}"] = now + 3600
        cache._access_order[f"key{i}"] = now + i

    # key0 was accessed first, should be evicted first
    cache._evict_lru()

    assert "key0" not in cache._data
    assert "key1" in cache._data
    assert "key2" in cache._data
    assert cache._eviction_count == 1


def test_evict_lru_multiple_evictions():
    """Eviction removes multiple entries per call (SWEEP_EVICT_FRACTION of max)."""
    cache = CacheClient(max_entries=5)
    now = time.time()
    for i in range(5):
        cache._data[f"key{i}"] = f"value{i}"
        cache._expires[f"key{i}"] = now + 3600
        cache._access_order[f"key{i}"] = now + i

    cache._evict_lru()

    # SWEEP_EVICT_FRACTION = 0.25, max_entries = 5, evict_count = max(1, int(5*0.25)) = max(1, 1) = 1
    # Wait, 5 * 0.25 = 1.25, int(1.25) = 1, max(1, 1) = 1
    # So 1 entry is evicted per call
    assert len(cache._data) == 4
    assert cache._eviction_count == 1


def test_evict_lru_no_op_under_capacity():
    """Eviction is a no-op when under max_entries."""
    cache = CacheClient(max_entries=5)
    now = time.time()
    for i in range(2):
        cache._data[f"key{i}"] = f"value{i}"
        cache._expires[f"key{i}"] = now + 3600
        cache._access_order[f"key{i}"] = now + i

    cache._evict_lru()

    assert len(cache._data) == 2
    assert cache._eviction_count == 0


def test_evict_lru_fires_at_exact_capacity():
    """Eviction triggers when len(_data) == max_entries (condition is < not <=)."""
    cache = CacheClient(max_entries=2)
    now = time.time()
    for i in range(2):
        cache._data[f"key{i}"] = f"value{i}"
        cache._expires[f"key{i}"] = now + 3600
        cache._access_order[f"key{i}"] = now + i

    cache._evict_lru()

    # evict_count = max(1, int(2 * 0.25)) = max(1, 0) = 1
    assert len(cache._data) == 1
    assert cache._eviction_count == 1


# ---------------------------------------------------------------------------
# size property
# ---------------------------------------------------------------------------

def test_size_returns_entry_count():
    """size property returns the number of cached entries."""
    cache = CacheClient()
    cache._data["a"] = 1
    cache._data["b"] = 2
    assert cache.size == 2


def test_size_empty_cache():
    """size is 0 for an empty cache."""
    cache = CacheClient()
    assert cache.size == 0


# ---------------------------------------------------------------------------
# stats property
# ---------------------------------------------------------------------------

def test_stats_returns_dict_with_expected_keys():
    """stats returns a dict with size, max_entries, eviction_count, sweep_count."""
    cache = CacheClient(max_entries=100)
    cache._eviction_count = 5
    cache._sweep_count = 3

    stats = cache.stats

    assert "size" in stats
    assert "max_entries" in stats
    assert "eviction_count" in stats
    assert "sweep_count" in stats
    assert stats["max_entries"] == 100
    assert stats["eviction_count"] == 5
    assert stats["sweep_count"] == 3


def test_stats_size_reflects_data_len():
    """stats.size mirrors the size property."""
    cache = CacheClient()
    cache._data["x"] = 1
    cache._data["y"] = 2
    stats = cache.stats
    assert stats["size"] == 2


def test_stats_default_counters_are_zero():
    """New cache has zero eviction and sweep counts."""
    cache = CacheClient()
    stats = cache.stats
    assert stats["eviction_count"] == 0
    assert stats["sweep_count"] == 0
