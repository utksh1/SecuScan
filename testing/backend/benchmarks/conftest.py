import pytest
import pytest_asyncio
from pathlib import Path


@pytest_asyncio.fixture
async def bench_env(setup_test_environment):
    """
    Provide an isolated execution environment for benchmark tests.
    Resets ratelimits and concurrency slot limits, and initializes the DB, cache, and plugins.
    """
    from backend.secuscan.config import settings
    from backend.secuscan import database as db_module
    from backend.secuscan import cache as cache_module
    from backend.secuscan.plugins import init_plugins
    from backend.secuscan.executor import TaskExecutor
    from backend.secuscan.ratelimit import concurrent_limiter, rate_limiter

    # Reset shared rate-limiter state
    await rate_limiter.reset()
    async with concurrent_limiter.lock:
        concurrent_limiter.running_tasks.clear()

    # Initialize the DB, cache, and plugin registry
    test_db = await db_module.init_db(settings.database_path)
    await cache_module.init_cache()
    await init_plugins(settings.plugins_dir)

    executor = TaskExecutor()

    yield {
        "executor": executor,
        "db": test_db,
        "db_path": settings.database_path,
        "raw_dir": Path(settings.raw_output_dir),
    }

    # Teardown
    await test_db.disconnect()
    db_module.db = None
    if cache_module.cache is not None:
        await cache_module.cache.disconnect()
        cache_module.cache = None


def load_threshold(name: str) -> float:
    """Load a threshold by key from thresholds.json"""
    import json

    threshold_path = Path(__file__).parent / "thresholds.json"
    with open(threshold_path) as f:
        thresholds = json.load(f)
    return float(thresholds[name])


# Dictionary to hold the collected benchmark metrics during a run
_benchmark_results = {}


@pytest.fixture
def record_benchmark():
    """
    Fixture to record custom benchmark metrics to be exported at the end of the session.
    """

    def _record(name: str, value: float):
        _benchmark_results[name] = value

    return _record


def pytest_sessionfinish(session, exitstatus):
    """
    Write collected benchmark results to benchmark_results.json at the workspace root.
    """
    if _benchmark_results:
        import json

        results_path = Path(session.config.rootdir) / "benchmark_results.json"
        with open(results_path, "w") as f:
            json.dump(_benchmark_results, f, indent=2)
        print(f"\nSaved benchmark results to {results_path}")
