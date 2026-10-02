# @spec docs/BACKLOG.md#RG-004 | docs/DAT.md#pseudonymisation
"""Coffre de pseudonymes : en mémoire vive uniquement, par session, avec durée de vie glissante."""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field

from .taxonomy import Label
from .textutil import TOKEN_CLOSE, TOKEN_OPEN


@dataclass
class _SessionVault:
    by_value: dict[tuple[Label, str], str] = field(default_factory=dict)
    by_token: dict[str, str] = field(default_factory=dict)
    counters: dict[Label, int] = field(default_factory=dict)
    last_access: float = field(default_factory=time.monotonic)


class Vault:
    """Associe chaque valeur exacte à un jeton stable `⟦TYPE_N⟧` au sein d'une session.

    Rien n'est écrit sur disque : un redémarrage du moteur vide le coffre, et les jetons
    antérieurs deviennent inconnus (la réhydratation est alors refusée).
    """

    def __init__(self, ttl_seconds: int, clock: object = time.monotonic) -> None:
        self.ttl_seconds = ttl_seconds
        self._clock = clock
        self._sessions: dict[str, _SessionVault] = {}
        self._lock = threading.Lock()

    def _now(self) -> float:
        return self._clock()  # type: ignore[operator, no-any-return]

    def _session(self, session_id: str) -> _SessionVault:
        vault = self._sessions.get(session_id)
        if vault is None:
            vault = _SessionVault(last_access=self._now())
            self._sessions[session_id] = vault
        vault.last_access = self._now()
        return vault

    def token_for(self, session_id: str, label: Label, value: str) -> str:
        with self._lock:
            vault = self._session(session_id)
            key = (label, value)
            token = vault.by_value.get(key)
            if token is None:
                number = vault.counters.get(label, 0) + 1
                vault.counters[label] = number
                token = f"{TOKEN_OPEN}{label.value}_{number}{TOKEN_CLOSE}"
                vault.by_value[key] = token
                vault.by_token[token] = value
            return token

    def value_for(self, session_id: str, token: str) -> str | None:
        with self._lock:
            vault = self._sessions.get(session_id)
            if vault is None:
                return None
            vault.last_access = self._now()
            return vault.by_token.get(token)

    def purge_expired(self) -> int:
        with self._lock:
            limit = self._now() - self.ttl_seconds
            expired = [sid for sid, vault in self._sessions.items() if vault.last_access < limit]
            for sid in expired:
                del self._sessions[sid]
            return len(expired)

    def stats(self) -> dict[str, int]:
        """Comptages agrégés uniquement : aucune valeur ni aucun jeton n'est exposé."""
        with self._lock:
            return {
                "sessions": len(self._sessions),
                "tokens": sum(len(v.by_token) for v in self._sessions.values()),
            }
