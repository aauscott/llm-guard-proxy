import json

import httpx
import respx

from app.clients.ollama_guard import OllamaGuardClient


@respx.mock
async def test_calls_ollama_chat_api_without_streaming() -> None:
    route = respx.post("http://ollama.test:11434/api/chat").mock(
        return_value=httpx.Response(
            200,
            json={"message": {"role": "assistant", "content": "safe"}, "done": True},
        )
    )
    client = OllamaGuardClient("http://ollama.test:11434", timeout=5.0)

    verdict = await client.classify(
        model="llama-guard3:8b",
        messages=[{"role": "user", "content": "hello"}],
        keep_alive="5m",
    )

    assert verdict == "safe"
    body = json.loads(route.calls.last.request.content)
    assert body == {
        "model": "llama-guard3:8b",
        "messages": [{"role": "user", "content": "hello"}],
        "stream": False,
        "keep_alive": "5m",
        "options": {"temperature": 0},
    }
