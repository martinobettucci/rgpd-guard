# @spec docs/BACKLOG.md#RG-009 | docs/DAT.md#moteur
"""Détecteur GLiNER : entités personnelles en zero-shot, multilingue, par fenêtres avec recouvrement."""

from __future__ import annotations

import re
import threading
from typing import Any

from ..config import Settings
from ..models import DetectionContext, Span
from ..taxonomy import Label

LABELS: dict[str, Label] = {
    "person": Label.PERSONNE,
    "address": Label.ADRESSE,
    "date of birth": Label.DATE_NAISSANCE,
    "phone number": Label.TELEPHONE,
    "email": Label.EMAIL,
    "iban": Label.IBAN,
    "credit card number": Label.CARTE_BANCAIRE,
    "social security number": Label.NIR,
}
THRESHOLD = 0.5
WINDOW_WORDS = 250
OVERLAP_WORDS = 40
_WORD_RE = re.compile(r"\S+")


def windows(text: str, size: int = WINDOW_WORDS, overlap: int = OVERLAP_WORDS) -> list[tuple[int, int]]:
    """Découpe en fenêtres de `size` mots se recouvrant de `overlap` mots ; renvoie des positions."""
    words = [(m.start(), m.end()) for m in _WORD_RE.finditer(text)]
    if not words:
        return []
    if len(words) <= size:
        return [(0, len(text))]
    result = []
    step = size - overlap
    for first in range(0, len(words), step):
        last = min(first + size, len(words)) - 1
        result.append((words[first][0], words[last][1]))
        if last == len(words) - 1:
            break
    return result


class GlinerDetector:
    name = "gliner"
    uses_model = True

    def __init__(self, model: Any) -> None:
        self.model = model
        self._lock = threading.Lock()

    def detect(self, text: str, ctx: DetectionContext) -> list[Span]:
        spans: list[Span] = []
        seen: set[tuple[int, int, Label]] = set()
        for start, end in windows(text):
            chunk = text[start:end]
            with self._lock:
                entities = self.model.predict_entities(chunk, list(LABELS), threshold=THRESHOLD)
            for entity in entities:
                label = LABELS.get(entity["label"])
                if label is None:
                    continue
                key = (start + entity["start"], start + entity["end"], label)
                if key in seen:
                    continue
                seen.add(key)
                spans.append(Span(key[0], key[1], label, float(entity["score"]), self.name))
        return spans


def load(settings: Settings) -> tuple[GlinerDetector, dict[str, str]]:
    import torch
    from gliner import GLiNER

    from ..model_store import MODELS, local_path

    torch.set_num_threads(max(1, settings.torch_threads))
    model = GLiNER.from_pretrained(local_path("gliner"), local_files_only=True)
    model.eval()
    return GlinerDetector(model), {"modele": f"{MODELS['gliner'].repo_id} ({MODELS['gliner'].license})"}
