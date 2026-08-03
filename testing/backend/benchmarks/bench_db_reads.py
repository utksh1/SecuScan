import statistics
import time
import pytest
from testing.backend.benchmarks.conftest import load_threshold


@pytest.mark.benchmark
@pytest.mark.asyncio
async def test_task_fetchall_100_rows(bench_env, record_benchmark):
    db = bench_env["db"]

    # Seed 100 tasks
    for i in range(100):
        await db.execute(
            """
            INSERT INTO tasks (
                id, plugin_id, tool_name, target, inputs_json, status, consent_granted
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (f"task-{i}", "icmp_ping", "ICMP Ping", "127.0.0.1", "{}", "completed", 1),
        )

    # Benchmark fetchall
    start = time.perf_counter()
    rows = await db.fetchall("SELECT * FROM tasks")
    elapsed_ms = (time.perf_counter() - start) * 1000.0

    # Record metric
    record_benchmark("task_fetchall_100_rows_ms", elapsed_ms)

    threshold = load_threshold("task_fetchall_100_rows_ms")
    print(
        f"\n[bench_task_fetchall_100_rows] Fetched {len(rows)} rows in {elapsed_ms:.2f}ms (threshold: {threshold}ms)"
    )

    assert len(rows) >= 100, f"Expected at least 100 rows, got {len(rows)}"
    assert elapsed_ms < threshold, (
        f"Fetchall took {elapsed_ms:.2f}ms, threshold: {threshold}ms"
    )


@pytest.mark.benchmark
@pytest.mark.asyncio
async def test_task_fetchone_repeated_50x(bench_env, record_benchmark):
    db = bench_env["db"]

    # Seed 1 task
    task_id = "target-task-id"
    await db.execute(
        """
        INSERT INTO tasks (
            id, plugin_id, tool_name, target, inputs_json, status, consent_granted
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (task_id, "icmp_ping", "ICMP Ping", "127.0.0.1", "{}", "completed", 1),
    )

    # Benchmark fetchone repeated 50 times
    latencies = []
    for _ in range(50):
        start = time.perf_counter()
        row = await db.fetchone("SELECT * FROM tasks WHERE id = ?", (task_id,))
        latencies.append((time.perf_counter() - start) * 1000.0)
        assert row is not None

    latencies.sort()
    p95_ms = (
        latencies[int(len(latencies) * 0.95)] if len(latencies) >= 2 else latencies[-1]
    )
    mean_ms = statistics.mean(latencies)

    # Record metric
    record_benchmark("task_fetchone_p95_ms", p95_ms)

    threshold = load_threshold("task_fetchone_p95_ms")

    print(
        f"\n[bench_task_fetchone_repeated_50x] Mean: {mean_ms:.2f}ms, P95: {p95_ms:.2f}ms (threshold: {threshold}ms)"
    )
    assert p95_ms < threshold, (
        f"P95 fetchone latency {p95_ms:.2f}ms exceeded threshold {threshold}ms"
    )


@pytest.mark.benchmark
@pytest.mark.asyncio
async def test_findings_fetchall_500_rows(bench_env, record_benchmark):
    db = bench_env["db"]

    # Seed 1 task
    task_id = "findings-task-id"
    await db.execute(
        """
        INSERT INTO tasks (
            id, plugin_id, tool_name, target, inputs_json, status, consent_granted
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (task_id, "icmp_ping", "ICMP Ping", "127.0.0.1", "{}", "completed", 1),
    )

    # Seed 500 findings
    for i in range(500):
        await db.execute(
            """
            INSERT INTO findings (
                id, task_id, plugin_id, title, category, severity, target, description, metadata_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                f"finding-{i}",
                task_id,
                "icmp_ping",
                f"Finding Title {i}",
                "Network",
                "HIGH",
                "127.0.0.1",
                f"Description for finding {i}",
                "{}",
            ),
        )

    # Benchmark fetchall
    start = time.perf_counter()
    rows = await db.fetchall("SELECT * FROM findings WHERE task_id = ?", (task_id,))
    elapsed_ms = (time.perf_counter() - start) * 1000.0

    # Record metric
    record_benchmark("findings_fetchall_500_rows_ms", elapsed_ms)

    threshold = load_threshold("findings_fetchall_500_rows_ms")
    print(
        f"\n[bench_findings_fetchall_500_rows] Fetched {len(rows)} findings in {elapsed_ms:.2f}ms (threshold: {threshold}ms)"
    )

    assert len(rows) >= 500, f"Expected at least 500 findings, got {len(rows)}"
    assert elapsed_ms < threshold, (
        f"Fetchall findings took {elapsed_ms:.2f}ms, threshold: {threshold}ms"
    )
