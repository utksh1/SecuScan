import time
import pytest
from starlette.requests import Request
from starlette.responses import Response

from backend.secuscan.request_middleware import RequestIDMiddleware


async def call_next(request):
    return Response("ok")


def make_request(headers=None):
    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/",
            "headers": headers or [],
        }
    )


@pytest.mark.benchmark
@pytest.mark.asyncio
async def test_request_middleware_existing_id(record_benchmark):
    middleware = RequestIDMiddleware(app=None)

    request = make_request(
        [(b"x-request-id", b"test-request-id")]
    )

    latencies = []

    for _ in range(100):
        start = time.perf_counter()

        await middleware.dispatch(request, call_next)

        latencies.append(
            (time.perf_counter() - start) * 1000.0
        )

    mean_ms = sum(latencies) / len(latencies)

    record_benchmark(
        "request_middleware_existing_id_mean_ms",
        mean_ms,
    )

    print(
        f"\n[bench_request_middleware_existing_id] "
        f"Mean: {mean_ms:.4f}ms "
    )


@pytest.mark.benchmark
@pytest.mark.asyncio
async def test_request_middleware_uuid_generation(record_benchmark):
    middleware = RequestIDMiddleware(app=None)

    latencies = []

    for _ in range(100):
        request = make_request()

        start = time.perf_counter()

        await middleware.dispatch(request, call_next)

        latencies.append(
            (time.perf_counter() - start) * 1000.0
        )

    mean_ms = sum(latencies) / len(latencies)

    record_benchmark(
        "request_middleware_uuid_generation_mean_ms",
        mean_ms,
    )

    print(
        f"\n[bench_request_middleware_uuid_generation] "
        f"Mean: {mean_ms:.4f}ms "
    )
