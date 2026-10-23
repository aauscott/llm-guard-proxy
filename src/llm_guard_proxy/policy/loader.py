from importlib.resources import files
from pathlib import Path
import re
from typing import Any

import yaml
from pydantic import ValidationError

from llm_guard_proxy.classifiers.registry import CLASSIFIERS
from llm_guard_proxy.policy.schema import Policy


class PolicyLoadError(ValueError):
    pass


def load_policy(path: str | Path) -> Policy:
    try:
        raw = yaml.safe_load(_read_policy(path)) or {}
    except FileNotFoundError as exc:
        raise PolicyLoadError(f"Policy file not found: {path}") from exc
    except yaml.YAMLError as exc:
        raise PolicyLoadError(f"Policy YAML is malformed: {exc}") from exc

    try:
        policy = Policy.model_validate(raw)
    except ValidationError as exc:
        raise PolicyLoadError(str(exc)) from exc

    validate_classifier_names(policy)
    validate_regex_patterns(policy)
    return policy


def _read_policy(path: str | Path) -> str:
    """Read a policy file or one of the policies bundled with the package."""
    policy_path = Path(path)
    if policy_path.is_file():
        return policy_path.read_text()

    requested = policy_path.as_posix()
    if len(policy_path.parts) == 1 or requested.startswith("policies/"):
        filename = policy_path.name
        if not filename.endswith((".yaml", ".yml")):
            filename = f"{filename}.yaml"
        bundled = files("llm_guard_proxy").joinpath("policies", filename)
        if bundled.is_file():
            return bundled.read_text()

    raise FileNotFoundError(path)


def validate_classifier_names(policy: Policy) -> None:
    unknown: set[str] = set()
    for stage in policy.stages.values():
        unknown.update(name for name in stage.enabled_classifiers if name not in CLASSIFIERS)
    if unknown:
        raise PolicyLoadError(f"Unknown classifiers in policy: {', '.join(sorted(unknown))}")


def validate_regex_patterns(policy: Policy) -> None:
    for rule in [*policy.regex.block, *policy.regex.warn]:
        try:
            re.compile(rule.pattern)
        except re.error as exc:
            raise PolicyLoadError(f"Invalid regex rule {rule.name!r}: {exc}") from exc


def classifier_config(policy: Policy, default_timeout_ms: int | None = None) -> dict[str, Any]:
    config: dict[str, Any] = {
        "terms": policy.terms.model_dump(),
        "regex": policy.regex.model_dump(),
        "llama_guard": policy.llama_guard.model_dump(),
    }
    if default_timeout_ms is not None:
        config["_default_timeout_ms"] = default_timeout_ms
    return config
