# @spec docs/BACKLOG.md#RG-006 | docs/DAT.md#flux
"""Parcours générique d'une sortie d'outil : seules les feuilles texte sont transformées, la forme est conservée."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

# Clés techniques jamais transformées : chemins, types, identifiants, indicateurs.
TECHNICAL_KEYS: frozenset[str] = frozenset(
    {
        "filePath",
        "file_path",
        "path",
        "type",
        "status",
        "mode",
        "id",
        "agentId",
        "tool_use_id",
        "backgroundTaskId",
        "returnCodeInterpretation",
        "resolvedModel",
        "outputFile",
        "media_type",
        "mimeType",
        "url",
        "uri",
        "name",
    }
)
_BINARY_BLOCK_TYPES: frozenset[str] = frozenset({"image", "document", "audio"})

Transform = Callable[[str], tuple[str, int]]


def walk(value: Any, transform: Transform) -> tuple[Any, int]:
    """Renvoie une copie transformée et le nombre total de remplacements."""
    if isinstance(value, str):
        return transform(value)
    if isinstance(value, list):
        items = []
        total = 0
        for item in value:
            new_item, count = walk(item, transform)
            items.append(new_item)
            total += count
        return items, total
    if isinstance(value, dict):
        if value.get("type") in _BINARY_BLOCK_TYPES or "isImage" in value and value.get("isImage") is True:
            return value, 0
        result: dict[str, Any] = {}
        total = 0
        for key, item in value.items():
            if key in TECHNICAL_KEYS and not isinstance(item, (dict, list)):
                result[key] = item
                continue
            new_item, count = walk(item, transform)
            result[key] = new_item
            total += count
        return result, total
    return value, 0


def iter_strings(value: Any) -> list[str]:
    """Toutes les feuilles texte non techniques, pour un contrôle sans réécriture."""
    found: list[str] = []

    def _collect(text: str) -> tuple[str, int]:
        found.append(text)
        return text, 0

    walk(value, _collect)
    return found
