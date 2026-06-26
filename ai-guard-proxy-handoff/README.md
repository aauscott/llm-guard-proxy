# AI Guard Proxy Handoff

This folder is a handoff package for building a policy-driven, plugin-based LLM security proxy.

The intended product is a local-first security gateway that can sit between chat UIs, coding agents, and LLM backends such as Ollama. It should inspect both user input and model output, run multiple classifiers in parallel, apply an organization-specific policy, and return either the model response or a safe canned response.

## Intended Architecture

```text
Client UI or Coding Agent
  -> OpenAI-compatible Security Proxy
    -> Input guard pipeline
    -> Policy engine
    -> LLM backend, usually Ollama first
    -> Output guard pipeline
    -> Policy engine
  -> Final response
```

## Key Product Principles

- Policy-driven: organizations define what they want to allow, block, warn, redact, or log.
- Plugin-based: new classifiers should be easy to add without rewriting the proxy.
- Local-first: the MVP should run locally with Open WebUI and Ollama.
- OpenAI-compatible: clients should be able to point to the proxy as if it were an OpenAI-compatible API.
- Fast by default: cheap checks first, parallel classifier execution second, slow model-based checks only when configured or needed.
- Useful defaults: ship school, enterprise, coding-agent, and permissive policy examples.

## Files In This Handoff

- `CODEX_PROMPT.md`: paste this into a coding-agent chat to start implementation.
- `PRODUCT_BRIEF.md`: what the project is and who it serves.
- `TECHNICAL_SPEC.md`: implementation details, APIs, modules, data models, and MVP scope.
- `POLICY_SCHEMA.md`: policy terminology and YAML structure.
- `CLASSIFIER_PLUGIN_SPEC.md`: contract for adding classifiers.
- `ROADMAP.md`: phased build plan.
- `TEST_PLAN.md`: testing strategy.
- `SECURITY_CONSIDERATIONS.md`: safety/security concerns for chat and coding-agent use.
- `example-policies/`: starter policy packs for different use cases.

