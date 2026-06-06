from backend.secuscan.knowledgebase import KnowledgeBase


def test_find_vulnerabilities_returns_exact_match_strength():
    kb = KnowledgeBase()

    result = kb.find_vulnerabilities(service="http", product="nginx", version="1.18.0")

    assert result["cpe"] == "cpe:/a:nginx:nginx:1.18.0"
    assert result["match_strength"] == "exact"
    assert result["cves"]


def test_find_vulnerabilities_returns_family_only_for_weak_match():
    kb = KnowledgeBase()

    result = kb.find_vulnerabilities(service="http", product="nginx", version="9.9.9")

    assert result["cpe"] == "cpe:/a:nginx:nginx:1.18.0"
    assert result["match_strength"] == "family"
