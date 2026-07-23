from app.classifiers.base import Classifier
from app.classifiers.llama_guard import LlamaGuardClassifier
from app.classifiers.prompt_injection import PromptInjectionClassifier
from app.classifiers.regex import RegexClassifier
from app.classifiers.safety_llm_stub import SafetyLlmStubClassifier
from app.classifiers.secrets import SecretsClassifier
from app.classifiers.terms import TermsClassifier
from app.classifiers.url_obfuscation import UrlObfuscationClassifier


CLASSIFIERS: dict[str, Classifier] = {
    "terms": TermsClassifier(),
    "regex": RegexClassifier(),
    "secrets": SecretsClassifier(),
    "prompt_injection": PromptInjectionClassifier(),
    "url_obfuscation": UrlObfuscationClassifier(),
    "llama_guard": LlamaGuardClassifier(),
    "safety_llm_stub": SafetyLlmStubClassifier(),
}
