from app.guards.pipeline import GuardResult, run_guard
from app.models import GuardItem
from app.policy.schema import Policy


async def inspect_output(item: GuardItem, policy: Policy, config: dict) -> GuardResult:
    return await run_guard(item, policy, config)
