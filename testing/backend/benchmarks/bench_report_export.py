import statistics
import time
import pytest
from backend.secuscan.reporting import ReportGenerator
from testing.backend.benchmarks.conftest import load_threshold


# Note: PDF export is excluded from CI benchmarks because xhtml2pdf has non-deterministic
# font rendering and layout engine performance in headless and container environments.
# PDF export performance should be verified manually or through local profiling.


def _get_mock_task_and_result_50x():
    task = {
        "id": "test-task-id",
        "tool_name": "ICMP Ping",
        "plugin_id": "icmp_ping",
        "target": "127.0.0.1",
        "status": "completed",
        "created_at": "2026-05-24T12:00:00.000000",
        "preset": "default",
        "command_used": "ping -c 4 127.0.0.1",
        "inputs": {"target": "127.0.0.1"},
    }

    result = {
        "findings": [
            {
                "id": f"finding-{i}",
                "title": f"Finding Title {i}",
                "category": "Network Security",
                "severity": "HIGH" if i % 2 == 0 else "MEDIUM",
                "target": "127.0.0.1",
                "description": f"Detailed description for finding {i} that contains some random text to simulate real-world payloads.",
                "remediation": "Do this and do that to resolve the issue.",
                "proof": "Here is proof.",
                "cve": "CVE-2026-1234",
                "cwe": "CWE-79",
                "cvss": 7.5,
                "discovered_at": "2026-05-24T12:00:05.000",
                "metadata": {"key": "value"},
            }
            for i in range(50)
        ],
        "structured": {"open_ports": [80, 443], "technologies": ["nginx", "openssl"]},
        "errors": [],
    }
    return task, result


@pytest.mark.benchmark
def test_csv_export_10x(bench_env, record_benchmark):
    task, result = _get_mock_task_and_result_50x()

    latencies = []
    for _ in range(10):
        start = time.perf_counter()
        ReportGenerator.generate_csv_report(task, result)
        latencies.append((time.perf_counter() - start) * 1000.0)

    mean_ms = statistics.mean(latencies)

    # Record metric
    record_benchmark("csv_export_mean_ms", mean_ms)

    threshold = load_threshold("csv_export_mean_ms")

    print(f"\n[bench_csv_export_10x] Mean: {mean_ms:.2f}ms (threshold: {threshold}ms)")
    assert mean_ms < threshold, (
        f"Mean CSV export latency {mean_ms:.2f}ms exceeded threshold {threshold}ms"
    )


@pytest.mark.benchmark
def test_html_export_10x(bench_env, record_benchmark):
    task, result = _get_mock_task_and_result_50x()

    latencies = []
    for _ in range(10):
        start = time.perf_counter()
        ReportGenerator.generate_html_report(task, result)
        latencies.append((time.perf_counter() - start) * 1000.0)

    mean_ms = statistics.mean(latencies)

    # Record metric
    record_benchmark("html_export_mean_ms", mean_ms)

    threshold = load_threshold("html_export_mean_ms")

    print(f"\n[bench_html_export_10x] Mean: {mean_ms:.2f}ms (threshold: {threshold}ms)")
    assert mean_ms < threshold, (
        f"Mean HTML export latency {mean_ms:.2f}ms exceeded threshold {threshold}ms"
    )
