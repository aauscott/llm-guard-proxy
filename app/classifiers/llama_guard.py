import re

from app.classifiers.base import Classifier
from app.clients.ollama_guard import OllamaGuardClient
from app.models import ChatMessage, GuardFinding, GuardItem, Severity


HAZARD_CATEGORIES = {
    "S1": "violent_crimes",
    "S2": "non_violent_crimes",
    "S3": "sex_related_crimes",
    "S4": "child_sexual_exploitation",
    "S5": "defamation",
    "S6": "specialized_advice",
    "S7": "privacy",
    "S8": "intellectual_property",
    "S9": "indiscriminate_weapons",
    "S10": "hate",
    "S11": "self_harm",
    "S12": "sexual_content",
    "S13": "elections",
    "S14": "code_interpreter_abuse",
}


class LlamaGuardClassifier(Classifier):
    name = "llama_guard"
    supported_stages = {"input", "output"}

    async def classify(self, item: GuardItem, config: dict) -> list[GuardFinding]:
        guard_config = config.get(self.name, {})
        provider = guard_config.get("provider", "ollama")
        if provider != "ollama":
            raise ValueError(f"Unsupported Llama Guard provider: {provider}")

        timeout_ms = guard_config.get("timeout_ms", 5000)
        client = OllamaGuardClient(
            base_url=guard_config.get("base_url", "http://localhost:11434"),
            timeout=timeout_ms / 1000,
        )
        raw_verdict = await client.classify(
            model=guard_config.get("model", "llama-guard3:8b"),
            messages=_guard_messages(item),
            keep_alive=guard_config.get("keep_alive", "5m"),
        )
        return _findings_from_verdict(
            raw_verdict,
            severity=guard_config.get("severity", "high"),
            model=guard_config.get("model", "llama-guard3:8b"),
        )


def _guard_messages(item: GuardItem) -> list[dict[str, str]]:
    messages = [
        message
        for message in (_guard_message(message) for message in item.messages)
        if message
    ]
    if messages:
        return messages
    role = "assistant" if item.stage == "output" else "user"
    return [{"role": role, "content": item.text}]


def _guard_message(message: ChatMessage) -> dict[str, str] | None:
    if message.role not in {"user", "assistant"}:
        return None
    content = _message_text(message)
    if not content:
        return None
    return {"role": message.role, "content": content}


def _message_text(message: ChatMessage) -> str:
    if isinstance(message.content, str):
        return message.content
    if not isinstance(message.content, list):
        return ""
    return "\n".join(
        str(part.get("text", ""))
        for part in message.content
        if part.get("type") == "text" and part.get("text")
    )


def _findings_from_verdict(
    raw_verdict: str,
    severity: Severity,
    model: str,
) -> list[GuardFinding]:
    verdict = raw_verdict.strip().strip("`").strip()
    match = re.match(r"^(safe|unsafe)\b", verdict, re.IGNORECASE)
    if not match:
        raise ValueError("Llama Guard returned a malformed verdict.")
    if match.group(1).lower() == "safe":
        return []

    codes = sorted(
        {code.upper() for code in re.findall(r"\bS(?:1[0-4]|[1-9])\b", verdict, re.IGNORECASE)},
        key=lambda code: int(code[1:]),
    )
    if not codes:
        codes = ["unsafe"]

    return [
        GuardFinding(
            classifier="llama_guard",
            category=HAZARD_CATEGORIES.get(code, "unsafe_content"),
            severity=severity,
            confidence=1.0,
            reason=f"Llama Guard classified the {code} content category as unsafe.",
            metadata={
                "hazard_code": None if code == "unsafe" else code,
                "model": model,
                "score_source": "categorical_verdict",
            },
        )
        for code in codes
    ]
