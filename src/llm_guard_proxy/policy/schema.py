from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from llm_guard_proxy.models import Action, Severity, Stage


Mode = Literal["fail_open", "fail_closed"]


class PolicyDefaults(BaseModel):
    classifier_timeout_ms: int = Field(default=750, gt=0)
    log_prompts: bool = False
    canned_response: str = "I can't help with that request. I ignored that message, so you can continue with a different question."


class StageConfig(BaseModel):
    enabled_classifiers: list[str] = Field(default_factory=list)


class RegexRule(BaseModel):
    name: str
    pattern: str
    category: str = "custom_pattern"
    severity: Severity


class TermsConfig(BaseModel):
    critical: list[str] = Field(default_factory=list)
    high: list[str] = Field(default_factory=list)
    medium: list[str] = Field(default_factory=list)
    low: list[str] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def migrate_action_lists(cls, value):
        if isinstance(value, dict):
            value = dict(value)
            for old, severity in (("block", "high"), ("warn", "medium")):
                if old in value:
                    if not isinstance(value[old], list) or not isinstance(value.get(severity, []), list):
                        raise ValueError("Term groups must be lists.")
                    value[severity] = [*value.get(severity, []), *value.pop(old)]
        return value


class RegexConfig(BaseModel):
    rules: list[RegexRule] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def migrate_action_lists(cls, value):
        if isinstance(value, dict):
            value = dict(value)
            if any(not isinstance(value.get(key, []), list) for key in ("rules", "block", "warn")):
                raise ValueError("Pattern rules must be lists.")
            value["rules"] = [*value.get("rules", []), *value.pop("block", []), *value.pop("warn", [])]
        return value


class LlamaGuardConfig(BaseModel):
    provider: Literal["ollama", "http"] = "ollama"
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
