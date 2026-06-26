from typing import Any

import httpx
from fastapi import HTTPException


class OllamaClient:
    def __init__(self, base_url: str, timeout: float = 120.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    async def chat_completions(self, body: dict[str, Any]) -> dict[str, Any]:
        url = f"{self.base_url}/v1/chat/completions"
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, json=body)
                response.raise_for_status()
                return response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise HTTPException(
                status_code=502,
                detail="Model backend is unavailable or returned an invalid response.",
            ) from exc

    async def stream_chat_completions(self, body: dict[str, Any]) -> list[str]:
        url = f"{self.base_url}/v1/chat/completions"
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                async with client.stream("POST", url, json=body) as response:
                    response.raise_for_status()
                    return [chunk async for chunk in response.aiter_text()]
        except httpx.HTTPError as exc:
            raise HTTPException(
                status_code=502,
                detail="Model backend is unavailable or returned an invalid streaming response.",
            ) from exc

    async def models(self) -> dict[str, Any]:
        url = f"{self.base_url}/v1/models"
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url)
                response.raise_for_status()
                payload = response.json()
                if payload.get("data") is None:
                    payload["data"] = []
                return payload
        except (httpx.HTTPError, ValueError) as exc:
            raise HTTPException(
                status_code=502,
                detail="Model backend is unavailable or returned an invalid model list.",
            ) from exc
