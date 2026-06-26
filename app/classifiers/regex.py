import re

from app.classifiers.base import Classifier
from app.models import GuardFinding, GuardItem


class RegexClassifier(Classifier):
    name = "regex"
    supported_stages = {"input", "output", "tool"}

    async def classify(self, item: GuardItem, config: dict) -> list[GuardFinding]:
        findings: list[GuardFinding] = []
        regex_config = config.get("regex", {})
        for bucket, action in (("block", "block"), ("warn", "warn")):
            for rule in regex_config.get(bucket, []):
                pattern = re.compile(rule["pattern"], re.IGNORECASE | re.MULTILINE)
                match = pattern.search(item.text)
                if match:
                    findings.append(GuardFinding(
                        classifier=self.name,
                        category=rule["category"],
                        severity=rule["severity"],
                        confidence=1.0,
                        action_hint=action,
                        matched=match.group(0)[:160],
                        reason=f"Regex rule {rule['name']} matched.",
                        metadata={"rule": rule["name"]},
                    ))
        return findings
