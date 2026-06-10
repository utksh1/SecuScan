from backend.secuscan.request_context import (
    get_request_id,
    request_id_context,
    set_request_id,
)


def test_set_request_id_override():
    request_id = set_request_id("custom-id")

    assert request_id == "custom-id"
    assert get_request_id() == "custom-id"


def test_set_request_id_generates_id(monkeypatch):
    monkeypatch.setattr(
        "backend.secuscan.request_context.uuid4",
        lambda: "fixed-uuid",
    )

    request_id = set_request_id()

    assert request_id == "fixed-uuid"
    assert get_request_id() == "fixed-uuid"


def test_get_request_id_default():
    token = request_id_context.set("")

    try:
        assert get_request_id() == ""
    finally:
        request_id_context.reset(token)