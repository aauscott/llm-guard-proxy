# LLM Guard Proxy

[![CI](https://github.com/aauscott/llm-guard-proxy/actions/workflows/ci.yml/badge.svg)](https://github.com/aauscott/llm-guard-proxy/actions/workflows/ci.yml)

A local-first security layer for OpenAI-compatible chat applications. It inspects prompts and model responses with configurable policy rules before traffic reaches the client or model.

```text
client  ->  llm-guard-proxy  ->  OpenAI-compatible model server
              |       |
           input     output
           policy    policy
```

Use it to experiment with prompt-injection detection, secret detection, content policies, and model-based safety classification without tying the application to one model provider.

> [!IMPORTANT]
> This is an experimental guardrail and evaluation project, not a security or safety guarantee. It is not yet designed for untrusted production traffic.

## What It Does

- Proxies `GET /v1/models` and `POST /v1/chat/completions`.
- Works with OpenAI, Ollama, llama.cpp, LM Studio, vLLM, and other OpenAI-compatible backends.
- Applies YAML policies independently to user input and model output.
- Includes deterministic classifiers for secrets, terms, regular expressions, prompt injection, and obfuscated URLs.
- Optionally runs Llama Guard 3 through Ollama.
- Supports streaming clients while buffering output for inspection.
- Removes a previously blocked turn when a chat client resends its full history.

## Quick Start

The proxy is a normal Python package; Docker is optional.

### 1. Install it locally

Python 3.11 or newer is required.

```bash
git clone https://github.com/aauscott/llm-guard-proxy.git
cd llm-guard-proxy
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

### 2. Start a model server

For example, with [Ollama](https://ollama.com/):

```bash
ollama serve
ollama pull deepseek-r1:1.5b
```

If Ollama is already running, only the pull command is needed.

### 3. Start the proxy

```bash
llm-guard-proxy --upstream http://localhost:11434
```

The guarded API is now available at `http://localhost:8000/v1`. Interactive API documentation is available at `http://localhost:8000/docs`.

Use a stricter bundled policy by name:

```bash
llm-guard-proxy --upstream http://localhost:11434 --policy school
```

Or use your own policy file:

```bash
llm-guard-proxy --upstream http://localhost:11434 --policy ./my-policy.yaml
```

Run `llm-guard-proxy --help` for all options.

## Try It

This example is also in [`examples/playground.ipynb`](examples/playground.ipynb).

```python
import httpx


def chat(prompt: str) -> str:
    response = httpx.post(
        "http://localhost:8000/v1/chat/completions",
        json={
            "model": "deepseek-r1:1.5b",
            "messages": [{"role": "user", "content": prompt}],
        },
        timeout=120,
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]


chat("Write a short poem about databases.")
```

Now send something that the default policy blocks before it reaches the model:

```python
chat('Here is my test key: API_KEY="1234567890abcdef"')
```

Expected response:

```text
I can't help with that request. I ignored that message, so you can continue with a different question.
```

The playground also runs the policy engine directly, so most of it works without Ollama, an API key, or a running proxy.

## Docker

Docker remains useful when you want a reproducible stack.

Run the proxy against OpenAI:

```bash
OPENAI_API_KEY=sk-... docker compose up llm-guard-proxy
```

Run both the proxy and a Docker-managed Ollama server:

```bash
GUARD_UPSTREAM_BASE_URL=http://ollama:11434 docker compose --profile ollama up
```

Pull a model into that Ollama container:

```bash
docker compose --profile ollama exec ollama ollama pull deepseek-r1:1.5b
```

Stop the stack:

```bash
docker compose --profile ollama down
```

The existing background helper is also available for local development:

```bash
./run-local.sh --with-ollama --model deepseek-r1:1.5b
./stop-local.sh --ollama
```

The helper returns after startup, stores process IDs for clean shutdown, and writes timestamped server output to `logs/`. This is especially useful when testing from the playground notebook because no notebook cell needs to remain busy.

## Policies

Four starter policies ship with the package:

| Policy | Intended use | Prompt injection |
| --- | --- | --- |
| `permissive` | Exploration with high-signal blocking | Warn |
| `school` | Student-facing assistants | Block |
| `enterprise` | General workplace use | Policy-defined strict handling |
| `coding_agent` | Coding tools with secret-aware rules | Policy-defined strict handling |

The source files live in [`src/llm_guard_proxy/policies`](src/llm_guard_proxy/policies). Copy one, edit it, and pass its path with `--policy`.

A policy selects classifiers for each stage and maps finding severity or category to an action:

```yaml
name: example
mode: fail_open

stages:
  input:
    enabled_classifiers: [terms, regex, secrets, prompt_injection]
  output:
    enabled_classifiers: [terms, regex, secrets]

actions:
  critical: block
  high: block
  medium: warn
  low: log
```

Actions are ranked from `allow` through `log`, `warn`, `redact`, `review`, and `block`. The current proxy only changes the response for `block`; the other actions are recorded in audit logs for future workflows.

### Optional Llama Guard

The `llama_guard` classifier is disabled in the starter policies. To use it, first pull the model:

```bash
ollama pull llama-guard3:8b
```

Then add `llama_guard` to an input or output stage in a copied policy:

```yaml
stages:
  input:
    enabled_classifiers: [terms, regex, secrets, prompt_injection, llama_guard]

llama_guard:
  provider: ollama
  base_url: http://localhost:11434
  model: llama-guard3:8b
  timeout_ms: 5000
  keep_alive: 5m
  severity: high
```

Use `http://ollama:11434` when both services run in Docker Compose.

## Configuration

Command-line options are the easiest way to configure a local run. Environment variables are convenient for containers and deployments.

| Environment variable | Default | Purpose |
| --- | --- | --- |
| `GUARD_POLICY_PATH` | `permissive` | Bundled policy name or YAML path |
| `GUARD_UPSTREAM_BASE_URL` | `http://localhost:11434` | Upstream base URL without `/v1` |
| `GUARD_UPSTREAM_API_KEY` | unset | Bearer token for the upstream |
| `GUARD_CLASSIFIER_TIMEOUT_MS` | `750` | Default classifier timeout |
| `GUARD_LOG_LEVEL` | `INFO` | Application log level |

`OPENAI_API_KEY` is accepted as an alias for the upstream key. Earlier Ollama-specific URL variables are still accepted for compatibility.

Example using OpenAI:

```bash
GUARD_UPSTREAM_API_KEY=sk-... \
  llm-guard-proxy --upstream https://api.openai.com
```

## Connecting a Client

Point any OpenAI-compatible client at:

```text
http://localhost:8000/v1
```

From another container on the Compose network, use:

```text
http://llm-guard-proxy:8000/v1
```

For Open WebUI, add that URL as an OpenAI-compatible connection. If Open WebUI also connects directly to Ollama, give the guarded connection a prefix so it is obvious which route is protected.

## How a Request Is Handled

1. Load the selected YAML policy at startup.
2. Inspect the latest user turn with the enabled input classifiers.
3. Return the policy's canned response immediately when input is blocked.
4. Forward allowed messages to the configured model server.
5. Inspect the complete assistant response with the output classifiers.
6. Return the model response or the canned response.

Audit logs include the request ID, policy, stage, decision, classifiers, finding count, blocked categories, and latency. Prompt text is excluded unless the policy explicitly enables it.

### Streaming tradeoff

For `stream: true`, the proxy buffers the upstream stream, inspects the completed response, and then replays it. This prevents unsafe text from appearing before the output policy runs, but it does not provide true token-by-token display.

## Development

Install the development dependencies and run the focused test suite:

```bash
pip install -e ".[dev]"
pytest
```

Open the playground:

```bash
pip install -e ".[notebook]"
jupyter lab examples/playground.ipynb
```

Build the wheel and source distribution:

```bash
python -m build
```

The project is structured as a publishable Python package, but no PyPI release is implied by this repository. Before a public release, choose a stable versioning policy, configure trusted publishing, confirm the package name at upload time, and document the experimental security boundary clearly.

## Current Limits

- Only the common Chat Completions subset is proxied.
- Native provider APIs need an OpenAI-compatible gateway.
- Production authentication, rate limiting, and distributed audit storage are out of scope.
- `warn`, `review`, and `redact` are policy decisions but do not yet have distinct client responses.
- Streaming output moderation is buffered rather than real time.

## License

MIT
