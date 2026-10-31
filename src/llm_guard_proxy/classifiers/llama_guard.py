import re

from llm_guard_proxy.classifiers.base import Classifier
from llm_guard_proxy.clients.ollama_guard import OllamaGuardClient
from llm_guard_proxy.clients.http_guard import HTTPGuardClient
from llm_guard_proxy.models import ChatMessage, GuardFinding, GuardItem, Severity


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
        timeout = guard_config.get("timeout_ms", 5000) / 1000
        base_url = guard_config.get("base_url", "http://localhost:11434")
        messages = _guard_messages(item)
        if provider == "http":
            raw_verdict = await HTTPGuardClient(base_url, timeout).classify(messages=messages)
        elif provider == "ollama":
            raw_verdict = await OllamaGuardClient(base_url, timeout).classify(
                model=guard_config.get("model", "llama-guard3:8b"),
                messages=messages,
                keep_alive=guard_config.get("keep_alive", "5m"),
            )
        else:
            raise ValueError(f"Unsupported Llama Guard provider: {provider}")
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
    match = re.fullmatch(r"(safe|unsafe)(?:\s+(S(?:1[0-4]|[1-9])(?:\s*,\s*S(?:1[0-4]|[1-9]))*))?", verdict, re.IGNORECASE)
    if not match:
        raise ValueError("Llama Guard returned a malformed verdict.")
    if match.group(1).lower() == "safe":
        if match.group(2):
            raise ValueError("Llama Guard returned a malformed verdict.")
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
            action_hint="block",
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
