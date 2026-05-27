#!/usr/bin/env python3
"""
Benchmark Runner Script for SecuScan.
Runs the performance benchmarks, compares results against thresholds,
and exits non-zero if any regressions are detected.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

# ANSI color codes
GREEN = "\033[92m"
RED = "\033[91m"
BOLD = "\033[1m"
RESET = "\033[0m"


def main():
    root_dir = Path(__file__).resolve().parents[1]
    thresholds_path = (
        root_dir / "testing" / "backend" / "benchmarks" / "thresholds.json"
    )
    results_path = root_dir / "benchmark_results.json"

    # 1. Load thresholds
    if not thresholds_path.exists():
        print(f"{RED}Error: Thresholds file not found at {thresholds_path}{RESET}")
        sys.exit(1)

    with open(thresholds_path) as f:
        thresholds = json.load(f)

    # Remove stale results if they exist from a previous run
    if results_path.exists():
        try:
            results_path.unlink()
        except OSError:
            pass

    # 2. Run pytest benchmarks
    print(f"{BOLD}Running SecuScan Performance Benchmarks...{RESET}\n")
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        str(root_dir / "testing" / "backend" / "benchmarks"),
        "-m",
        "benchmark",
        "-v",
        "-s",
    ]

    # Run the tests. We capture output/errors normally.
    result = subprocess.run(cmd, cwd=str(root_dir))

    # 3. Read results
    if not results_path.exists():
        print(f"\n{RED}Error: Benchmark run did not produce {results_path}{RESET}")
        sys.exit(1)

    with open(results_path) as f:
        results = json.load(f)

    # 4. Compare results against thresholds
    print(f"\n{BOLD}=== Performance Benchmark Report ==={RESET}\n")
    print(
        f"{'Benchmark Metric':<45} | {'Measured':<12} | {'Threshold':<12} | {'Status':<6}"
    )
    print("-" * 82)

    has_regression = False
    for metric, threshold in thresholds.items():
        if metric not in results:
            print(f"{metric:<45} | {'N/A':<12} | {threshold:<12} | {RED}MISSING{RESET}")
            has_regression = True
            continue

        value = results[metric]

        # Check if throughput metric (higher is better) or latency metric (lower is better)
        if "throughput" in metric:
            passed = value >= threshold
            status_str = f"{GREEN}PASS{RESET}" if passed else f"{RED}FAIL{RESET}"
            unit = "calls/s"
        else:
            passed = value <= threshold
            status_str = f"{GREEN}PASS{RESET}" if passed else f"{RED}FAIL{RESET}"
            unit = "ms"

        val_fmt = f"{value:.2f} {unit}"
        thresh_fmt = f"{threshold:.2f} {unit}"

        # If we failed the threshold, mark regression
        if not passed:
            has_regression = True

        print(f"{metric:<45} | {val_fmt:<12} | {thresh_fmt:<12} | {status_str:<6}")

    print("\n" + "=" * 82 + "\n")

    if has_regression:
        print(
            f"{RED}{BOLD}Performance regression detected! One or more metrics exceeded thresholds.{RESET}"
        )
        sys.exit(1)
    else:
        print(f"{GREEN}{BOLD}All performance benchmarks passed!{RESET}")
        sys.exit(0)


if __name__ == "__main__":
    main()
