import statistics
import time
import pytest
from backend.secuscan.reporting import ReportGenerator
from testing.backend.benchmarks.conftest import load_threshold


def _get_mock_task_and_result():
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
                "title": f"Finding {i}",
                "category": "Network",
                "severity": "medium" if i % 2 == 0 else "high",
                "target": "127.0.0.1",
                "description": f"Description {i} with some details.",
                "remediation": "Mitigation steps here.",
                "proof": "Proof details.",
                "cve": "CVE-2026-1234",
                "cwe": "CWE-79",
                "cvss": 7.5,
                "discovered_at": "2026-05-24T12:00:05.000",
                "metadata": {"some_key": "some_value"},
            }
            for i in range(20)
        ],
        "structured": {"open_ports": [80, 443], "technologies": ["nginx", "openssl"]},
        "errors": [],
    }
    return task, result


@pytest.mark.benchmark
def test_build_report_payload_100x(bench_env, record_benchmark):
    task, result = _get_mock_task_and_result()

    latencies = []
    for _ in range(100):
        start = time.perf_counter()
        ReportGenerator._build_report_payload(task, result)
        latencies.append((time.perf_counter() - start) * 1000.0)

    mean_ms = statistics.mean(latencies)

    # Record metric
    record_benchmark("report_payload_build_mean_ms", mean_ms)

    threshold = load_threshold("report_payload_build_mean_ms")

    print(
        f"\n[bench_build_report_payload_100x] Mean: {mean_ms:.2f}ms (threshold: {threshold}ms)"
    )
    assert mean_ms < threshold, (
        f"Mean payload build latency {mean_ms:.2f}ms exceeded threshold {threshold}ms"
    )


@pytest.mark.benchmark
def test_normalize_1000_findings(bench_env, record_benchmark):
    _, result = _get_mock_task_and_result()
    finding = result["findings"][0]

    start = time.perf_counter()
    for _ in range(1000):
        ReportGenerator._normalize_finding(finding)
    elapsed = time.perf_counter() - start

    throughput = 1000.0 / elapsed

    # Record metric
    record_benchmark("finding_normalization_throughput_per_sec", throughput)

    threshold = load_threshold("finding_normalization_throughput_per_sec")

    print(
        f"\n[bench_normalize_1000_findings] Throughput: {throughput:.2f} calls/sec (threshold: {threshold} calls/sec)"
    )
    assert throughput > threshold, (
        f"Throughput {throughput:.2f} calls/sec was below threshold {threshold} calls/sec"
    )


@pytest.mark.benchmark
def test_html_report_generate_10x(bench_env, record_benchmark):
    task, result = _get_mock_task_and_result()

    latencies = []
    for _ in range(10):
        start = time.perf_counter()
        ReportGenerator.generate_html_report(task, result)
        latencies.append((time.perf_counter() - start) * 1000.0)

    mean_ms = statistics.mean(latencies)

    # Record metric
    record_benchmark("html_report_generate_mean_ms", mean_ms)

    threshold = load_threshold("html_report_generate_mean_ms")

    print(
        f"\n[bench_html_report_generate_10x] Mean: {mean_ms:.2f}ms (threshold: {threshold}ms)"
    )
    assert mean_ms < threshold, (
        f"Mean HTML report generation latency {mean_ms:.2f}ms exceeded threshold {threshold}ms"
    )
