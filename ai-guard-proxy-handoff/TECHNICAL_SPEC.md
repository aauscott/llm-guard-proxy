# Technical Specification

## Overview

Build a FastAPI service that exposes OpenAI-compatible endpoints and forwards requests to Ollama after guard checks.

The MVP should focus on `POST /v1/chat/completions`. Streaming can be deferred unless easy to support cleanly.

## Core Flow

```text
Request arrives
  -> normalize OpenAI chat request
  -> extract text/messages for input inspection
  -> run input classifiers
  -> policy engine decides allow/warn/redact/block/log
  -> if blocked, return canned response
  -> forward request to Ollama
  -> extract assistant output
  -> run output classifiers
  -> policy engine decides allow/warn/redact/block/log
  -> if blocked, return canned response
  -> return backend response
```

## API

### `POST /v1/chat/completions`

Accept a mostly standard OpenAI chat completion body:

```json
{
  "model": "llama3.1:8b",
  "messages": [
    {"role": "system", "content": "You are helpful."},
    {"role": "user", "content": "Hello"}
  ],
  "temperature": 0.7,
  "stream": false
}
```

Return an OpenAI-compatible response body.

If blocked, return a normal assistant message:

```json
{
  "id": "guard-blocked-request-id",
  "object": "chat.completion",
  "created": 1710000000,
  "model": "guard-policy",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "I can't help with that request."
      },
      "finish_reason": "stop"
    }
  ]
}
```

## Configuration

Use environment variables:

```text
GUARD_POLICY_PATH=policies/permissive.yaml
OLLAMA_BASE_URL=http://localhost:11434
GUARD_CLASSIFIER_TIMEOUT_MS=750
GUARD_LOG_LEVEL=INFO
```

## Policy Engine

The policy engine consumes classifier results and produces a decision.

Possible actions:

- `allow`
- `warn`
- `redact`
- `block`
- `log`
- `review`

For MVP, implement:

- `allow`
- `warn` as allow plus audit log
- `block`
- `log`

`redact` and `review` can be included in schemas but can be implemented later.

## Classifier Result Shape

Every classifier returns a list of results. Empty list means no finding.

```json
{
  "classifier": "prompt_injection",
  "category": "prompt_injection",
  "severity": "high",
  "confidence": 0.92,
  "action_hint": "block",
  "matched": "ignore previous instructions",
  "reason": "Instruction override phrase detected"
}
```

## Guard Pipeline

The guard pipeline should:

- Select classifiers enabled for the stage: `input`, `output`, or `tool`.
- Run classifiers concurrently using `asyncio.gather`.
- Apply a timeout per classifier.
- Treat classifier errors according to policy:
  - `fail_open` for development/permissive profiles.
  - `fail_closed` for high-security profiles.
- Return all findings to the policy engine.

## Ollama Client

Ollama supports OpenAI-compatible APIs in current local workflows, but the client should be written so the backend URL is configurable.

For MVP:

- Forward to `${OLLAMA_BASE_URL}/v1/chat/completions` if available.
- Keep request/response close to OpenAI shape.
- If backend fails, return a clear 502 with a safe error message.

## Logging

Use structured JSON logs. Each request should include:

- `request_id`
- `stage`: `input` or `output`
- `decision`
- `policy_name`
- `classifiers_run`
- `findings_count`
- `blocked_categories`
- `latency_ms`

Do not log full prompts by default. Add policy/config option to enable full prompt logging for local debugging only.

## Performance Goals

MVP target:

- Deterministic classifiers should usually finish in under 50 ms.
- Whole guard pass should usually finish in under 250 ms without model-based classifiers.
- Model-based classifiers should be optional and timeout-controlled.

## Coding Agent Extension Points

The same proxy can serve coding agents if they use an OpenAI-compatible endpoint. Later versions should add:

- Tool-call inspection.
- Shell command classification.
- Diff/file-write classification.
- Secret leakage checks in retrieved context.
- Detection of indirect prompt injection in files, web pages, issues, docs, and tool outputs.

