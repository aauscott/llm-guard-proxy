from typing import Any, Literal

from pydantic import BaseModel, Field


Action = Literal["allow", "log", "warn", "redact", "block", "review"]
Severity = Literal["low", "medium", "high", "critical"]
Stage = Literal["input", "output", "tool"]


class ChatMessage(BaseModel):
    role: str
    content: str | list[dict[str, Any]] | None = None
    name: str | None = None


class ChatCompletionRequest(BaseModel):
    model: str
    messages: list[ChatMessage]
    temperature: float | None = None
    stream: bool = False
    max_tokens: int | None = None
    top_p: float | None = None

    model_config = {"extra": "allow"}


class ChatCompletionChoice(BaseModel):
    index: int
    message: ChatMessage
    finish_reason: str


class ChatCompletionResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: list[ChatCompletionChoice]
    usage: dict[str, Any] | None = None

    model_config = {"extra": "allow"}


class GuardItem(BaseModel):
    request_id: str
    stage: Stage
    text: str
    messages: list[ChatMessage] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class GuardFinding(BaseModel):
    classifier: str
    category: str
    severity: Severity
    confidence: float = Field(ge=0.0, le=1.0)
    action_hint: Action | None = None
    matched: str | None = None
    reason: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class PolicyDecision(BaseModel):
    action: Action
    blocked: bool
    findings: list[GuardFinding] = Field(default_factory=list)
    blocked_categories: list[str] = Field(default_factory=list)
    reason: str = "No policy findings."
