# Prompt For Codex Coding Agent

I want you to build an open-source project called `ai-guard-proxy`.

It should be a policy-driven, plugin-based LLM security proxy that can sit between clients like Open WebUI, coding agents, or other OpenAI-compatible tools and an LLM backend such as Ollama.

Please read all files in this handoff folder before coding:

- `PRODUCT_BRIEF.md`
- `TECHNICAL_SPEC.md`
- `POLICY_SCHEMA.md`
- `CLASSIFIER_PLUGIN_SPEC.md`
- `ROADMAP.md`
- `TEST_PLAN.md`
- `SECURITY_CONSIDERATIONS.md`
- all YAML files in `example-policies/`

## Build The MVP

Create a Python FastAPI project that:

1. Exposes an OpenAI-compatible `POST /v1/chat/completions` endpoint.
2. Accepts standard OpenAI-style chat completion request bodies.
3. Runs input guard checks before forwarding the request to the model backend.
4. Forwards allowed requests to Ollama.
5. Runs output guard checks before returning the assistant response.
6. Returns a canned response when policy blocks input or output.
7. Logs guard decisions in structured JSON.
8. Loads policy from YAML.
9. Supports multiple classifiers using a simple plugin interface.
10. Runs configured classifiers concurrently with timeouts.

## MVP Classifiers

Implement these built-in classifiers first:

- `terms`: configurable blocked/warn terms from policy YAML.
- `regex`: configurable regex patterns from policy YAML.
- `secrets`: simple local detection for API keys/tokens/password-like strings.
- `prompt_injection`: heuristic detector for jailbreak and instruction override attempts.
- `url_obfuscation`: decodes obvious URL/base64/hex obfuscation where reasonable and flags suspicious patterns.

Do not implement heavyweight model-based classifiers in the first pass. Instead, create the interface and a stub/example classifier so model-based safety classifiers can be added later.

## Suggested Stack

- Python 3.11+
- FastAPI
- Uvicorn
- httpx
- Pydantic
- PyYAML
- pytest
- pytest-asyncio

## Expected Repository Shape

```text
ai-guard-proxy/
  README.md
  pyproject.toml
  docker-compose.yml
  .env.example
  app/
    main.py
    config.py
    models.py
    policy/
      loader.py
      engine.py
      schema.py
    classifiers/
      base.py
      registry.py
      terms.py
      regex.py
      secrets.py
      prompt_injection.py
      url_obfuscation.py
      safety_llm_stub.py
    guards/
      pipeline.py
      input_guard.py
      output_guard.py
    clients/
      ollama.py
    routes/
      chat_completions.py
    logging/
      audit.py
  policies/
    school.yaml
    enterprise.yaml
    coding_agent.yaml
    permissive.yaml
  tests/
    test_policy_loader.py
    test_policy_engine.py
    test_terms_classifier.py
    test_prompt_injection_classifier.py
    test_chat_completions.py
```

## Behavioral Requirements

- If input is blocked, do not call Ollama.
- If output is blocked, do not return the unsafe model output.
- Include a `request_id` in logs.
- Return a generic canned response to the client unless the policy defines a custom response.
- Keep classifier results internally available for logs, but do not expose sensitive classifier detail to the end user by default.
- Make policy behavior easy to understand.
- Keep the code simple enough for outside contributors to add classifiers.

## Developer Experience

The repo should support:

```bash
cp .env.example .env
pip install -e ".[dev]"
uvicorn app.main:app --reload --port 8000
```

Then Open WebUI or another OpenAI-compatible client should be able to use:

```text
http://localhost:8000/v1
```

as its API base.

## Deliverables

After implementation:

- Show the generated file tree.
- Explain how to run it locally with Ollama.
- Run tests.
- Include example `curl` commands for allowed and blocked requests.

