from llm_guard_proxy.guards.pipeline import GuardResult, run_guard
from llm_guard_proxy.models import GuardItem
from llm_guard_proxy.policy.schema import Policy


async def inspect_output(item: GuardItem, policy: Policy, config: dict) -> GuardResult:
    return await run_guard(item, policy, config)
