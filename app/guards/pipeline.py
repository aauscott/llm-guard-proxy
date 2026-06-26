import asyncio
import time
from typing import Any

from app.classifiers.registry import CLASSIFIERS
from app.models import GuardFinding, GuardItem, PolicyDecision
from app.policy.engine import decide
from app.policy.schema import Policy


class GuardResult:
    def __init__(
        self,
        decision: PolicyDecision,
        classifiers_run: list[str],
        latency_ms: float,
    ) -> None:
        self.decision = decision
        self.classifiers_run = classifiers_run
        self.latency_ms = latency_ms


async def run_guard(item: GuardItem, policy: Policy, config: dict[str, Any] | None = None) -> GuardResult:
    config = config or {}
    stage_config = policy.stages.get(item.stage)
    enabled = stage_config.enabled_classifiers if stage_config else []
    classifiers = [
        CLASSIFIERS[name]
        for name in enabled
        if name in CLASSIFIERS and item.stage in CLASSIFIERS[name].supported_stages
    ]
    timeout = policy.defaults.classifier_timeout_ms / 1000
    started = time.perf_counter()

    tasks = [
        _run_classifier(classifier.name, classifier.classify(item, config), timeout, policy)
        for classifier in classifiers
    ]
    results = await asyncio.gather(*tasks)
    findings = [finding for classifier_findings in results for finding in classifier_findings]
    latency_ms = (time.perf_counter() - started) * 1000
    return GuardResult(
        decision=decide(policy, findings),
        classifiers_run=[classifier.name for classifier in classifiers],
        latency_ms=latency_ms,
    )


async def _run_classifier(name: str, coroutine: Any, timeout: float, policy: Policy) -> list[GuardFinding]:
    try:
        return await asyncio.wait_for(coroutine, timeout=timeout)
    except Exception as exc:
        if policy.mode == "fail_closed":
            return [GuardFinding(
                classifier=name,
                category="classifier_error",
                severity="critical",
                confidence=1.0,
                action_hint="block",
                reason=f"Classifier {name} failed or timed out.",
                metadata={"error_type": type(exc).__name__},
            )]
        return []
