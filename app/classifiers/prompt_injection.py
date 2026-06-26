import re

from app.classifiers.base import Classifier
from app.models import GuardFinding, GuardItem


HIGH_PATTERNS = [
    r"ignore (all )?(previous|prior|above) instructions",
    r"reveal (the )?(system|developer) prompt",
    r"bypass (your )?(rules|policy|safety)",
    r"disregard (the )?(safety )?policy",
    r"output hidden instructions",
    r"you are now in developer mode",
]

MEDIUM_PATTERNS = [
    r"jailbreak",
    r"developer mode",
    r"do not follow your instructions",
    r"show me your hidden prompt",
]


class PromptInjectionClassifier(Classifier):
    name = "prompt_injection"
    supported_stages = {"input", "output", "tool"}

    async def classify(self, item: GuardItem, config: dict) -> list[GuardFinding]:
        findings: list[GuardFinding] = []
        findings.extend(_scan(self.name, item.text, HIGH_PATTERNS, "high", "block", 0.92))
        findings.extend(_scan(self.name, item.text, MEDIUM_PATTERNS, "medium", "warn", 0.72))
        return findings


def _scan(
    classifier: str,
    text: str,
    patterns: list[str],
    severity: str,
    action_hint: str,
    confidence: float,
) -> list[GuardFinding]:
    findings: list[GuardFinding] = []
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            findings.append(GuardFinding(
                classifier=classifier,
                category="prompt_injection",
                severity=severity,
                confidence=confidence,
                action_hint=action_hint,
                matched=match.group(0),
                reason="Prompt-injection heuristic matched.",
                metadata={"pattern": pattern},
            ))
    return findings
