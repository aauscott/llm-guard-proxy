from functools import lru_cache

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    policy_path: str = Field(
        default="policies/permissive.yaml",
        validation_alias=AliasChoices("GUARD_POLICY_PATH", "policy_path"),
    )
    upstream_base_url: str = Field(
        default="http://localhost:11434",
        validation_alias=AliasChoices(
            "GUARD_UPSTREAM_BASE_URL",
            "UPSTREAM_BASE_URL",
            "OLLAMA_BASE_URL",
            "GUARD_OLLAMA_BASE_URL",
            "upstream_base_url",
            "ollama_base_url",
        ),
    )
    upstream_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("GUARD_UPSTREAM_API_KEY", "OPENAI_API_KEY", "upstream_api_key"),
    )
    classifier_timeout_ms: int = Field(
        default=750,
        validation_alias=AliasChoices("GUARD_CLASSIFIER_TIMEOUT_MS", "classifier_timeout_ms"),
    )
    log_level: str = Field(
        default="INFO",
        validation_alias=AliasChoices("GUARD_LOG_LEVEL", "log_level"),
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
