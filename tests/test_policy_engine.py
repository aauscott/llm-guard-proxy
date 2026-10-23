from llm_guard_proxy.models import GuardFinding
from llm_guard_proxy.policy.engine import decide
from llm_guard_proxy.policy.loader import load_policy


def test_blocks_critical_findings() -> None:
    policy = load_policy("permissive")
    finding = GuardFinding(
        classifier="secrets",
        category="secret_leak",
        severity="critical",
        confidence=1.0,
        reason="secret",
    )

    decision = decide(policy, [finding])

    assert decision.blocked is True
    assert decision.action == "block"


def test_warns_but_allows_prompt_injection_in_permissive_policy() -> None:
    policy = load_policy("permissive")
    finding = GuardFinding(
        classifier="prompt_injection",
        category="prompt_injection",
        severity="high",
        confidence=0.92,
        action_hint="warn",
        reason="heuristic",
    )

    decision = decide(policy, [finding])

    assert decision.blocked is False
    assert decision.action == "warn"


def test_allows_clean_findings() -> None:
    policy = load_policy("permissive")

    decision = decide(policy, [])

    assert decision.blocked is False
    assert decision.action == "allow"
