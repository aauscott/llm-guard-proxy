# Classifier Plugin Specification

Classifiers should be small, testable modules that inspect a normalized guard item and return zero or more findings.

## Python Interface

```python
from abc import ABC, abstractmethod
from app.models import GuardItem, GuardFinding

class Classifier(ABC):
    name: str
    supported_stages: set[str]

    @abstractmethod
    async def classify(self, item: GuardItem, config: dict) -> list[GuardFinding]:
        ...
```

## Guard Item

```python
class GuardItem(BaseModel):
    request_id: str
    stage: Literal["input", "output", "tool"]
    text: str
    messages: list[ChatMessage] = []
    metadata: dict = {}
```

## Guard Finding

```python
class GuardFinding(BaseModel):
    classifier: str
    category: str
    severity: Literal["low", "medium", "high", "critical"]
    confidence: float
    action_hint: Literal["allow", "log", "warn", "redact", "block", "review"] | None = None
    matched: str | None = None
    reason: str
    metadata: dict = {}
```

## Built-In MVP Classifiers

### `terms`

Checks policy-provided terms:

- `terms.block`
- `terms.warn`

Should support case-insensitive matching by default.

### `regex`

Checks policy-provided regex patterns.

Each pattern should include:

- `name`
- `pattern`
- `category`
- `severity`

### `secrets`

Detects common secret-like strings:

- API keys
- Bearer tokens
- private key headers
- password assignments
- `.env`-style secrets

### `prompt_injection`

Heuristic detection for phrases such as:

- ignore previous instructions
- reveal system prompt
- bypass your rules
- developer mode
- disregard safety policy
- output hidden instructions

This should be conservative in MVP: obvious attempts should flag high severity; vague phrases should warn or log.

### `url_obfuscation`

Looks for:

- suspicious encoded URLs
- repeated URL encoding
- base64-like payloads containing URLs or instruction text
- hex-encoded strings that decode to suspicious content

## Future Classifiers

- PII detector
- toxicity detector
- malware intent detector
- policy-specific topic classifier
- Llama Guard-style model classifier
- NeMo Guardrails adapter
- LLM Guard adapter
- coding-agent tool-call classifier
- diff/file-write classifier
- shell-command classifier

## Plugin Discovery

For MVP, a simple registry is enough:

```python
CLASSIFIERS = {
    "terms": TermsClassifier(),
    "regex": RegexClassifier(),
    "secrets": SecretsClassifier(),
    "prompt_injection": PromptInjectionClassifier(),
    "url_obfuscation": UrlObfuscationClassifier(),
}
```

Later, support Python entry points:

```toml
[project.entry-points."ai_guard_proxy.classifiers"]
my_classifier = "my_package.classifiers:MyClassifier"
```

