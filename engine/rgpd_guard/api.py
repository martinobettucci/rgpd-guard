# @spec docs/BACKLOG.md#RG-001 | docs/BACKLOG.md#RG-010 | docs/BACKLOG.md#RG-011 | docs/BACKLOG.md#RG-012 | docs/DAT.md#api
"""API HTTP du moteur : hooks Claude Code, analyse, journal, politiques, état des moteurs, sessions."""

from __future__ import annotations

import json
import logging
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any, Literal

from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, ValidationError
from starlette.middleware.trustedhost import TrustedHostMiddleware

from . import __version__
from .audit import decision_of, mask
from .auth import (
    SESSION_COOKIE,
    OriginGuard,
    SessionStore,
    require_session,
    require_session_or_token,
    require_token,
    token_matches,
)
from .config import Settings, get_settings
from .hooks import EVENTS
from .mentions import MentionStatus, resolve_mentions
from .models import Context
from .pipeline import PROFILES
from .policy import Policy
from .pseudonymizer import pseudonymize
from .service import Engine
from .taxonomy import CATEGORY_NAMES, LABEL_NAMES
from .textutil import is_code_path

log = logging.getLogger(__name__)
VAULT_PURGE_SECONDS = 300
PROFILE_HEADER = "X-RGPD-Guard-Profile"


class AnalyzeRequest(BaseModel):
    text: str = Field(max_length=2_000_000)
    profile: Literal["rapide", "equilibre", "max"] | None = None
    context: Literal["prompt", "tool_output"] = "prompt"
    code: bool = False
    summary: bool = False


class ScanRequest(BaseModel):
    path: str = Field(min_length=1, max_length=4096)


class LoginRequest(BaseModel):
    token: str = Field(min_length=1, max_length=512)


def _french_errors(exc: ValidationError | RequestValidationError) -> list[dict[str, str]]:
    return [
        {"champ": ".".join(str(p) for p in e.get("loc", ())), "message": str(e.get("msg", ""))} for e in exc.errors()
    ]


def create_app(settings: Settings | None = None, engine: Engine | None = None) -> FastAPI:
    settings = settings or get_settings()
    if not settings.token or not settings.hmac_key:
        raise RuntimeError("RGPD_GUARD_TOKEN et RGPD_GUARD_HMAC_KEY sont obligatoires.")

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.engine = engine or Engine(settings)
        app.state.sessions = SessionStore()
        app.state.last_vault_purge = time.monotonic()
        log.info("moteur prêt : profil %s, composants %s", settings.profile, list(app.state.engine.registry.status))
        yield
        app.state.engine.store.close()

    app = FastAPI(title="RGPD Guard", version=__version__, lifespan=lifespan, docs_url=None, redoc_url=None)
    app.add_middleware(OriginGuard, allowed_origins=settings.cors_origins_list)
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.allowed_hosts_list)

    @app.exception_handler(RequestValidationError)
    async def _validation_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse({"detail": "Requête invalide.", "erreurs": _french_errors(exc)}, status_code=422)

    def get_engine(request: Request) -> Engine:
        eng: Engine = request.app.state.engine
        return eng

    @app.get("/health")
    def health(request: Request) -> dict[str, Any]:
        eng = get_engine(request)
        missing = eng.registry.missing_for_name(settings.profile)
        return {
            "status": "ok",
            "version": __version__,
            "env": settings.env,
            "profile": settings.profile,
            "degraded": missing,
            "components": {s.name: s.ready for s in eng.registry.status.values()},
        }

    @app.post("/v1/hooks/{event}", dependencies=[Depends(require_token)])
    async def hook(event: str, request: Request) -> dict[str, Any]:
        if event not in EVENTS:
            raise HTTPException(status_code=404, detail=f"Événement inconnu : {event}")
        try:
            payload = json.loads(await request.body() or b"{}")
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=400, detail="JSON de hook invalide.") from exc
        if not isinstance(payload, dict):
            raise HTTPException(status_code=400, detail="JSON de hook invalide.")
        profile = request.headers.get(PROFILE_HEADER) or None
        if profile not in PROFILES:
            profile = None
        eng = get_engine(request)
        if time.monotonic() - request.app.state.last_vault_purge > VAULT_PURGE_SECONDS:
            eng.vault.purge_expired()
            request.app.state.last_vault_purge = time.monotonic()
        result: dict[str, Any] = eng.hooks.handle(event, payload, profile)
        return result

    @app.post("/v1/analyze", dependencies=[Depends(require_session_or_token)])
    def analyze(body: AnalyzeRequest, request: Request) -> dict[str, Any]:
        eng = get_engine(request)
        context = Context(body.context)
        analysis = eng.pipeline.analyze(body.text, body.profile or settings.profile, context, body.code)
        counts: dict[str, int] = {}
        for finding in analysis.findings:
            counts[finding.span.label.value] = counts.get(finding.span.label.value, 0) + 1
        result: dict[str, Any] = {
            "decision": decision_of(analysis),
            "profile": analysis.profile,
            "partial": analysis.partial,
            "counts": counts,
            "categories": [
                {
                    "category": c.score.category.value,
                    "name": CATEGORY_NAMES[c.score.category],
                    "probability": round(c.score.probability, 3),
                    "action": c.action.value,
                }
                for c in analysis.categories
            ],
            "timings_ms": analysis.timings_ms,
        }
        if body.summary:
            return result
        sandbox_session = "bac-a-sable"
        result["findings"] = [
            {
                "start": f.span.start,
                "end": f.span.end,
                "label": f.span.label.value,
                "name": LABEL_NAMES[f.span.label],
                "score": round(f.span.score, 3),
                "detector": f.span.detector,
                "validated": f.span.validated,
                "action": f.action.value,
                "preview": mask(f.value),
            }
            for f in analysis.findings
        ]
        result["pseudonymized"] = pseudonymize(body.text, analysis.to_pseudonymize, eng.vault, sandbox_session)
        return result

    @app.post("/v1/scan", dependencies=[Depends(require_token)])
    def scan(body: ScanRequest, request: Request) -> dict[str, Any]:
        """Comptages par type pour un fichier du dossier monté ; aucune valeur n'est renvoyée."""
        eng = get_engine(request)
        mentions = resolve_mentions(f'@"{body.path}"', "/", settings.workspace_root)
        mention = mentions[0] if mentions else None
        if mention is None or mention.status is not MentionStatus.TEXT:
            status = mention.status.value if mention else "not_a_file"
            return {"path": body.path, "status": status, "decision": None, "counts": {}, "categories": []}
        analysis = eng.pipeline.analyze(mention.content, settings.profile, Context.PROMPT, is_code_path(mention.path))
        counts: dict[str, int] = {}
        for finding in analysis.findings:
            counts[LABEL_NAMES[finding.span.label]] = counts.get(LABEL_NAMES[finding.span.label], 0) + 1
        return {
            "path": body.path,
            "status": "analysed",
            "decision": decision_of(analysis),
            "counts": counts,
            "categories": [CATEGORY_NAMES[c.score.category] for c in analysis.categories],
        }

    @app.post("/v1/auth/session")
    def login(body: LoginRequest, request: Request, response: Response) -> dict[str, Any]:
        if not token_matches(settings.token, body.token):
            raise HTTPException(status_code=401, detail="Jeton incorrect.")
        session_id = request.app.state.sessions.create()
        response.set_cookie(SESSION_COOKIE, session_id, httponly=True, samesite="strict", path="/")
        return {"authenticated": True}

    @app.get("/v1/auth/session")
    def whoami(request: Request) -> dict[str, Any]:
        return {"authenticated": request.app.state.sessions.valid(request.cookies.get(SESSION_COOKIE))}

    @app.delete("/v1/auth/session")
    def logout(request: Request, response: Response) -> dict[str, Any]:
        request.app.state.sessions.revoke(request.cookies.get(SESSION_COOKIE))
        response.delete_cookie(SESSION_COOKIE, path="/")
        return {"authenticated": False}

    @app.get("/v1/audit/events", dependencies=[Depends(require_session)])
    def audit_events(
        request: Request,
        limit: int = Query(50, ge=1, le=200),
        offset: int = Query(0, ge=0),
        decision: str | None = Query(None, max_length=32),
        event: str | None = Query(None, max_length=64),
        label: str | None = Query(None, max_length=32),
    ) -> dict[str, Any]:
        events, total = get_engine(request).store.list_events(limit, offset, decision, event, label)
        return {"events": events, "total": total, "limit": limit, "offset": offset}

    @app.get("/v1/audit/stats", dependencies=[Depends(require_session)])
    def audit_stats(request: Request) -> dict[str, Any]:
        return get_engine(request).store.stats()

    @app.get("/v1/policies", dependencies=[Depends(require_session)])
    def get_policy(request: Request) -> dict[str, Any]:
        eng = get_engine(request)
        return {
            "policy": eng.policy.model_dump(mode="json"),
            "source": eng.policy_source,
            "labels": {k.value: v for k, v in LABEL_NAMES.items()},
            "categories": {k.value: v for k, v in CATEGORY_NAMES.items()},
        }

    @app.put("/v1/policies", dependencies=[Depends(require_session)])
    async def put_policy(request: Request) -> JSONResponse:
        try:
            document = json.loads(await request.body() or b"{}")
            policy = Policy.model_validate(document)
        except json.JSONDecodeError:
            return JSONResponse({"detail": "JSON invalide."}, status_code=422)
        except ValidationError as exc:
            return JSONResponse({"detail": "Politique invalide.", "erreurs": _french_errors(exc)}, status_code=422)
        get_engine(request).set_policy(policy)
        return JSONResponse({"policy": policy.model_dump(mode="json"), "source": "custom"})

    @app.post("/v1/policies/reset", dependencies=[Depends(require_session)])
    def reset_policy(request: Request) -> dict[str, Any]:
        eng = get_engine(request)
        eng.set_policy(eng.default_policy, source="default")
        return {"policy": eng.policy.model_dump(mode="json"), "source": "default"}

    @app.get("/v1/engines", dependencies=[Depends(require_session)])
    def engines(request: Request) -> dict[str, Any]:
        eng = get_engine(request)
        bench_file = settings.data_dir / "bench" / "latest.json"
        bench = json.loads(bench_file.read_text(encoding="utf-8")) if bench_file.is_file() else None
        return {
            "default_profile": settings.profile,
            "profiles": {
                name: {
                    "detectors": list(p.detectors),
                    "classifiers_prompt": list(p.classifiers_prompt),
                    "classifiers_output": list(p.classifiers_output),
                    "missing": eng.registry.missing_for(p),
                }
                for name, p in PROFILES.items()
            },
            "components": eng.components(),
            "vault": eng.vault.stats(),
            "bench": bench,
        }

    return app
