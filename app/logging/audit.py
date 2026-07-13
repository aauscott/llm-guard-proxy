import json
import logging
from typing import Any

from app.guards.pipeline import GuardResult
from app.policy.schema import Policy


logger = logging.getLogger("llm_guard_proxy.audit")


def configure_logging(level: str) -> None:
    formatter = logging.Formatter(
        fmt="%(levelname)s: %(asctime)s.%(msecs)03d P:%(process)d T:%(thread)d %(filename)s:%(lineno)d %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S%z",
    )
    root_logger = logging.getLogger()
    root_logger.setLevel(level.upper())

    if root_logger.handlers:
        for handler in root_logger.handlers:
            handler.setFormatter(formatter)
            handler.setLevel(level.upper())
    else:
        handler = logging.StreamHandler()
        handler.setFormatter(formatter)
        handler.setLevel(level.upper())
        root_logger.addHandler(handler)

    for logger_name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        uvicorn_logger = logging.getLogger(logger_name)
        for handler in uvicorn_logger.handlers:
            handler.setFormatter(formatter)
            handler.setLevel(level.upper())


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
    logger.info(json.dumps(payload, sort_keys=True), stacklevel=2)
