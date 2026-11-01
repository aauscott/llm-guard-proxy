from llm_guard_proxy.classifiers.base import Classifier
from llm_guard_proxy.models import GuardFinding, GuardItem


class TermsClassifier(Classifier):
    name = "terms"
    supported_stages = {"input", "output", "tool"}

    async def classify(self, item: GuardItem, config: dict) -> list[GuardFinding]:
        text = item.text.lower()
        findings: list[GuardFinding] = []
        terms = config.get("terms", {})
        for severity in ("critical", "high", "medium", "low"):
            for term in terms.get(severity, []):
                if term.lower() in text:
                    findings.append(GuardFinding(
                        classifier=self.name,
                        category="policy_term",
                        severity=severity,
                        confidence=1.0,
                        matched=term,
                        reason="Policy term matched.",
                    ))
        return findings
