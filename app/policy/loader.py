from pathlib import Path
import re
from typing import Any

import yaml
from pydantic import ValidationError

from app.classifiers.registry import CLASSIFIERS
from app.policy.schema import Policy


class PolicyLoadError(ValueError):
    pass


def load_policy(path: str | Path) -> Policy:
    policy_path = Path(path)
    try:
        raw = yaml.safe_load(policy_path.read_text()) or {}
    except FileNotFoundError as exc:
        raise PolicyLoadError(f"Policy file not found: {policy_path}") from exc
    except yaml.YAMLError as exc:
        raise PolicyLoadError(f"Policy YAML is malformed: {exc}") from exc

    try:
        policy = Policy.model_validate(raw)
    except ValidationError as exc:
        raise PolicyLoadError(str(exc)) from exc

    validate_classifier_names(policy)
    validate_regex_patterns(policy)
    return policy


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


def classifier_config(policy: Policy) -> dict[str, Any]:
    return {
        "terms": policy.terms.model_dump(),
        "regex": policy.regex.model_dump(),
        "llama_guard": policy.llama_guard.model_dump(),
    }
