"""Client for the standalone Llama Guard service."""

import re
from typing import Literal

import httpx
from pydantic import BaseModel, Field, model_validator


class GuardVerdict(BaseModel):
    verdict: Literal["safe", "unsafe"]
    categories: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_categories(self):
        if any(not re.fullmatch(r"S(?:1[0-4]|[1-9])", code) for code in self.categories):
            raise ValueError("Unknown Llama Guard category")
        if self.verdict == "safe" and self.categories:
            raise ValueError("Safe verdict cannot include unsafe categories")
        return self


class HTTPGuardClient:
    def __init__(self, base_url: str, timeout: float):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    async def classify(self, *, messages: list[dict[str, str]]) -> str:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(f"{self.base_url}/classify", json={"messages": messages})
            response.raise_for_status()
            verdict = GuardVerdict.model_validate(response.json())
        return verdict.verdict + ("\n" + ",".join(verdict.categories) if verdict.categories else "")
