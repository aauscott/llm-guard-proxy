"""Optional local Transformers/PEFT service; independent of the proxy process."""

import argparse
from contextlib import asynccontextmanager
from threading import Lock
from typing import Literal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from llm_guard_proxy.classifiers.llama_guard import _findings_from_verdict
from llm_guard_proxy.clients.http_guard import GuardVerdict

BASE_MODEL = "meta-llama/Llama-Guard-3-1B"
BASE_REVISION = "acf7aafa60f0410f8f42b1fa35e077d705892029"
ADAPTER = "aascott/Llama-Guard-3-1B-Confusable-Guard-LoRA"
ADAPTER_REVISION = "81e8725c8a58713c05b74d5f999b0565e1d1201e"


class GuardMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1)


class ClassificationRequest(BaseModel):
    messages: list[GuardMessage] = Field(min_length=1)


def render_messages(messages: list[GuardMessage]) -> list[dict]:
    """Adapt text to the base model's template and combine consecutive same-role turns."""
    if messages[0].role != "user":
        raise ValueError("Conversation must start with a user message")
    result: list[dict] = []
    for message in messages:
        if result and result[-1]["role"] == message.role:
            result[-1]["content"][0]["text"] += "\n" + message.content
        else:
            result.append({"role": message.role, "content": [{"type": "text", "text": message.content}]})
    return result


class GuardModel:
    def __init__(self, base_model: str, base_revision: str, adapter: str, adapter_revision: str):
        import torch
        from peft import PeftModel
        from transformers import AutoModelForCausalLM, AutoTokenizer

        self.torch = torch
        self.device = "cuda" if torch.cuda.is_available() else "mps" if torch.backends.mps.is_available() else "cpu"
        # Match the training repository's conservative float32 choice on Apple Silicon.
        dtype = torch.bfloat16 if self.device == "cuda" and torch.cuda.is_bf16_supported() else torch.float32
        self.tokenizer = AutoTokenizer.from_pretrained(base_model, revision=base_revision)
        if self.tokenizer.pad_token_id is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token
        base = AutoModelForCausalLM.from_pretrained(
            base_model, revision=base_revision, torch_dtype=dtype, low_cpu_mem_usage=True,
        )
        self.model = PeftModel.from_pretrained(base, adapter, revision=adapter_revision).to(self.device)
        self.model.eval()

    def classify(self, messages: list[dict]) -> str:
        inputs = self.tokenizer.apply_chat_template(
            messages, tokenize=True, add_generation_prompt=True,
            return_dict=True, return_tensors="pt",
        )
        width = inputs["input_ids"].shape[-1]
        if width + 32 > self.model.config.max_position_embeddings:
            raise ValueError("Conversation exceeds guard context window; text was not truncated")
        inputs = {name: tensor.to(self.device) for name, tensor in inputs.items()}
        with self.torch.inference_mode():
            output = self.model.generate(
                **inputs, max_new_tokens=32, do_sample=False,
                pad_token_id=self.tokenizer.pad_token_id,
            )
        return self.tokenizer.decode(
            output[0, width:], skip_special_tokens=True, clean_up_tokenization_spaces=False,
        ).strip()


def create_guard_app(model_factory=GuardModel, **model_options) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app):
        app.state.model = model_factory(**model_options)
        yield
        del app.state.model

    app = FastAPI(title="Local Llama Guard", lifespan=lifespan)
    inference_lock = Lock()

    @app.get("/health")
    def health():
        return {"status": "ready"}

    @app.post("/classify", response_model=GuardVerdict)
    def classify(payload: ClassificationRequest):
        try:
            messages = render_messages(payload.messages)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        # One resident model, one generation at a time. Avoid accumulating stale work.
        if not inference_lock.acquire(blocking=False):
            raise HTTPException(status_code=503, detail="Guard model is busy; retry later")
        try:
            try:
                raw = app.state.model.classify(messages)
            except ValueError as exc:
                raise HTTPException(status_code=422, detail="Guard could not process the conversation") from exc
            try:
                findings = _findings_from_verdict(raw, severity="high", model="local-guard")
            except ValueError as exc:
                raise HTTPException(status_code=502, detail="Guard returned a malformed verdict") from exc
            return GuardVerdict(
                verdict="unsafe" if findings else "safe",
                categories=[f.metadata["hazard_code"] for f in findings if f.metadata["hazard_code"]],
            )
        finally:
            inference_lock.release()

    return app


def main():
    parser = argparse.ArgumentParser(description="Serve the Confusable Guard adapter locally")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8001)
    parser.add_argument("--base-model", default=BASE_MODEL)
    parser.add_argument("--base-revision", default=BASE_REVISION)
    parser.add_argument("--adapter", default=ADAPTER, help="Hugging Face ID or local adapter directory")
    parser.add_argument("--adapter-revision", default=ADAPTER_REVISION)
    args = parser.parse_args()
    import uvicorn

    app = create_guard_app(
        base_model=args.base_model, base_revision=args.base_revision,
        adapter=args.adapter, adapter_revision=args.adapter_revision,
    )
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
