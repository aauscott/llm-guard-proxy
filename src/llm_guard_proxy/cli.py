"""Command-line entry point for the proxy server."""

import argparse
import os
from collections.abc import Sequence

import uvicorn

from llm_guard_proxy import __version__
from llm_guard_proxy.config import get_settings


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="llm-guard-proxy",
        description="Run policy guardrails in front of an OpenAI-compatible model API.",
    )
    parser.add_argument("--host", default=os.getenv("GUARD_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.getenv("GUARD_PORT", "8000")))
    parser.add_argument("--upstream", help="Model server base URL, without /v1")
    parser.add_argument(
        "--policy",
        help="Bundled policy name (for example, permissive) or a YAML file path",
    )
    parser.add_argument("--reload", action="store_true", help="Reload after source changes")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser


def main(argv: Sequence[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    _set_if_present("GUARD_UPSTREAM_BASE_URL", args.upstream)
    _set_if_present("GUARD_POLICY_PATH", args.policy)
    get_settings.cache_clear()

    uvicorn.run(
        "llm_guard_proxy.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
    )


def _set_if_present(name: str, value: str | None) -> None:
    if value is not None:
        os.environ[name] = value


if __name__ == "__main__":
    main()
