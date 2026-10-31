"""Local-first policy guardrails for OpenAI-compatible chat APIs."""

from importlib.metadata import PackageNotFoundError, version


try:
    __version__ = version("llm-guard-proxy")
except PackageNotFoundError:  # pragma: no cover - used from an uninstalled source tree
    __version__ = "0.2.0"


__all__ = ["__version__"]
