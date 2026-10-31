import asyncio
import json

import httpx
import pytest
import respx
from starlette.testclient import TestClient

from llm_guard_proxy.classifiers.llama_guard import LlamaGuardClassifier
from llm_guard_proxy.clients.http_guard import HTTPGuardClient
from llm_guard_proxy.guard_service import create_guard_app
from llm_guard_proxy.guards.pipeline import run_guard
from llm_guard_proxy.models import GuardItem
from llm_guard_proxy.policy.loader import classifier_config, load_policy


@respx.mock
async def test_http_unsafe_blocks_even_when_high_severity_only_warns():
    route = respx.post("http://guard.test/classify").respond(200, json={
        "verdict": "unsafe", "categories": ["S5", "S10"],
    })
    policy = load_policy("permissive")
    policy.stages["input"].enabled_classifiers = ["llama_guard"]
    policy.llama_guard.provider = "http"
    policy.llama_guard.base_url = "http://guard.test"
    result = await run_guard(GuardItem(request_id="r", stage="input", text="test"), policy, classifier_config(policy))
    assert result.decision.blocked
    assert result.decision.blocked_categories == ["defamation", "hate"]
    assert json.loads(route.calls.last.request.content) == {"messages": [{"role": "user", "content": "test"}]}


@pytest.mark.parametrize("payload", [
    {"verdict": "maybe"}, {"verdict": "safe", "categories": ["S1"]},
    {"verdict": "unsafe", "categories": ["S999"]},
])
@respx.mock
async def test_http_rejects_invalid_verdicts(payload):
    respx.post("http://guard.test/classify").respond(200, json=payload)
    with pytest.raises(ValueError):
        await HTTPGuardClient("http://guard.test", 5).classify(messages=[])


@pytest.mark.parametrize("mode,blocked", [("fail_open", False), ("fail_closed", True)])
@respx.mock
async def test_http_failure_respects_mode(mode, blocked):
    respx.post("http://guard.test/classify").mock(side_effect=httpx.ReadTimeout("timed out"))
    policy = load_policy("permissive")
    policy.mode = mode
    policy.stages["input"].enabled_classifiers = ["llama_guard"]
    policy.llama_guard.provider = "http"
    policy.llama_guard.base_url = "http://guard.test"
    result = await run_guard(GuardItem(request_id="r", stage="input", text="test"), policy, classifier_config(policy))
    assert result.decision.blocked is blocked


def test_service_loads_once_renders_roles_and_parses_verdict():
    calls = []

    class Model:
        def __init__(self):
            calls.append("loaded")

        def classify(self, messages):
            calls.append(messages)
            return "unsafe\nS10"

    with TestClient(create_guard_app(Model)) as client:
        assert client.get("/health").json() == {"status": "ready"}
        for _ in range(2):
            response = client.post("/classify", json={"messages": [
                {"role": "user", "content": "one"},
                {"role": "user", "content": "two"},
                {"role": "assistant", "content": "reply"},
            ]})
            assert response.json() == {"verdict": "unsafe", "categories": ["S10"]}
        assert calls.count("loaded") == 1
        assert calls[1] == [
            {"role": "user", "content": [{"type": "text", "text": "one\ntwo"}]},
            {"role": "assistant", "content": [{"type": "text", "text": "reply"}]},
        ]
        assert client.post("/classify", json={"messages": [{"role": "assistant", "content": "alone"}]}).status_code == 422


async def test_pipeline_starts_all_async_checks_before_collecting(monkeypatch):
    from llm_guard_proxy.classifiers.registry import CLASSIFIERS

    ready = asyncio.Event()
    started = []

    async def classify(self, item, config):
        started.append(self.name)
        if len(started) == 2:
            ready.set()
        await asyncio.wait_for(ready.wait(), 1)
        return []

    for name in ("terms", "llama_guard"):
        monkeypatch.setattr(type(CLASSIFIERS[name]), "classify", classify)
    policy = load_policy("school")
    policy.stages["input"].enabled_classifiers = ["terms", "llama_guard"]
    result = await run_guard(GuardItem(request_id="r", stage="input", text="hello"), policy)
    assert not result.decision.blocked
    assert len(started) == 2


@pytest.mark.parametrize("raw,expected", [("safe", 200), ("unsafe", 200), ("maybe", 502)])
def test_service_validates_model_output(raw, expected):
    class Model:
        def classify(self, messages):
            return raw

    with TestClient(create_guard_app(Model)) as client:
        response = client.post("/classify", json={"messages": [{"role": "user", "content": "hello"}]})
        assert response.status_code == expected
        if raw == "safe":
            assert response.json() == {"verdict": "safe", "categories": []}
        if raw == "unsafe":
            assert response.json() == {"verdict": "unsafe", "categories": []}


def test_service_rejects_concurrent_inference_without_queueing():
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event

    entered, release = Event(), Event()

    class Model:
        def classify(self, messages):
            entered.set()
            assert release.wait(5)
            return "safe"

    with TestClient(create_guard_app(Model)) as client, ThreadPoolExecutor() as pool:
        payload = {"messages": [{"role": "user", "content": "hello"}]}
        first = pool.submit(client.post, "/classify", json=payload)
        try:
            assert entered.wait(5)
            assert client.post("/classify", json=payload).status_code == 503
            assert client.get("/health").status_code == 200
        finally:
            release.set()
        assert first.result().status_code == 200
