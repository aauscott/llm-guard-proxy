import re

from llm_guard_proxy.classifiers.base import Classifier
from llm_guard_proxy.models import GuardFinding, GuardItem


class RegexClassifier(Classifier):
    name = "regex"
    supported_stages = {"input", "output", "tool"}

    async def classify(self, item: GuardItem, config: dict) -> list[GuardFinding]:
        findings: list[GuardFinding] = []
        for rule in config.get("regex", {}).get("rules", []):
            pattern = re.compile(rule["pattern"], re.IGNORECASE | re.MULTILINE)
            match = pattern.search(item.text)
            if match:
                findings.append(GuardFinding(
                    classifier=self.name,
                    category=rule.get("category", "custom_pattern"),
                    severity=rule["severity"],
                    confidence=1.0,
                    matched=match.group(0)[:160],
                    reason=f"Regex rule {rule['name']} matched.",
                    metadata={"rule": rule["name"]},
                ))
        return findings
