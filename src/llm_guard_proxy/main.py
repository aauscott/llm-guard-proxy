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
    app.include_router(chat_router)
    return app


app = create_app()
