# Product Brief

## Name

`ai-guard-proxy`

## One-Sentence Description

A local-first, OpenAI-compatible security proxy for LLM chat apps and coding agents, with policy-driven filtering and plugin-based classifiers.

## Problem

Organizations want to run LLMs locally or privately but need control over what users can ask and what models can return. A school, a company, a home lab, and a coding-agent workflow may all need different rules.

Hard-coding rules into a UI or a model server is brittle. The security layer should be independent, configurable, testable, and reusable across many clients and model backends.

## Target Users

- Individuals running Ollama locally.
- Schools deploying local LLMs to students or staff.
- Companies experimenting with internal LLM assistants.
- Developers using local coding agents.
- Security researchers building guardrail experiments.

## MVP Use Case

Run Open WebUI locally, point it to `ai-guard-proxy`, and have the proxy forward safe requests to Ollama while blocking unsafe input or output based on YAML policy.

## Future Use Cases

- Coding agents such as Continue.dev, Aider, OpenHands, or similar tools.
- Multiple LLM backends.
- Model-based safety classifiers.
- Organization-specific policy packs.
- Admin UI for policies and logs.
- Distributed deployment for teams.

## Non-Goals For MVP

- Perfect safety.
- Full enterprise identity management.
- Full admin dashboard.
- Replacing existing LLM gateways.
- Heavy model-based guardrails by default.
- Cloud dependency.

## Success Criteria

- Easy to run locally.
- Easy to point Open WebUI at it.
- Clear policy files.
- Clear classifier plugin contract.
- Fast enough that normal chat remains usable.
- Tests cover policy loading, classifier behavior, and block/allow flow.

