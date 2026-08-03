from backend.secuscan.triage_engine import _extract_variable_hints


def test_finding_with_proof_containing_variable_names():
    finding = {"proof": "user_input = request.GET.get('name')"}
    assert _extract_variable_hints(finding) == ["user_input"]


def test_finding_with_description_containing_variable_names():
    finding = {"description": "The password = input() call reads unsanitized data."}
    assert _extract_variable_hints(finding) == ["password"]


def test_finding_with_title_containing_variable_names():
    finding = {"title": "Hardcoded secret: token = 'abc123'"}
    assert _extract_variable_hints(finding) == ["token"]


def test_deduplication_of_variable_names_while_preserving_order():
    finding = {
        "proof": "a = 1",
        "description": "b = 2 a = 3",
        "title": "c = 4 b = 5",
    }
    # Fields are concatenated in proof, description, title order:
    # "a = 1 b = 2 a = 3 c = 4 b = 5" -> matches a, b, a, c, b
    # -> deduped preserving first-seen order: a, b, c
    assert _extract_variable_hints(finding) == ["a", "b", "c"]


def test_cap_at_10_results():
    assignments = " ".join(f"v{i} = {i}" for i in range(15))
    finding = {"proof": assignments}
    result = _extract_variable_hints(finding)
    assert len(result) == 10
    assert result == [f"v{i}" for i in range(10)]


def test_empty_finding_dict():
    assert _extract_variable_hints({}) == []


def test_finding_with_no_relevant_fields():
    finding = {"category": "xss", "severity": "high"}
    assert _extract_variable_hints(finding) == []