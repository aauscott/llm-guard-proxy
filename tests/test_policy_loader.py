import pytest

from app.policy.loader import PolicyLoadError, load_policy


def test_loads_valid_policy() -> None:
    policy = load_policy("policies/permissive.yaml")

    assert policy.name == "permissive"
    assert policy.mode == "fail_open"
    assert "prompt_injection" in policy.stages["input"].enabled_classifiers
    assert policy.llama_guard.model == "llama-guard3:8b"
    assert policy.llama_guard.timeout_ms == 5000


def test_rejects_unknown_classifier(tmp_path) -> None:
    path = tmp_path / "bad.yaml"
    path.write_text(
        """
name: bad
mode: fail_open
stages:
  input:
    enabled_classifiers: [missing]
actions:
  critical: block
  high: block
  medium: warn
  low: log
"""
    )

    with pytest.raises(PolicyLoadError, match="Unknown classifiers"):
        load_policy(path)


def test_rejects_invalid_regex(tmp_path) -> None:
    path = tmp_path / "bad-regex.yaml"
    path.write_text(
        """
name: bad_regex
mode: fail_open
stages:
  input:
    enabled_classifiers: [regex]
actions:
  critical: block
  high: block
  medium: warn
  low: log
regex:
  block:
    - name: broken
      pattern: "["
      category: secret_leak
      severity: high
"""
    )

    with pytest.raises(PolicyLoadError, match="Invalid regex"):
        load_policy(path)


def test_loads_selected_llama_guard_configuration(tmp_path) -> None:
    path = tmp_path / "llama-guard.yaml"
    path.write_text(
        """
name: model_guard
stages:
  input:
    enabled_classifiers: [terms, llama_guard]
actions:
  critical: block
  high: block
  medium: warn
  low: log
llama_guard:
  provider: ollama
  base_url: http://ollama:11434
  model: llama-guard3:8b
  timeout_ms: 9000
  severity: medium
"""
    )

    policy = load_policy(path)

    assert policy.stages["input"].enabled_classifiers == ["terms", "llama_guard"]
    assert policy.llama_guard.base_url == "http://ollama:11434"
    assert policy.llama_guard.timeout_ms == 9000
    assert policy.llama_guard.severity == "medium"
