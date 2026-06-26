from fastapi import FastAPI

from app.config import get_settings
from app.logging.audit import configure_logging
from app.policy.loader import load_policy
from app.routes.chat_completions import router as chat_router


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)
    app = FastAPI(title="ai-guard-proxy", version="0.1.0")
    app.state.settings = settings
    app.state.policy = load_policy(settings.policy_path)
    app.include_router(chat_router)
    return app


app = create_app()
