from contextvars import ContextVar
from uuid import uuid4

request_id_context: ContextVar[str] = ContextVar(
    "request_id",
    default=""
)

def get_request_id() -> str:
    return request_id_context.get()

def set_request_id(request_id: str = None) -> str:
    request_id = request_id or str(uuid4())
    request_id_context.set(request_id)
    return request_id