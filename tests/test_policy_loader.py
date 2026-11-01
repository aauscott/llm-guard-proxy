import pytest

from llm_guard_proxy.policy.loader import PolicyLoadError, classifier_config, load_policy


def test_loads_valid_policy() -> None:
    policy = load_policy("permissive")

    assert policy.name == "permissive"
    assert policy.mode == "fail_open"
    assert "prompt_injection" in policy.stages["input"].enabled_classifiers
    assert policy.llama_guard.model == "llama-guard3:8b"
    assert policy.llama_guard.timeout_ms == 5000


def test_loads_bundled_policy_outside_repository(monkeypatch, tmp_path) -> None:
    monkeypatch.chdir(tmp_path)

    policy = load_policy("school")

    assert policy.name == "school_default"


def test_global_timeout_is_added_to_classifier_config() -> None:
    policy = load_policy("permissive")

    config = classifier_config(policy, default_timeout_ms=250)

    assert config["_default_timeout_ms"] == 250


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


def test_legacy_policy_migrates_rules_and_terms_without_category_overrides(tmp_path, caplog):
    import yaml
    from llm_guard_proxy.models import GuardFinding
    from llm_guard_proxy.policy.engine import decide

    path = tmp_path / 'legacy.yaml'
    path.write_text(yaml.safe_dump({
        'name': 'legacy',
        'terms': {'block': ['old block'], 'warn': ['old warn']},
        'regex': {'block': [{'name': 'example', 'pattern': 'example',
                            'category': 'secret_leak', 'severity': 'low'}]},
        'categories': {'secret_leak': {'min_action': 'block'}},
    }))
    policy = load_policy(path)
    assert policy.terms.high == ['old block']
    assert policy.terms.medium == ['old warn']
    assert policy.regex.rules[0].severity == 'low'
    assert policy.regex.rules[0].category == 'secret_leak'
    assert 'categories' not in policy.model_dump()
    finding = GuardFinding(classifier='regex', category='secret_leak', severity='low',
                           confidence=1, reason='Match')
    assert decide(policy, [finding]).action == 'log'
    assert 'category overrides are ignored' in caplog.text
    path.write_text(yaml.safe_dump(policy.model_dump()))
    assert load_policy(path) == policy
