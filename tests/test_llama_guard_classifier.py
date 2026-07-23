import pytest

from app.classifiers.llama_guard import LlamaGuardClassifier
from app.clients.ollama_guard import OllamaGuardError
from app.guards.pipeline import run_guard
from app.models import ChatMessage, GuardItem
from app.policy.loader import classifier_config, load_policy


def _config(**overrides):
    config = {
        "provider": "ollama",
        "base_url": "http://ollama.test:11434",
        "model": "llama-guard3:8b",
        "timeout_ms": 5000,
        "keep_alive": "5m",
        "severity": "high",
    }
    config.update(overrides)
    return {"llama_guard": config}


async def test_safe_input_returns_no_findings(monkeypatch) -> None:
    captured = {}

    async def mock_classify(self, **kwargs):
        captured.update(kwargs)
        return "safe"

    monkeypatch.setattr("app.clients.ollama_guard.OllamaGuardClient.classify", mock_classify)
    item = GuardItem(
        request_id="r1",
        stage="input",
        text="Help me write a poem.",
        messages=[ChatMessage(role="user", content="Help me write a poem.")],
    )

    findings = await LlamaGuardClassifier().classify(item, _config())

    assert findings == []
    assert captured["model"] == "llama-guard3:8b"
    assert captured["messages"] == [{"role": "user", "content": "Help me write a poem."}]


async def test_unsafe_verdict_maps_hazard_categories(monkeypatch) -> None:
    async def mock_classify(self, **kwargs):
        return "unsafe\nS1,S11"

    monkeypatch.setattr("app.clients.ollama_guard.OllamaGuardClient.classify", mock_classify)
    item = GuardItem(request_id="r1", stage="input", text="unsafe example")

    findings = await LlamaGuardClassifier().classify(item, _config())

    assert [finding.category for finding in findings] == ["violent_crimes", "self_harm"]
    assert [finding.metadata["hazard_code"] for finding in findings] == ["S1", "S11"]
    assert all(finding.action_hint is None for finding in findings)


async def test_output_sends_prompt_and_response_context(monkeypatch) -> None:
    captured = {}

    async def mock_classify(self, **kwargs):
        captured.update(kwargs)
        return "safe"

    monkeypatch.setattr("app.clients.ollama_guard.OllamaGuardClient.classify", mock_classify)
    item = GuardItem(
        request_id="r1",
        stage="output",
        text="The answer is four.",
        messages=[
            ChatMessage(role="system", content="Be concise."),
            ChatMessage(role="user", content="What is two plus two?"),
            ChatMessage(role="assistant", content="The answer is four."),
        ],
    )

    await LlamaGuardClassifier().classify(item, _config())

    assert captured["messages"] == [
        {"role": "user", "content": "What is two plus two?"},
        {"role": "assistant", "content": "The answer is four."},
    ]


async def test_malformed_verdict_raises(monkeypatch) -> None:
    async def mock_classify(self, **kwargs):
        return "maybe"

    monkeypatch.setattr("app.clients.ollama_guard.OllamaGuardClient.classify", mock_classify)
    item = GuardItem(request_id="r1", stage="input", text="hello")

    with pytest.raises(ValueError, match="malformed verdict"):
        await LlamaGuardClassifier().classify(item, _config())


@pytest.mark.parametrize(
    ("policy_path", "blocked"),
    [("policies/permissive.yaml", False), ("policies/school.yaml", True)],
)
async def test_provider_failure_respects_policy_mode(monkeypatch, policy_path, blocked) -> None:
    async def mock_classify(self, **kwargs):
        raise OllamaGuardError("offline")

    monkeypatch.setattr("app.clients.ollama_guard.OllamaGuardClient.classify", mock_classify)
    policy = load_policy(policy_path)
    policy.stages["input"].enabled_classifiers = ["llama_guard"]
    item = GuardItem(request_id="r1", stage="input", text="hello")

    result = await run_guard(item, policy, classifier_config(policy))

    assert result.decision.blocked is blocked
    if blocked:
        assert result.decision.findings[0].category == "classifier_error"
