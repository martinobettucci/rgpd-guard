# @spec docs/BACKLOG.md#RG-012 | docs/DAT.md#securite
"""Authentification locale : jeton d'en-tête pour les hooks, cookie de session pour le dashboard."""

from __future__ import annotations

import hmac
import secrets
import threading
import time

from fastapi import HTTPException, Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp

TOKEN_HEADER = "X-RGPD-Guard-Token"  # noqa: S105 (nom d'en-tête)
SESSION_COOKIE = "rgpd_guard_session"
SESSION_IDLE_SECONDS = 8 * 3600
MUTATING_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})


def token_matches(expected: str, provided: str | None) -> bool:
    return bool(expected) and provided is not None and hmac.compare_digest(expected.encode(), provided.encode())


class SessionStore:
    """Sessions du dashboard, en mémoire uniquement."""

    def __init__(self, idle_seconds: int = SESSION_IDLE_SECONDS) -> None:
        self.idle_seconds = idle_seconds
        self._sessions: dict[str, float] = {}
        self._lock = threading.Lock()

    def create(self) -> str:
        session_id = secrets.token_urlsafe(32)
        with self._lock:
            self._sessions[session_id] = time.monotonic()
        return session_id

    def valid(self, session_id: str | None) -> bool:
        if not session_id:
            return False
        with self._lock:
            last = self._sessions.get(session_id)
            if last is None or time.monotonic() - last > self.idle_seconds:
                self._sessions.pop(session_id, None)
                return False
            self._sessions[session_id] = time.monotonic()
            return True

    def revoke(self, session_id: str | None) -> None:
        if session_id:
            with self._lock:
                self._sessions.pop(session_id, None)


class OriginGuard(BaseHTTPMiddleware):
    """Refuse les requêtes modifiantes provenant d'une origine non autorisée (falsification, DNS rebinding)."""

    def __init__(self, app: ASGIApp, allowed_origins: list[str]) -> None:
        super().__init__(app)
        self.allowed_origins = set(allowed_origins)

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if request.method in MUTATING_METHODS:
            origin = request.headers.get("origin")
            if origin and origin not in self.allowed_origins:
                return JSONResponse({"detail": "Origine non autorisée."}, status_code=403)
            content_type = request.headers.get("content-type", "")
            has_body = request.headers.get("content-length", "0") not in ("", "0")
            if has_body and not content_type.startswith("application/json"):
                return JSONResponse({"detail": "Corps JSON attendu."}, status_code=415)
        return await call_next(request)


def require_token(request: Request) -> None:
    expected: str = request.app.state.engine.settings.token
    if not token_matches(expected, request.headers.get(TOKEN_HEADER)):
        raise HTTPException(status_code=401, detail="Jeton RGPD Guard absent ou invalide.")


def require_session(request: Request) -> None:
    sessions: SessionStore = request.app.state.sessions
    if not sessions.valid(request.cookies.get(SESSION_COOKIE)):
        raise HTTPException(status_code=401, detail="Session expirée ou absente : reconnectez-vous.")


def require_session_or_token(request: Request) -> None:
    expected: str = request.app.state.engine.settings.token
    if token_matches(expected, request.headers.get(TOKEN_HEADER)):
        return
    require_session(request)
