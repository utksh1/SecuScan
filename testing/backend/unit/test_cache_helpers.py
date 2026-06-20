import asyncio
import time
from unittest.mock import AsyncMock, patch

from backend.secuscan.cache import CacheClient


# ---------------------------------------------------------------------------
# get_or_set_cached unit tests (directly against CacheClient)
# ---------------------------------------------------------------------------


def _run(coro):
    return asyncio.run(coro)


async def _get_or_set_cached(cache: CacheClient, key: str, builder):
    """Inline copy of the route helper so unit tests stay self-contained."""
    cached = await cache.get_json(key)
    if cached is not None:
        return cached
    value = await builder()
    await cache.set_json(key, value)
    return value


def test_first_call_invokes_builder_and_stores_result():
    cache = CacheClient()

    build_calls = 0

    async def builder():
        nonlocal build_calls
        build_calls += 1
        return {"result": "built"}

    async def run():
        return await _get_or_set_cached(cache, "test:key", builder)

    result = _run(run())
    assert result == {"result": "built"}
    assert build_calls == 1


def test_second_call_returns_cached_value_without_rebuilding():
    cache = CacheClient()

    build_calls = 0

    async def builder():
        nonlocal build_calls
        build_calls += 1
        return {"value": build_calls}

    async def run_twice():
        first = await _get_or_set_cached(cache, "test:key", builder)
        second = await _get_or_set_cached(cache, "test:key", builder)
        return first, second

    first, second = _run(run_twice())
    assert first == second
    assert build_calls == 1


def test_different_keys_are_cached_independently():
    cache = CacheClient()

    async def builder_a():
        return {"key": "a"}

    async def builder_b():
        return {"key": "b"}

    async def run():
        a = await _get_or_set_cached(cache, "ns:a", builder_a)
        b = await _get_or_set_cached(cache, "ns:b", builder_b)
        a2 = await _get_or_set_cached(cache, "ns:a", builder_a)
        b2 = await _get_or_set_cached(cache, "ns:b", builder_b)
        return a, b, a2, b2

    a, b, a2, b2 = _run(run())
    assert a == a2 == {"key": "a"}
    assert b == b2 == {"key": "b"}


def test_delete_prefix_invalidates_cache():
    cache = CacheClient()

    async def builder():
        return {"fresh": True}

    async def run():
        await _get_or_set_cached(cache, "summary:dashboard", builder)
        await cache.delete_prefix("summary:")
        # After invalidation the builder must be called again
        return await cache.get_json("summary:dashboard")

    result = _run(run())
    assert result is None


# ---------------------------------------------------------------------------
# LRU eviction order
# ---------------------------------------------------------------------------


def test_lru_eviction_evicts_oldest_when_over_capacity():
    cache = CacheClient(max_entries=3)

    async def run():
        await cache.set_json("key:1", "val1")
        await cache.set_json("key:2", "val2")
        await cache.set_json("key:3", "val3")
        await cache.set_json("key:4", "val4")

    _run(run())
    assert cache.size == 3
    assert _run(cache.get_json("key:1")) is None
    assert _run(cache.get_json("key:2")) == "val2"
    assert _run(cache.get_json("key:3")) == "val3"
    assert _run(cache.get_json("key:4")) == "val4"


def test_lru_eviction_skips_when_under_capacity():
    cache = CacheClient(max_entries=5)

    async def run():
        await cache.set_json("key:1", "val1")
        await cache.set_json("key:2", "val2")

    _run(run())
    assert cache.size == 2
    assert _run(cache.get_json("key:1")) == "val1"
    assert cache._eviction_count == 0


def test_lru_eviction_preserves_recently_accessed():
    cache = CacheClient(max_entries=3)

    async def run():
        await cache.set_json("key:1", "val1")
        await cache.set_json("key:2", "val2")
        await cache.set_json("key:3", "val3")
        cache._access_order["key:2"] = 1.0  # Oldest
        cache._access_order["key:3"] = 2.0  # Middle
        await cache.get_json("key:1")  # Refreshes to ~now (most recent)
        await cache.set_json("key:4", "val4")

    _run(run())
    assert cache.size == 3
    assert _run(cache.get_json("key:1")) == "val1"  # Recently accessed, preserved
    assert _run(cache.get_json("key:2")) is None  # Oldest, evicted
    assert _run(cache.get_json("key:4")) == "val4"


# ---------------------------------------------------------------------------
# Expiry cleanup
# ---------------------------------------------------------------------------


def test_expiry_sweep_removes_access_order_entries():
    cache = CacheClient()

    async def run():
        await cache.set_json("key:1", "val1", ttl=10)
        await cache.set_json("key:2", "val2", ttl=10)
        cache._expires["key:1"] = time.time() - 1
        cache._expires["key:2"] = time.time() - 1
        cache._sweep_expired()

    _run(run())
    assert "key:1" not in cache._data
    assert "key:1" not in cache._expires
    assert "key:1" not in cache._access_order
    assert cache._sweep_count == 2


def test_expired_entry_get_returns_none_and_cleans_access_order():
    cache = CacheClient()

    async def run():
        await cache.set_json("key:1", "val1", ttl=10)
        cache._expires["key:1"] = time.time() - 1
        result = await cache.get_json("key:1")
        return result

    result = _run(run())
    assert result is None
    assert "key:1" not in cache._data
    assert "key:1" not in cache._expires
    assert "key:1" not in cache._access_order


def test_opportunistic_sweep_triggers_on_write_interval():
    cache = CacheClient()
    cache.max_entries = 1000

    async def run():
        for i in range(51):
            await cache.set_json(f"exp:{i}", f"val{i}", ttl=0)
            cache._expires[f"exp:{i}"] = time.time() - 1
        assert cache._sweep_count > 0

    _run(run())


# ---------------------------------------------------------------------------
# delete_prefix cleanup
# ---------------------------------------------------------------------------


def test_delete_prefix_removes_from_all_internal_dicts():
    cache = CacheClient()

    async def run():
        await cache.set_json("prefix:a", "val_a")
        await cache.set_json("prefix:b", "val_b")
        await cache.set_json("other:c", "val_c")
        await cache.delete_prefix("prefix:")

    _run(run())
    assert "prefix:a" not in cache._data
    assert "prefix:a" not in cache._expires
    assert "prefix:a" not in cache._access_order
    assert "prefix:b" not in cache._data
    assert "other:c" in cache._data
    assert cache.size == 1


# ---------------------------------------------------------------------------
# Edge cases: max_entries <= 0
# ---------------------------------------------------------------------------


def test_max_entries_zero_does_not_crash():
    cache = CacheClient(max_entries=0)

    async def run():
        await cache.set_json("key:1", "val1")
        await cache.set_json("key:2", "val2")

    _run(run())
    assert cache.size >= 0


def test_max_entries_negative_does_not_crash():
    cache = CacheClient(max_entries=-1)

    async def run():
        await cache.set_json("key:1", "val1")
        await cache.set_json("key:2", "val2")

    _run(run())
    assert cache.size >= 0
