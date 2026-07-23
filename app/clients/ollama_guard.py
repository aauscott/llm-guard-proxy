from typing import Any

import httpx


class OllamaGuardError(RuntimeError):
    pass


class OllamaGuardClient:
    """Small Ollama transport kept separate for future vLLM/SGLang adapters."""

    def __init__(self, base_url: str, timeout: float) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    async def classify(
        self,
        *,
        model: str,
        messages: list[dict[str, str]],
        keep_alive: str,
    ) -> str:
        body: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "stream": False,
            "keep_alive": keep_alive,
            "options": {"temperature": 0},
        }
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(f"{self.base_url}/api/chat", json=body)
                response.raise_for_status()
                payload = response.json()
                content = payload["message"]["content"]
        except (httpx.HTTPError, KeyError, TypeError, ValueError) as exc:
            raise OllamaGuardError(
                "Ollama Llama Guard is unavailable or returned an invalid response."
            ) from exc

        if not isinstance(content, str) or not content.strip():
            raise OllamaGuardError("Ollama Llama Guard returned an empty verdict.")
        return content
