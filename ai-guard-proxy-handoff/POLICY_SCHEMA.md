# Policy Schema

Policies should be YAML files. They define which classifiers run, how results are interpreted, and what response/action to take.

## Terminology

| Term | Meaning |
|---|---|
| `classifier` | A module that scores or labels content |
| `scanner` | A deterministic classifier, often regex/rule based |
| `policy` | Organization-specific rules |
| `category` | Type of issue, such as `prompt_injection` or `pii_leak` |
| `severity` | `low`, `medium`, `high`, or `critical` |
| `confidence` | Float from `0.0` to `1.0` |
| `action` | `allow`, `warn`, `redact`, `block`, `log`, or `review` |
| `policy pack` | A reusable preset policy for a specific use case |

## Example Shape

```yaml
name: school_default
description: Conservative defaults for a school-hosted local LLM.
mode: fail_closed

defaults:
  classifier_timeout_ms: 750
  log_prompts: false
  canned_response: "I can't help with that request."

stages:
  input:
    enabled_classifiers:
      - terms
      - regex
      - secrets
      - prompt_injection
      - url_obfuscation
  output:
    enabled_classifiers:
      - terms
      - regex
      - secrets
      - prompt_injection

actions:
  critical: block
  high: block
  medium: warn
  low: log

categories:
  prompt_injection:
    min_action: block
  secret_leak:
    min_action: block
  explicit_content:
    min_action: block

terms:
  block:
    - "example blocked term"
  warn:
    - "example warning term"

regex:
  block:
    - name: example_private_key
      pattern: "-----BEGIN (RSA|OPENSSH|EC|DSA)? ?PRIVATE KEY-----"
      category: secret_leak
      severity: critical
  warn: []
```

## Policy Decision Rules

Suggested MVP logic:

1. If any finding maps to `block`, block.
2. Else if any finding maps to `warn`, allow but log warning.
3. Else if any finding maps to `log`, allow and log.
4. Else allow.

The engine should consider:

- explicit `action_hint` from classifier
- category-specific policy
- severity fallback
- confidence threshold

## Confidence Thresholds

Optional:

```yaml
thresholds:
  block: 0.85
  warn: 0.55
```

If omitted, deterministic classifiers can default to `1.0` confidence for exact matches.

## Customization Goals

Users should be able to:

- Add blocked terms without editing Python.
- Add regex detectors without editing Python.
- Disable classifiers.
- Change block/warn behavior by category.
- Change canned responses.
- Use different policies for schools, companies, coding agents, and home labs.

