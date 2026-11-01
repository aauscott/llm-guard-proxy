import secrets
from pathlib import Path

from fastapi import FastAPI

from llm_guard_proxy import __version__
from llm_guard_proxy.config import get_settings
from llm_guard_proxy.logging.audit import configure_logging
from llm_guard_proxy.policy.loader import load_policy
from llm_guard_proxy.routes.chat_completions import router as chat_router


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)
    app = FastAPI(title="llm-guard-proxy", version=__version__)
    app.state.settings = settings
    app.state.policy = load_policy(settings.policy_path)
    if settings.admin_enabled:
        from llm_guard_proxy.routes.admin import router as admin_router

        if Path(settings.admin_policy_path).is_file():
            app.state.policy = load_policy(settings.admin_policy_path)
        app.state.admin_token = secrets.token_urlsafe(32)
        app.include_router(admin_router)
    app.include_router(chat_router)
    return app


app = create_app()
