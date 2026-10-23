from llm_guard_proxy.classifiers.base import Classifier
from llm_guard_proxy.classifiers.llama_guard import LlamaGuardClassifier
from llm_guard_proxy.classifiers.prompt_injection import PromptInjectionClassifier
from llm_guard_proxy.classifiers.regex import RegexClassifier
from llm_guard_proxy.classifiers.safety_llm_stub import SafetyLlmStubClassifier
from llm_guard_proxy.classifiers.secrets import SecretsClassifier
from llm_guard_proxy.classifiers.terms import TermsClassifier
from llm_guard_proxy.classifiers.url_obfuscation import UrlObfuscationClassifier


CLASSIFIERS: dict[str, Classifier] = {
    "terms": TermsClassifier(),
    "regex": RegexClassifier(),
    "secrets": SecretsClassifier(),
    "prompt_injection": PromptInjectionClassifier(),
    "url_obfuscation": UrlObfuscationClassifier(),
    "llama_guard": LlamaGuardClassifier(),
    "safety_llm_stub": SafetyLlmStubClassifier(),
}
