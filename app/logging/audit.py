import json
import logging
from typing import Any

from app.guards.pipeline import GuardResult
from app.policy.schema import Policy


logger = logging.getLogger("llm_guard_proxy.audit")


def configure_logging(level: str) -> None:
    logging.basicConfig(level=level.upper(), format="%(message)s")


def audit_guard(
    *,
    request_id: str,
    stage: str,
    policy: Policy,
    result: GuardResult,
    log_prompts: bool = False,
    text: str | None = None,
) -> None:
    payload: dict[str, Any] = {
        "request_id": request_id,
        "stage": stage,
        "decision": result.decision.action,
        "policy_name": policy.name,
        "classifiers_run": result.classifiers_run,
        "findings_count": len(result.decision.findings),
        "blocked_categories": result.decision.blocked_categories,
        "latency_ms": round(result.latency_ms, 2),
    }
    if log_prompts:
        payload["text"] = text
    logger.info(json.dumps(payload, sort_keys=True))
