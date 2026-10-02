# @spec docs/BACKLOG.md#RG-004 | docs/BACKLOG.md#RG-007 | docs/DAT.md#moteur
"""Outils texte partagés : jetons de pseudonymisation, blocs de code, langue, fichiers source."""

from __future__ import annotations

import re
from pathlib import PurePath

# Jeton de pseudonymisation : ⟦TYPE_N⟧ (U+27E6, U+27E7).
TOKEN_OPEN = "⟦"  # noqa: S105 (délimiteur de jeton)
TOKEN_CLOSE = "⟧"  # noqa: S105 (délimiteur de jeton)
TOKEN_RE = re.compile(TOKEN_OPEN + r"([A-Z_]+)_(\d+)" + TOKEN_CLOSE)

_FENCE_RE = re.compile(r"(^|\n)(```|~~~)[^\n]*\n.*?(\n\2[ \t]*(?=\n|$)|$)", re.DOTALL)

CODE_EXTENSIONS: frozenset[str] = frozenset(
    {
        ".py",
        ".pyi",
        ".js",
        ".jsx",
        ".ts",
        ".tsx",
        ".mjs",
        ".cjs",
        ".java",
        ".kt",
        ".kts",
        ".go",
        ".rs",
        ".c",
        ".h",
        ".cc",
        ".cpp",
        ".hpp",
        ".cs",
        ".rb",
        ".php",
        ".swift",
        ".scala",
        ".lua",
        ".sh",
        ".bash",
        ".zsh",
        ".ps1",
        ".sql",
        ".css",
        ".scss",
        ".less",
        ".vue",
        ".svelte",
        ".html",
        ".xml",
        ".toml",
        ".ini",
        ".cfg",
        ".gradle",
        ".dart",
        ".r",
        ".m",
        ".pl",
        ".ex",
        ".exs",
        ".clj",
        ".hs",
        ".ml",
    }
)


def token_ranges(text: str) -> list[tuple[int, int]]:
    """Positions des jetons déjà présents, à exclure de toute détection."""
    return [(m.start(), m.end()) for m in TOKEN_RE.finditer(text)]


def mask_for_classifier(text: str, spans: list[tuple[int, int, str | None]]) -> str:
    """Remplace les spans (triés, sans recouvrement) et les jetons existants par des marqueurs neutres.

    `spans` donne pour chaque identifiant `(début, fin, marqueur)` ; un marqueur `None` laisse le texte
    en clair. Un jeton `⟦TYPE_N⟧` devient `[type]`, pour qu'un prompt pseudonymisé recollé soit jugé
    comme le texte d'origine.
    """
    parts: list[str] = []
    cursor = 0
    for start, end, marker in spans:
        if marker is None or start < cursor:
            continue
        parts.append(text[cursor:start])
        parts.append(marker)
        cursor = end
    parts.append(text[cursor:])
    return TOKEN_RE.sub(lambda m: f"[{m.group(1).lower().replace('_', ' ')}]", "".join(parts))


def code_block_ranges(text: str) -> list[tuple[int, int]]:
    """Positions des blocs de code délimités (``` ou ~~~) d'un texte Markdown."""
    ranges = []
    for match in _FENCE_RE.finditer(text):
        start = match.start() + len(match.group(1))
        ranges.append((start, match.end()))
    return ranges


def overlaps(start: int, end: int, ranges: list[tuple[int, int]]) -> bool:
    return any(start < r_end and r_start < end for r_start, r_end in ranges)


def is_code_path(path: str | None) -> bool:
    if not path:
        return False
    return PurePath(path.replace("\\", "/")).suffix.lower() in CODE_EXTENSIONS


_FR_HINTS = re.compile(
    r"\b(le|la|les|des|du|une|est|et|pour|avec|dans|sur|qui|que|pas|je|vous|nous|mon|ma|mes|son|sa|ses|"
    r"cette|aux|au|été|où|né|née)\b",
    re.IGNORECASE,
)
_EN_HINTS = re.compile(
    r"\b(the|and|for|with|this|that|is|are|was|were|you|my|his|her|their|from|have|has|not|of|to|in|born)\b",
    re.IGNORECASE,
)


def guess_language(text: str) -> str:
    """Heuristique légère FR/EN par mots outils ; le français l'emporte à égalité."""
    sample = text[:5000]
    fr = len(_FR_HINTS.findall(sample))
    en = len(_EN_HINTS.findall(sample))
    return "en" if en > fr else "fr"
