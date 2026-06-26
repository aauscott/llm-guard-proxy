from app.models import Action, GuardFinding, PolicyDecision
from app.policy.schema import Policy


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
    candidates: list[Action] = []
    if finding.action_hint:
        candidates.append(finding.action_hint)
    if category_policy := policy.categories.get(finding.category):
        candidates.append(category_policy.min_action)
    candidates.append(policy.actions[finding.severity])

    action = max(candidates, key=lambda item: ACTION_RANK[item])
    threshold = getattr(policy.thresholds, action, 0.0)
    if finding.confidence < threshold:
        return "allow"
    return action
