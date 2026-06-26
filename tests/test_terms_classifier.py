from app.classifiers.terms import TermsClassifier
from app.models import GuardItem


async def test_terms_matches_blocked_terms_case_insensitively() -> None:
    classifier = TermsClassifier()
    item = GuardItem(request_id="r1", stage="input", text="This has EXAMPLE blocked TERM.")

    findings = await classifier.classify(item, {"terms": {"block": ["example blocked term"], "warn": []}})

    assert len(findings) == 1
    assert findings[0].action_hint == "block"


async def test_terms_ignores_unrelated_text() -> None:
    classifier = TermsClassifier()
    item = GuardItem(request_id="r1", stage="input", text="hello there")

    findings = await classifier.classify(item, {"terms": {"block": ["blocked"], "warn": []}})

    assert findings == []
