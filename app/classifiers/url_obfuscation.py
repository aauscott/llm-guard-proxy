import base64
import binascii
import re
from urllib.parse import unquote

from app.classifiers.base import Classifier
from app.models import GuardFinding, GuardItem


SUSPICIOUS = [
    r"https?://",
    r"ignore previous instructions",
    r"reveal system prompt",
    r"bypass.+policy",
]


class UrlObfuscationClassifier(Classifier):
    name = "url_obfuscation"
    supported_stages = {"input", "output", "tool"}

    async def classify(self, item: GuardItem, config: dict) -> list[GuardFinding]:
        decoded_values = _decode_candidates(item.text)
        findings: list[GuardFinding] = []
        for decoded in decoded_values:
            if decoded == item.text:
                continue
            if any(re.search(pattern, decoded, re.IGNORECASE) for pattern in SUSPICIOUS):
                findings.append(GuardFinding(
                    classifier=self.name,
                    category="indirect_prompt_injection",
                    severity="medium",
                    confidence=0.72,
                    action_hint="warn",
                    matched=decoded[:160],
                    reason="Obfuscated content decoded to suspicious text.",
                ))
                break
        return findings


def _decode_candidates(text: str) -> set[str]:
    candidates = {text}
    current = text
    for _ in range(3):
        decoded = unquote(current)
        candidates.add(decoded)
        if decoded == current:
            break
        current = decoded

    for token in re.findall(r"\b[A-Za-z0-9+/=_-]{20,}\b", text):
        padded = token + "=" * (-len(token) % 4)
        try:
            candidates.add(base64.urlsafe_b64decode(padded).decode("utf-8", "ignore"))
        except (binascii.Error, ValueError):
            pass

    for token in re.findall(r"\b(?:0x)?[0-9a-fA-F]{24,}\b", text):
        token = token.removeprefix("0x")
        if len(token) % 2:
            continue
        try:
            candidates.add(bytes.fromhex(token).decode("utf-8", "ignore"))
        except ValueError:
            pass

    return candidates
