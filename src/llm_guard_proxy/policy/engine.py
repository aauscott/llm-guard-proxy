from llm_guard_proxy.models import Action, GuardFinding, PolicyDecision
from llm_guard_proxy.policy.schema import Policy


ACTION_RANK: dict[Action, int] = {
    "allow": 0,
    "log": 1,
    "warn": 2,
    "redact": 3,
    "review": 4,
    "block": 5,
}


def decide(policy: Policy, findings: list[GuardFinding]) -> PolicyDecision:
    if not findings:
        return PolicyDecision(action="allow", blocked=False)

    selected: Action = "allow"
    selected_findings: list[GuardFinding] = []

    for finding in findings:
        action = action_for_finding(policy, finding)
        if action == "allow":
            continue
        if ACTION_RANK[action] > ACTION_RANK[selected]:
            selected = action
            selected_findings = [finding]
        elif ACTION_RANK[action] == ACTION_RANK[selected]:
            selected_findings.append(finding)

    blocked = selected == "block"
    blocked_categories = sorted({finding.category for finding in selected_findings if blocked})
    reason = f"Policy selected action {selected} for {len(findings)} finding(s)."
    return PolicyDecision(
        action=selected,
        blocked=blocked,
        findings=findings,
        blocked_categories=blocked_categories,
        reason=reason,
    )


def action_for_finding(policy: Policy, finding: GuardFinding) -> Action:
    # Failure handling is an operational setting, independent of content severity.
    if finding.category == "classifier_error" and policy.mode == "fail_closed":
        return "block"
    action = policy.actions[finding.severity]
    threshold = getattr(policy.thresholds, action, 0.0)
    if finding.confidence < threshold:
        return "allow"
    return action
