# @spec docs/BACKLOG.md#RG-004 | docs/DAT.md#pseudonymisation
"""Remplacement des valeurs détectées par des jetons, et réinjection des valeurs d'origine."""

from __future__ import annotations

from dataclasses import dataclass

from .models import Finding
from .textutil import TOKEN_RE
from .vault import Vault


def pseudonymize(text: str, findings: list[Finding], vault: Vault, session_id: str) -> str:
    """Remplace chaque valeur par son jeton de session. Les spans ne se recouvrent pas (fusion préalable)."""
    out: list[str] = []
    cursor = 0
    for finding in sorted(findings, key=lambda f: f.span.start):
        if finding.span.start < cursor:
            continue
        out.append(text[cursor : finding.span.start])
        out.append(vault.token_for(session_id, finding.span.label, finding.value))
        cursor = finding.span.end
    out.append(text[cursor:])
    return "".join(out)


@dataclass
class Rehydration:
    text: str
    replaced: int
    unknown: list[str]


def rehydrate(text: str, vault: Vault, session_id: str) -> Rehydration:
    """Réinjecte la valeur exacte de chaque jeton connu ; liste les jetons inconnus."""
    unknown: list[str] = []
    replaced = 0

    def _sub(match: object) -> str:
        nonlocal replaced
        token = match.group(0)  # type: ignore[attr-defined]
        value = vault.value_for(session_id, token)
        if value is None:
            unknown.append(token)
            return str(token)
        replaced += 1
        return value

    result = TOKEN_RE.sub(_sub, text)
    return Rehydration(text=result, replaced=replaced, unknown=unknown)


def contains_token(text: str) -> bool:
    return TOKEN_RE.search(text) is not None
