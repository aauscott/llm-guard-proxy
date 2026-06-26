import json
import time
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from app.clients.ollama import OllamaClient
from app.config import Settings
from app.guards.input_guard import inspect_input
from app.guards.output_guard import inspect_output
from app.logging.audit import audit_guard
from app.models import ChatCompletionRequest, GuardItem
from app.policy.loader import classifier_config
from app.policy.schema import Policy


router = APIRouter()


@router.get("/v1/models")
async def models(request: Request) -> dict[str, Any]:
    settings: Settings = request.app.state.settings
    client = OllamaClient(settings.ollama_base_url)
    return await client.models()


@router.post("/v1/chat/completions", response_model=None)
async def chat_completions(payload: ChatCompletionRequest, request: Request) -> dict[str, Any] | StreamingResponse:
    settings: Settings = request.app.state.settings
    policy: Policy = request.app.state.policy
    request_id = request.headers.get("x-request-id", str(uuid4()))
    config = classifier_config(policy)

    input_text = _messages_to_text(payload.messages)
    input_item = GuardItem(
        request_id=request_id,
        stage="input",
        text=input_text,
        messages=payload.messages,
        metadata={"model": payload.model},
    )
    input_result = await inspect_input(input_item, policy, config)
    audit_guard(
        request_id=request_id,
        stage="input",
        policy=policy,
        result=input_result,
        log_prompts=policy.defaults.log_prompts,
        text=input_text,
    )
    if input_result.decision.blocked:
        if payload.stream:
            return StreamingResponse(
                stream_blocked_response(request_id, policy, payload.model),
                media_type="text/event-stream",
            )
        return blocked_response(request_id, policy, payload.model)

    client = OllamaClient(settings.ollama_base_url)
    if payload.stream:
        stream_chunks = await client.stream_chat_completions(payload.model_dump(exclude_none=True))
        output_text = _assistant_text_from_stream(stream_chunks)
        output_item = GuardItem(
            request_id=request_id,
            stage="output",
            text=output_text,
            metadata={"model": payload.model},
        )
        output_result = await inspect_output(output_item, policy, config)
        audit_guard(
            request_id=request_id,
            stage="output",
            policy=policy,
            result=output_result,
            log_prompts=policy.defaults.log_prompts,
            text=output_text,
        )
        if output_result.decision.blocked:
            return StreamingResponse(
                stream_blocked_response(request_id, policy, payload.model),
                media_type="text/event-stream",
            )
        return StreamingResponse(iter(stream_chunks), media_type="text/event-stream")

    backend_response = await client.chat_completions(payload.model_dump(exclude_none=True))

    output_text = _assistant_text(backend_response)
    output_item = GuardItem(
        request_id=request_id,
        stage="output",
        text=output_text,
        metadata={"model": payload.model},
    )
    output_result = await inspect_output(output_item, policy, config)
    audit_guard(
        request_id=request_id,
        stage="output",
        policy=policy,
        result=output_result,
        log_prompts=policy.defaults.log_prompts,
        text=output_text,
    )
    if output_result.decision.blocked:
        return blocked_response(request_id, policy, payload.model)

    return backend_response


def blocked_response(request_id: str, policy: Policy, model: str) -> dict[str, Any]:
    return {
        "id": f"guard-blocked-{request_id}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": model or "guard-policy",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": policy.defaults.canned_response,
                },
                "finish_reason": "stop",
            }
        ],
    }


def stream_blocked_response(request_id: str, policy: Policy, model: str):
    response_id = f"guard-blocked-{request_id}"
    created = int(time.time())
    first_chunk = {
        "id": response_id,
        "object": "chat.completion.chunk",
        "created": created,
        "model": model or "guard-policy",
        "choices": [
            {
                "index": 0,
                "delta": {
                    "role": "assistant",
                    "content": policy.defaults.canned_response,
                },
                "finish_reason": None,
            }
        ],
    }
    final_chunk = {
        "id": response_id,
        "object": "chat.completion.chunk",
        "created": created,
        "model": model or "guard-policy",
        "choices": [
            {
                "index": 0,
                "delta": {},
                "finish_reason": "stop",
            }
        ],
    }
    yield f"data: {json.dumps(first_chunk)}\n\n"
    yield f"data: {json.dumps(final_chunk)}\n\n"
    yield "data: [DONE]\n\n"


def _messages_to_text(messages: list[Any]) -> str:
    parts: list[str] = []
    for message in messages:
        content = message.content
        if isinstance(content, str):
            parts.append(content)
        elif isinstance(content, list):
            for item in content:
                if item.get("type") == "text":
                    parts.append(str(item.get("text", "")))
    return "\n".join(parts)


def _assistant_text(response: dict[str, Any]) -> str:
    parts: list[str] = []
    for choice in response.get("choices", []):
        message = choice.get("message", {})
        content = message.get("content")
        if isinstance(content, str):
            parts.append(content)
    return "\n".join(parts)


def _assistant_text_from_stream(chunks: list[str]) -> str:
    parts: list[str] = []
    for line in "".join(chunks).splitlines():
        if not line.startswith("data:"):
            continue
        data = line.removeprefix("data:").strip()
        if not data or data == "[DONE]":
            continue
        try:
            payload = json.loads(data)
        except json.JSONDecodeError:
            continue
        for choice in payload.get("choices", []):
            delta = choice.get("delta", {})
            if isinstance(delta.get("content"), str):
                parts.append(delta["content"])
            message = choice.get("message", {})
            if isinstance(message.get("content"), str):
                parts.append(message["content"])
    return "".join(parts)
