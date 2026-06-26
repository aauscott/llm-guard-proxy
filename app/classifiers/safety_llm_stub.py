from app.classifiers.base import Classifier
from app.models import GuardFinding, GuardItem


class SafetyLlmStubClassifier(Classifier):
    name = "safety_llm_stub"
    supported_stages = {"input", "output", "tool"}

    async def classify(self, item: GuardItem, config: dict) -> list[GuardFinding]:
        return []
