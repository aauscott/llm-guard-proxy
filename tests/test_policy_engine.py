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


async def test_all_classifier_findings_follow_the_same_mapping(monkeypatch):
    from llm_guard_proxy.classifiers.registry import CLASSIFIERS
    from llm_guard_proxy.models import GuardItem

    async def unsafe(self, **kwargs):
        return 'unsafe\nS10'

    monkeypatch.setattr('llm_guard_proxy.clients.ollama_guard.OllamaGuardClient.classify', unsafe)
    policy = load_policy('permissive')
    item = GuardItem(request_id='r', stage='input', text='sample Bearer abcdefghijklmnopqrstuvwxyz')
    configs = {
        'terms': {'terms': {'high': ['sample']}},
        'regex': {'regex': {'rules': [{'name': 'sample', 'pattern': 'sample', 'severity': 'high'}]}},
        'secrets': {},
        'llama_guard': {},
    }
    for name, config in configs.items():
        findings = await CLASSIFIERS[name].classify(item, config)
        assert findings and all(f.severity == 'high' for f in findings)
        for action in ('allow', 'log', 'warn', 'block'):
            policy.actions['high'] = action
            decision = decide(policy, findings)
            assert decision.action == action, name
            assert decision.blocked == (action == 'block')


def test_fail_closed_is_independent_of_content_mapping():
    policy = load_policy('school')
    policy.actions['critical'] = 'allow'
    failure = GuardFinding(classifier='llama_guard', category='classifier_error',
                           severity='critical', confidence=1, reason='Timeout')
    assert decide(policy, [failure]).blocked


def test_strongest_mapped_action_wins_and_thresholds_still_apply():
    policy = load_policy('school')
    findings = [GuardFinding(classifier='test', category='custom', severity=severity,
                            confidence=0.8, reason='Test') for severity in ('high', 'medium')]
    assert decide(policy, findings).action == 'block'
    policy.thresholds.block = 0.9
    assert decide(policy, findings).action == 'warn'
