import asyncio
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
