# Security Considerations

## This Is A Guardrail, Not A Guarantee

The proxy should reduce risk, but it should not claim perfect protection. Policies and classifiers can miss adversarial content or produce false positives.

## Do Not Log Sensitive Prompts By Default

Audit logs should capture decisions and metadata, not full prompts, unless explicitly enabled for local debugging.

## Input And Output Checks Are Both Required

Input checks stop unsafe requests before they reach the model. Output checks stop unsafe model responses, leaks, or policy-violating content before the user sees them.

## Coding Agents Need Extra Boundaries

For coding agents, plain chat filtering is not enough. Later versions should inspect:

- shell commands
- tool calls
- file reads
- file writes
- diffs
- retrieved web content
- repository files
- environment variables

## Indirect Prompt Injection

Agents can read malicious instructions from files, docs, websites, GitHub issues, dependency READMEs, or tool outputs. These should be treated as untrusted context, not instructions.

## Fail Open vs Fail Closed

Policies should choose behavior when classifiers fail:

- `fail_open`: useful for development and low-risk home use.
- `fail_closed`: better for schools, enterprise, or sensitive workflows.

## Canned Responses

Blocked responses should be generic and should not reveal classifier internals. Example:

```text
I can't help with that request.
```

For schools, a friendlier response may be appropriate:

```text
I can't help with that, but I can help with a safer version of the question.
```

## Secrets

The proxy should avoid:

- returning secrets in responses
- logging secrets
- forwarding obvious secrets to external backends
- including secrets in error messages

## Public Repo Guidance

Include clear disclaimers:

- The project is experimental.
- Users must define policies appropriate to their environment.
- No default policy is perfect.
- Safety decisions should be tested before deployment.

