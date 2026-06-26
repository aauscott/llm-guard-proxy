from app.classifiers.base import Classifier
from app.models import GuardFinding, GuardItem


class TermsClassifier(Classifier):
    name = "terms"
    supported_stages = {"input", "output", "tool"}

    async def classify(self, item: GuardItem, config: dict) -> list[GuardFinding]:
        text = item.text.lower()
        findings: list[GuardFinding] = []
        terms = config.get("terms", {})

        for term in terms.get("block", []):
            if term.lower() in text:
                findings.append(GuardFinding(
                    classifier=self.name,
                    category="blocked_term",
                    severity="high",
                    confidence=1.0,
                    action_hint="block",
                    matched=term,
                    reason="Blocked policy term matched.",
                ))

        for term in terms.get("warn", []):
            if term.lower() in text:
                findings.append(GuardFinding(
                    classifier=self.name,
                    category="warning_term",
                    severity="medium",
                    confidence=1.0,
                    action_hint="warn",
                    matched=term,
                    reason="Warning policy term matched.",
                ))

        return findings
