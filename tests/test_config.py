from app.config import Settings


def test_upstream_base_url_uses_guard_env_name(monkeypatch) -> None:
    monkeypatch.setenv("GUARD_UPSTREAM_BASE_URL", "http://example.test:8080")

    settings = Settings(_env_file=None)

    assert settings.upstream_base_url == "http://example.test:8080"


def test_upstream_base_url_accepts_legacy_ollama_env_name(monkeypatch) -> None:
    monkeypatch.delenv("GUARD_UPSTREAM_BASE_URL", raising=False)
    monkeypatch.delenv("UPSTREAM_BASE_URL", raising=False)
    monkeypatch.delenv("GUARD_OLLAMA_BASE_URL", raising=False)
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://localhost:11434")

    settings = Settings(_env_file=None)

    assert settings.upstream_base_url == "http://localhost:11434"
