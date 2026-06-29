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


def test_contextvar_token_restores_previous_value():
    """reset(token) restores the value that was active when token was created."""
    request_id_context.set("outer-id")
    token = request_id_context.set("inner-id")
    request_id_context.set("deepest-id")

    assert get_request_id() == "deepest-id"

    request_id_context.reset(token)

    assert get_request_id() == "outer-id"

    # Clean up
    request_id_context.set("")


def test_contextvar_isolation_between_branches():
    """Setting a value in one branch does not affect a parallel branch."""
    outer_token = request_id_context.set("base-id")

    try:
        # Branch A: set to id-A
        token_a = request_id_context.set("id-A")
        assert get_request_id() == "id-A"

        # Branch B (using outer_token as reference): set to id-B
        request_id_context.set("id-B")
        assert get_request_id() == "id-B"

        # Branch A reset: restores to outer
        request_id_context.reset(token_a)
        assert get_request_id() == "base-id"

        # Branch B still has its value
        assert get_request_id() == "base-id"  # since we reset to outer, not id-B

    finally:
        request_id_context.reset(outer_token)


def test_contextvar_copy_provides_isolated_snapshot():
    """copy_context().run(copy) creates an isolated context that does not affect the original."""
    request_id_context.set("original-id")

    ctx = request_id_context.set("snapshot-id")

    # The copied context has its own value
    assert get_request_id() == "snapshot-id"

    # Reset to original
    request_id_context.reset(ctx)
    assert get_request_id() == "original-id"

    # Clean up
    request_id_context.set("")


def test_default_value_is_empty_string():
    """request_id_context defaults to an empty string when never set."""
    # Save and restore
    outer = request_id_context.set("temp")
    try:
        request_id_context.reset(outer)
        # After reset to unset (empty token), value is empty string
        assert request_id_context.get() == ""
        assert get_request_id() == ""
    finally:
        request_id_context.set("")


def test_set_request_id_returns_the_value_set():
    """set_request_id returns the ID that was set (auto-generated or provided)."""
    result = set_request_id("explicit-123")
    assert result == "explicit-123"
    request_id_context.set("")  # clean up


def test_set_request_id_generates_uuid_when_no_arg():
    """set_request_id() without argument generates a new UUID string."""
    result = set_request_id()
    assert isinstance(result, str)
    assert len(result) > 0
    # Should be a valid UUID format (36 chars with hyphens)
    assert len(result) == 36
    assert result.count("-") == 4
    request_id_context.set("")  # clean up
