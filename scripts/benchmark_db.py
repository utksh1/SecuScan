#!/usr/bin/env python3
"""
Benchmark: database query performance before and after index optimization.

Usage:
    python scripts/benchmark_db.py

Seeds a temporary SQLite database with 10,000 findings and 1,000 tasks,
then measures query execution time for the dashboard hot paths.

Expected output shows time improvement from full-table-scan to indexed queries.
"""

import asyncio
import json
import sqlite3
import sys
import tempfile
import time
import uuid
from datetime import datetime, timedelta
from pathlib import Path

# Add repo root to path
repo_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(repo_root))


SEVERITIES = ["critical", "high", "medium", "low", "info"]
STATUSES = ["queued", "running", "completed", "failed"]


def seed_database(db_path: str, findings_count: int = 10_000, tasks_count: int = 1_000):
    """Seed the database with realistic load."""
    print(f"Seeding {findings_count} findings and {tasks_count} tasks...")
    conn = sqlite3.connect(db_path)

    # Seed tasks
    for i in range(tasks_count):
        conn.execute(
            """
            INSERT INTO tasks
                (id, plugin_id, tool_name, target, status, created_at, inputs_json)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(uuid.uuid4()),
                "http_inspector",
                "http_inspector",
                f"192.168.1.{i % 255}",
                STATUSES[i % len(STATUSES)],
                (datetime.utcnow() - timedelta(seconds=i)).isoformat(),
                json.dumps({"target": f"192.168.1.{i % 255}"}),
            ),
        )

    # Seed findings
    for i in range(findings_count):
        conn.execute(
            """
            INSERT INTO findings
                (id, task_id, plugin_id, title, category, severity,
                 target, description, remediation, discovered_at, metadata_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(uuid.uuid4()),
                str(uuid.uuid4()),
                "http_inspector",
                f"Finding {i}",
                "web",
                SEVERITIES[i % len(SEVERITIES)],
                f"192.168.1.{i % 255}",
                f"Description {i}",
                "Apply patch",
                (datetime.utcnow() - timedelta(seconds=i)).isoformat(),
                json.dumps({}),
            ),
        )

    conn.commit()
    conn.close()
    print("Seeding complete.\n")


def benchmark_query(label: str, db_path: str, query: str, params: tuple = (), runs: int = 10):
    """Run a query N times and report average execution time."""
    conn = sqlite3.connect(db_path)
    times = []
    for _ in range(runs):
        start = time.perf_counter()
        conn.execute(query, params).fetchall()
        times.append(time.perf_counter() - start)
    conn.close()
    avg_ms = (sum(times) / len(times)) * 1000
    min_ms = min(times) * 1000
    max_ms = max(times) * 1000
    print(f"  {label}")
    print(f"    avg={avg_ms:.2f}ms  min={min_ms:.2f}ms  max={max_ms:.2f}ms")
    return avg_ms


def explain_query(label: str, db_path: str, query: str):
    """Print SQLite EXPLAIN QUERY PLAN output for a query."""
    conn = sqlite3.connect(db_path)
    plan = conn.execute(f"EXPLAIN QUERY PLAN {query}").fetchall()
    conn.close()
    print(f"\n  EXPLAIN QUERY PLAN — {label}")
    for row in plan:
        print(f"    {row}")


def main():
    with tempfile.TemporaryDirectory() as tmp:
        db_path = f"{tmp}/benchmark.db"

        # Initialize schema (with indexes)
        from backend.secuscan.database import Database
        asyncio.run(Database(db_path).connect())

        seed_database(db_path, findings_count=10_000, tasks_count=1_000)

        print("=" * 60)
        print("QUERY PLAN ANALYSIS (SQLite EXPLAIN QUERY PLAN)")
        print("=" * 60)

        explain_query(
            "Severity GROUP BY (optimized dashboard)",
            db_path,
            "SELECT severity, COUNT(*) AS cnt FROM findings GROUP BY severity",
        )
        explain_query(
            "Recent findings LIMIT 5",
            db_path,
            "SELECT id, title, severity, discovered_at FROM findings ORDER BY discovered_at DESC LIMIT 5",
        )
        explain_query(
            "Running tasks (composite index)",
            db_path,
            "SELECT id, tool_name, target FROM tasks WHERE status = 'running' ORDER BY created_at DESC LIMIT 5",
        )

        print("\n")
        print("=" * 60)
        print("BENCHMARK RESULTS (10,000 findings, 1,000 tasks, 10 runs)")
        print("=" * 60)

        benchmark_query(
            "Severity GROUP BY (optimized — DB aggregation)",
            db_path,
            "SELECT severity, COUNT(*) AS cnt FROM findings GROUP BY severity",
        )
        benchmark_query(
            "Recent findings LIMIT 5",
            db_path,
            "SELECT id, title, severity, discovered_at FROM findings ORDER BY discovered_at DESC LIMIT 5",
        )
        benchmark_query(
            "Running tasks with composite index",
            db_path,
            "SELECT id, tool_name, target, status, created_at FROM tasks WHERE status = 'running' ORDER BY created_at DESC LIMIT 5",
        )
        benchmark_query(
            "Total findings COUNT(*)",
            db_path,
            "SELECT COUNT(*) FROM findings",
        )
        benchmark_query(
            "Task stats GROUP BY status",
            db_path,
            "SELECT status, COUNT(*) FROM tasks GROUP BY status",
        )

        print("\nBenchmark complete.")


if __name__ == "__main__":
    main()