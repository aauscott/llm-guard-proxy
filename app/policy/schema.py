from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from app.models import Action, Severity, Stage


Mode = Literal["fail_open", "fail_closed"]


class PolicyDefaults(BaseModel):
    classifier_timeout_ms: int = Field(default=750, gt=0)
    log_prompts: bool = False
    canned_response: str = "I can't help with that request. I ignored that message, so you can continue with a different question."


class StageConfig(BaseModel):
    enabled_classifiers: list[str] = Field(default_factory=list)


class CategoryPolicy(BaseModel):
    min_action: Action


class RegexRule(BaseModel):
    name: str
    pattern: str
    category: str
    severity: Severity


class TermsConfig(BaseModel):
    block: list[str] = Field(default_factory=list)
    warn: list[str] = Field(default_factory=list)


class RegexConfig(BaseModel):
    block: list[RegexRule] = Field(default_factory=list)
    warn: list[RegexRule] = Field(default_factory=list)


class LlamaGuardConfig(BaseModel):
    provider: Literal["ollama"] = "ollama"
    base_url: str = "http://localhost:11434"
    model: str = "llama-guard3:8b"
    timeout_ms: int = Field(default=5000, gt=0)
    keep_alive: str = "5m"
    severity: Severity = "high"


class Thresholds(BaseModel):
    block: float = Field(default=0.0, ge=0.0, le=1.0)
    warn: float = Field(default=0.0, ge=0.0, le=1.0)
    log: float = Field(default=0.0, ge=0.0, le=1.0)


class Policy(BaseModel):
    name: str
    description: str = ""
    mode: Mode = "fail_open"
    defaults: PolicyDefaults = Field(default_factory=PolicyDefaults)
    stages: dict[Stage, StageConfig] = Field(default_factory=dict)
    actions: dict[Severity, Action] = Field(default_factory=lambda: {
        "critical": "block",
        "high": "block",
        "medium": "warn",
        "low": "log",
    })
    categories: dict[str, CategoryPolicy] = Field(default_factory=dict)
    thresholds: Thresholds = Field(default_factory=Thresholds)
    terms: TermsConfig = Field(default_factory=TermsConfig)
    regex: RegexConfig = Field(default_factory=RegexConfig)
    llama_guard: LlamaGuardConfig = Field(default_factory=LlamaGuardConfig)

    @field_validator("actions")
    @classmethod
    def require_all_severities(cls, value: dict[Severity, Action]) -> dict[Severity, Action]:
        missing = {"low", "medium", "high", "critical"} - set(value)
        if missing:
            raise ValueError(f"actions missing severities: {', '.join(sorted(missing))}")
        return value

    @model_validator(mode="after")
    def ensure_default_stages(self) -> "Policy":
        self.stages.setdefault("input", StageConfig())
        self.stages.setdefault("output", StageConfig())
        return self
