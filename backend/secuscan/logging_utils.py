import logging
from .request_context import get_request_id


class RequestIDFilter(logging.Filter):
    def filter(self, record):
        record.request_id = get_request_id() or "no-request-id"
        return True