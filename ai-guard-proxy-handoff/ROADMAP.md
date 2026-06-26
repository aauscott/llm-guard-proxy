# Roadmap

## Phase 1: Local Chat MVP

- FastAPI service.
- OpenAI-compatible `/v1/chat/completions`.
- Ollama backend.
- YAML policy loader.
- Input and output guard pipeline.
- Built-in deterministic classifiers.
- Structured audit logs.
- Example policies.
- Tests.

## Phase 2: Better Guardrails

- PII classifier.
- Improved secrets classifier.
- More robust prompt-injection heuristics.
- Optional local safety model classifier.
- Redaction action.
- Policy validation command.
- CLI:

```bash
ai-guard-proxy validate-policy policies/school.yaml
ai-guard-proxy run --policy policies/school.yaml
```

## Phase 3: Coding Agent Support

- Tool-call guard stage.
- Shell command classifier.
- File write/diff classifier.
- URL fetch/result classifier.
- Retrieved-context prompt-injection scanner.
- Per-tool policies.

## Phase 4: Multi-Backend Gateway

- Multiple Ollama model routing.
- LiteLLM-compatible backend option.
- OpenAI-compatible backend option.
- Per-model policies.
- Fallback behavior.

## Phase 5: Usability And Distribution

- Docker image.
- Compose example with Open WebUI and Ollama.
- Admin examples.
- Policy pack gallery.
- Contributor guide for classifiers.
- Optional lightweight web dashboard for logs and policy status.

