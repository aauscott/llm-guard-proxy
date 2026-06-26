import pytest

from app.policy.loader import PolicyLoadError, load_policy


def test_loads_valid_policy() -> None:
    policy = load_policy("policies/permissive.yaml")

    assert policy.name == "permissive"
    assert policy.mode == "fail_open"
    assert "prompt_injection" in policy.stages["input"].enabled_classifiers


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
