from llm_guard_proxy.classifiers.terms import TermsClassifier
from llm_guard_proxy.models import GuardItem


async def test_terms_matches_assigned_severity_case_insensitively() -> None:
    classifier = TermsClassifier()
    item = GuardItem(request_id="r1", stage="input", text="This has EXAMPLE blocked TERM.")

    findings = await classifier.classify(item, {"terms": {"high": ["example blocked term"], "medium": []}})

    assert len(findings) == 1
    assert findings[0].severity == "high"


async def test_terms_ignores_unrelated_text() -> None:
    classifier = TermsClassifier()
    item = GuardItem(request_id="r1", stage="input", text="hello there")

    findings = await classifier.classify(item, {"terms": {"high": ["blocked"], "medium": []}})

    assert findings == []
