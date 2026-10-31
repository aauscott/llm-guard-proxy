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

Llama Guard runs alongside the rule classifiers. Each stage schedules all enabled
checks concurrently and waits for their results or timeouts before deciding.
Every `unsafe` verdict blocks, even if the policy maps `high` severity to `warn`.
The blocked chat response includes the detected category, for example
`Llama Guard: hate (S10).` This works with streaming and non-streaming clients.

#### Separate local service with the Confusable Guard adapter

The optional service loads `meta-llama/Llama-Guard-3-1B` and
`aascott/Llama-Guard-3-1B-Confusable-Guard-LoRA` once at startup, using pinned
revisions from the model card. No retraining, merging, or changes to the model
repository are required. The service uses the base tokenizer's safety template,
not an ordinary assistant prompt. It selects CUDA, Apple MPS, or CPU automatically.

Install in a separate environment, from this repository:

```bash
python3 -m venv .venv-guard
.venv-guard/bin/pip install -e ".[guard]"
```

Accept access to the gated base model on Hugging Face, then authenticate locally
if the weights are not already cached:

```bash
.venv-guard/bin/hf auth login
```

Start the guard service in its own terminal:

```bash
.venv-guard/bin/llm-guard-service
```

The default address is `http://127.0.0.1:8001`. Startup downloads missing model
files and loads the weights; `/health` returns `{"status":"ready"}` once ready.
One model generation runs at a time; concurrent inference requests receive 503
rather than accumulating in a queue. Timed-out HTTP calls do not cancel an
already-running model generation.

To load an existing local adapter instead:

```bash
.venv-guard/bin/llm-guard-service --adapter /absolute/path/to/adapter
```

Add `llama_guard` to your custom policy's **input** `enabled_classifiers`, leaving
all existing rule classifiers in place. Add this top-level configuration:

```yaml
llama_guard:
  provider: http
  base_url: http://127.0.0.1:8001
  model: aascott/Llama-Guard-3-1B-Confusable-Guard-LoRA
  timeout_ms: 30000
  severity: high
```

For this provider, `model` labels findings; the service's startup arguments select
the actual model. Add `llama_guard` to the output stage as well if you want response
moderation. Output checks include conversation context and assess the last
assistant message. Overlong conversations are rejected rather than truncated.

Restart the proxy after editing your policy:

```bash
./stop-local.sh
./run-local.sh --with-ollama --model deepseek-r1:1.5b --policy ./policies/my-policy.yaml
```

The guard service and Ollama are independent processes. The proxy's stop helper
does not stop the guard service; use Ctrl+C in its terminal.

`mode: fail_open` logs classifier errors/timeouts and lets other checks decide.
`mode: fail_closed` blocks on classifier errors, including an unavailable or busy
guard service. Unsafe verdicts block under either mode. The 30-second timeout is
a starting value; CPU inference or long conversations may require more time.

The HTTP contract is `POST /classify` with
`{"messages":[{"role":"user","content":"Hello"}]}`. It returns
`{"verdict":"safe","categories":[]}` or, for example,
`{"verdict":"unsafe","categories":["S10"]}`. Messages must start with a user;
consecutive messages with the same role are combined for the safety template.

#### Llama Guard hosted by Ollama

The existing Ollama integration is also supported:

```bash
ollama pull llama-guard3:8b
```

Enable `llama_guard` in the desired stages and configure:

```yaml
llama_guard:
  provider: ollama
  base_url: http://localhost:11434
  model: llama-guard3:8b
  timeout_ms: 30000
  keep_alive: 5m
  severity: high
```

Use `http://ollama:11434` when the guard model and proxy run in Docker Compose.

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
