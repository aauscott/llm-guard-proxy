from abc import ABC, abstractmethod

from llm_guard_proxy.models import GuardFinding, GuardItem, Stage


class Classifier(ABC):
    name: str
    supported_stages: set[Stage]

    @abstractmethod
    async def classify(self, item: GuardItem, config: dict) -> list[GuardFinding]:
        raise NotImplementedError
