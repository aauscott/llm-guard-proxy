import re

from app.classifiers.base import Classifier
from app.models import GuardFinding, GuardItem


SECRET_PATTERNS = [
    ("private_key_header", r"-----BEGIN (RSA|OPENSSH|EC|DSA)? ?PRIVATE KEY-----", "critical"),
    ("bearer_token", r"\bBearer\s+[A-Za-z0-9._\-]{20,}\b", "high"),
    ("api_key_assignment", r"\b[A-Z0-9_]*(API_)?(KEY|TOKEN|SECRET|PASSWORD)\s*=\s*['\"]?[^'\"\s]{12,}", "high"),
    ("password_assignment", r"\b(password|passwd|pwd)\s*[:=]\s*['\"]?[^'\"\s]{10,}", "medium"),
    ("generic_secret", r"\b(sk|pk)_[A-Za-z0-9]{24,}\b", "high"),
]


class SecretsClassifier(Classifier):
    name = "secrets"
    supported_stages = {"input", "output", "tool"}

    async def classify(self, item: GuardItem, config: dict) -> list[GuardFinding]:
        findings: list[GuardFinding] = []
        for name, pattern, severity in SECRET_PATTERNS:
            match = re.search(pattern, item.text, re.IGNORECASE | re.MULTILINE)
            if match:
                findings.append(GuardFinding(
                    classifier=self.name,
                    category="secret_leak",
                    severity=severity,
                    confidence=0.95,
                    action_hint="block",
                    matched=_safe_match(match.group(0)),
                    reason=f"Secret-like value detected by {name}.",
                    metadata={"rule": name},
                ))
        return findings


def _safe_match(value: str) -> str:
    if len(value) <= 12:
        return value
    return f"{value[:6]}...{value[-4:]}"
