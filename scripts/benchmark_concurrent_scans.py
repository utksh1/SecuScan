"""Simple concurrent scan benchmark harness."""

from __future__ import annotations

import asyncio
import statistics
import time

import httpx

BASE_URL = "http://127.0.0.1:8000/api/v1"
PLUGIN = "http_inspector"
TARGET = "https://example.com"


async def run_scan(client: httpx.AsyncClient, idx: int) -> float:
    start = time.perf_counter()
    response = await client.post(
        f"{BASE_URL}/task/start",
        json={
            "plugin_id": PLUGIN,
            "inputs": {"target": TARGET},
            "consent_granted": True,
        },
        timeout=30,
    )
    response.raise_for_status()
    return time.perf_counter() - start


async def main(concurrency: int = 5) -> None:
    async with httpx.AsyncClient() as client:
        latencies = await asyncio.gather(*[run_scan(client, i) for i in range(concurrency)])

    print(f"Submitted {concurrency} scans")
    print(f"Min latency: {min(latencies):.3f}s")
    print(f"P50 latency: {statistics.median(latencies):.3f}s")
    print(f"Max latency: {max(latencies):.3f}s")


if __name__ == "__main__":
    asyncio.run(main())
