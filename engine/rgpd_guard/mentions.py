# @spec docs/BACKLOG.md#RG-005 | docs/DAT.md#flux
"""Résolution des mentions `@chemin` d'un prompt : Claude Code injecte leur contenu sans hook d'outil."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

_MENTION_RE = re.compile(r'(?:(?<=\s)|^)@(?:"([^"\n]+)"|([^\s"]+))')
_LINE_SUFFIX_RE = re.compile(r"#L\d+(?:-\d+)?$")
_TRAILING = ".,;:!?)]}'"
MAX_MENTION_BYTES = 2_000_000


class MentionStatus(StrEnum):
    TEXT = "text"  # fichier texte lisible : contenu à analyser
    DIRECTORY = "directory"  # dossier : seule la liste des noms est injectée
    BINARY = "binary"  # fichier non textuel (image, PDF...) : non analysable
    TOO_LARGE = "too_large"
    OUT_OF_REACH = "out_of_reach"  # ressemble à un fichier mais hors du dossier monté
    NOT_A_FILE = "not_a_file"  # adresse, pseudo, chemin inexistant


@dataclass
class Mention:
    raw: str
    path: str
    status: MentionStatus
    content: str = ""


def _looks_like_path(candidate: str) -> bool:
    return "/" in candidate or "\\" in candidate or bool(re.search(r"\.[A-Za-z0-9]{1,8}$", candidate))


def _within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def extract_mentions(prompt: str) -> list[str]:
    raws = []
    for match in _MENTION_RE.finditer(prompt):
        candidate = match.group(1) or match.group(2) or ""
        if not match.group(1):
            candidate = candidate.rstrip(_TRAILING)
        candidate = _LINE_SUFFIX_RE.sub("", candidate)
        if candidate and "@" not in candidate:
            raws.append(candidate)
    return raws


def resolve_mentions(prompt: str, cwd: str, workspace_root: Path | None) -> list[Mention]:
    mentions = []
    for raw in extract_mentions(prompt):
        expanded = os.path.expanduser(raw) if raw.startswith("~") else raw
        path = Path(os.path.normpath(os.path.join(cwd or "/", expanded)))
        if workspace_root is None or not _within(path, workspace_root.resolve()):
            status = MentionStatus.OUT_OF_REACH if _looks_like_path(raw) else MentionStatus.NOT_A_FILE
            mentions.append(Mention(raw, str(path), status))
            continue
        try:
            if path.is_dir():
                mentions.append(Mention(raw, str(path), MentionStatus.DIRECTORY))
                continue
            if not path.is_file():
                mentions.append(Mention(raw, str(path), MentionStatus.NOT_A_FILE))
                continue
            if path.stat().st_size > MAX_MENTION_BYTES:
                mentions.append(Mention(raw, str(path), MentionStatus.TOO_LARGE))
                continue
            data = path.read_bytes()
        except OSError:  # droits insuffisants pour le moteur : on ne peut pas vérifier, donc hors de portée
            mentions.append(Mention(raw, str(path), MentionStatus.OUT_OF_REACH))
            continue
        if b"\x00" in data[:8192]:
            mentions.append(Mention(raw, str(path), MentionStatus.BINARY))
            continue
        try:
            content = data.decode("utf-8")
        except UnicodeDecodeError:
            mentions.append(Mention(raw, str(path), MentionStatus.BINARY))
            continue
        mentions.append(Mention(raw, str(path), MentionStatus.TEXT, content))
    return mentions
