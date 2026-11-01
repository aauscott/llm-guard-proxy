"""Small, opt-in policy editor for a single local proxy process."""

import hashlib
import secrets
import tempfile
from importlib.resources import files
from pathlib import Path
from urllib.parse import urlsplit

import yaml
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, Response
from pydantic import BaseModel

from llm_guard_proxy.classifiers.registry import CLASSIFIERS
from llm_guard_proxy.policy.loader import load_policy, validate_classifier_names, validate_regex_patterns
from llm_guard_proxy.policy.schema import Policy


def local_only(request: Request) -> None:
    if not request.client or request.client.host not in {"127.0.0.1", "::1"}:
        raise HTTPException(403, "The policy editor is available only on this computer.")
    if request.url.hostname not in {"localhost", "127.0.0.1", "::1"}:
        raise HTTPException(403, "Open the editor using localhost or 127.0.0.1.")
    origin = request.headers.get("origin")
    if origin and urlsplit(origin).netloc != request.url.netloc:
        raise HTTPException(403, "Cross-origin requests are not allowed.")
    if request.headers.get("sec-fetch-site") == "cross-site":
        raise HTTPException(403, "Cross-site requests are not allowed.")


router = APIRouter(prefix="/admin", dependencies=[Depends(local_only)])


def revision(policy: Policy) -> str:
    return hashlib.sha256(policy.model_dump_json().encode()).hexdigest()


@router.get("", response_class=HTMLResponse)
def editor():
    return HTMLResponse(files("llm_guard_proxy").joinpath("static", "admin.html").read_text(), headers={
        "Cache-Control": "no-store", "X-Frame-Options": "DENY",
        "Content-Security-Policy": "default-src 'self'; script-src 'self'; style-src 'self'; frame-ancestors 'none'; base-uri 'none'",
    })


@router.get("/assets/{name}")
def asset(name: str):
    if name not in {"admin.js", "admin.css"}:
        raise HTTPException(404)
    return Response(files("llm_guard_proxy").joinpath("static", name).read_text(),
                    media_type="text/javascript" if name.endswith(".js") else "text/css")


@router.get("/policy")
def current(request: Request, response: Response):
    response.headers["Cache-Control"] = "no-store"
    policy = request.app.state.policy
    return {"policy": policy.model_dump(), "revision": revision(policy),
            "token": request.app.state.admin_token,
            "path": str(Path(request.app.state.settings.admin_policy_path).resolve()),
            "classifiers": list(CLASSIFIERS),
            "templates": {p.stem: load_policy(p).model_dump() for p in
                          files("llm_guard_proxy").joinpath("policies").iterdir() if p.name.endswith(".yaml")}}


class SavePolicy(BaseModel):
    policy: Policy
    revision: str


@router.put("/policy")
async def save(body: SavePolicy, request: Request):
    if not secrets.compare_digest(request.headers.get("x-editor-token", ""), request.app.state.admin_token):
        raise HTTPException(403, "Reload the editor before saving.")
    if body.revision != revision(request.app.state.policy):
        raise HTTPException(409, "The active policy changed. Reload the page before saving.")
    try:
        if not body.policy.name.strip():
            raise ValueError("Policy name is required.")
        validate_classifier_names(body.policy)
        validate_regex_patterns(body.policy)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    # No await between checking the revision, atomic persistence, and activation.
    path = Path(request.app.state.settings.admin_policy_path)
    temporary = None
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(mode="w", dir=path.parent, delete=False) as handle:
            temporary = Path(handle.name)
            yaml.safe_dump(body.policy.model_dump(), handle, sort_keys=False)
        temporary.replace(path)
    except OSError as exc:
        raise HTTPException(500, "Could not save the policy. Check the policy folder permissions.") from exc
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    request.app.state.policy = body.policy
    return {"revision": revision(body.policy)}
