import re
import logging
from contextvars import ContextVar
from typing import Optional
from uuid import uuid4

logger = logging.getLogger(__name__)

request_id_context: ContextVar[str] = ContextVar(
    "request_id",
    default=""
)

# Only allow alphanumeric, hyphens, underscores -- max 128 chars
RequestIdPattern = re.compile(r'^[a-zA-Z0-9_-]{1,128}$')


def get_request_id() -> str:
    return request_id_context.get()

def set_request_id(request_id: Optional[str] = None) -> str:
    if request_id and not RequestIdPattern.match(request_id):
        logger.warning(
            "Rejected malformed X-Request-ID (length=%d), generating new ID",
            len(request_id),
        )
        request_id = None
    request_id = request_id or str(uuid4())
    request_id_context.set(request_id)
    return request_id