"""
Import-safe helpers extracted from routes.py.
These functions have no external dependencies and can be tested directly.
"""

from typing import Iterator

SSE_RAW_OUTPUT_CHUNK_SIZE = 64 * 1024


def iter_raw_output_chunks(path: str, chunk_size: int = SSE_RAW_OUTPUT_CHUNK_SIZE) -> Iterator[str]:
    """Yield raw output in bounded chunks for completed-task SSE replay."""
    with open(path, "r", encoding="utf-8", errors="replace") as output_file:
        while True:
            chunk = output_file.read(chunk_size)
            if not chunk:
                break
            yield chunk
