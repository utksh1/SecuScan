import asyncio
import statistics
import time
import pytest
from testing.backend.benchmarks.conftest import load_threshold


@pytest.mark.benchmark
@pytest.mark.asyncio
async def test_10_concurrent_task_creates(bench_env, record_benchmark):
    executor = bench_env["executor"]
    plugin_id = "icmp_ping"
    safe_mode = True
    inputs = {"target": "127.0.0.1", "safe_mode": safe_mode}

    latencies = []

    async def create_one():
        start = time.perf_counter()
        tid = await executor.create_task(plugin_id, inputs, safe_mode=safe_mode)
        latencies.append((time.perf_counter() - start) * 1000.0)
        return tid

    start_total = time.perf_counter()
    tasks = [create_one() for _ in range(10)]
    await asyncio.gather(*tasks)
    total_time_ms = (time.perf_counter() - start_total) * 1000.0

    mean_lat = statistics.mean(latencies)
    p50_lat = statistics.median(latencies)
    latencies.sort()
    p95_lat = (
        latencies[int(len(latencies) * 0.95)] if len(latencies) >= 2 else latencies[-1]
    )

    # Record metric
    record_benchmark("concurrent_task_creates_10_total_ms", total_time_ms)

    threshold_total = load_threshold("concurrent_task_creates_10_total_ms")

    print(
        f"\n[bench_10_concurrent_task_creates] Total time: {total_time_ms:.2f}ms (threshold: {threshold_total}ms)"
    )
    print(f"Mean: {mean_lat:.2f}ms, P50: {p50_lat:.2f}ms, P95: {p95_lat:.2f}ms")

    assert (
        total_time_ms < threshold_total
    ), f"10 concurrent task creates took {total_time_ms:.2f}ms, threshold: {threshold_total}ms"


@pytest.mark.benchmark
@pytest.mark.asyncio
async def test_20_sequential_task_creates(bench_env, record_benchmark):
    executor = bench_env["executor"]
    plugin_id = "icmp_ping"
    safe_mode = True
    inputs = {"target": "127.0.0.1", "safe_mode": safe_mode}

    latencies = []
    for _ in range(20):
        start = time.perf_counter()
        await executor.create_task(plugin_id, inputs, safe_mode=safe_mode)
        latencies.append((time.perf_counter() - start) * 1000.0)

    mean_lat = statistics.mean(latencies)

    # Record metric
    record_benchmark("sequential_task_creates_mean_ms", mean_lat)

    threshold_mean = load_threshold("sequential_task_creates_mean_ms")

    print(
        f"\n[bench_20_sequential_task_creates] Mean latency: {mean_lat:.2f}ms (threshold: {threshold_mean}ms)"
    )

    assert (
        mean_lat < threshold_mean
    ), f"Mean sequential task create took {mean_lat:.2f}ms, threshold: {threshold_mean}ms"


@pytest.mark.benchmark
@pytest.mark.asyncio
async def test_concurrent_slot_saturation(bench_env, record_benchmark):
    from backend.secuscan.ratelimit import concurrent_limiter

    # Fills all 3 concurrency slots (via limiter), tries to acquire a 4th slot,
    # asserts it is rejected in < 5 ms (no spin-wait regression).
    async with concurrent_limiter.lock:
        concurrent_limiter.running_tasks.clear()

    # Fill slots
    assert (await concurrent_limiter.acquire("task-1")) == (True, "")
    assert (await concurrent_limiter.acquire("task-2")) == (True, "")
    assert (await concurrent_limiter.acquire("task-3")) == (True, "")

    # Try acquiring 4th slot, measure time
    start = time.perf_counter()
    acquired, msg = await concurrent_limiter.acquire("task-4")
    elapsed_ms = (time.perf_counter() - start) * 1000.0

    # Record metric
    record_benchmark("slot_rejection_ms", elapsed_ms)

    threshold_rejection = load_threshold("slot_rejection_ms")

    print(
        f"\n[bench_concurrent_slot_saturation] Slot rejection elapsed: {elapsed_ms:.4f}ms (threshold: {threshold_rejection}ms)"
    )

    assert not acquired, "Should not be able to acquire 4th slot"
    assert (
        elapsed_ms < threshold_rejection
    ), f"Slot rejection took {elapsed_ms:.2f}ms, threshold: {threshold_rejection}ms"
