# @spec docs/BACKLOG.md#RG-007 | docs/DAT.md#moteur
"""Détecteur spaCy : personnes et lieux en texte libre, pipelines français et anglais sur CPU."""

from __future__ import annotations

import threading
from typing import Any

from ..config import Settings
from ..models import DetectionContext, Span
from ..taxonomy import Label

_LABELS: dict[str, Label] = {
    "PER": Label.PERSONNE,
    "PERSON": Label.PERSONNE,
    "LOC": Label.LIEU,
    "GPE": Label.LIEU,
    "FAC": Label.LIEU,
    "ORG": Label.ORGANISATION,
}
# Mots que la NER prend parfois pour des personnes en tête de phrase.
_STOPWORDS = frozenset(
    {
        "bonjour",
        "bonsoir",
        "salut",
        "merci",
        "cordialement",
        "madame",
        "monsieur",
        "hello",
        "hi",
        "thanks",
        "dear",
        "regards",
        "claude",
    }
)
_EXCLUDED_FR = ["parser", "lemmatizer", "morphologizer", "attribute_ruler", "senter"]
_EXCLUDED_EN = ["parser", "lemmatizer", "tagger", "attribute_ruler", "senter"]
SCORE_PERSON = 0.75
SCORE_OTHER = 0.7


class SpacyDetector:
    name = "spacy"
    uses_model = True

    def __init__(self, pipelines: dict[str, Any]) -> None:
        self.pipelines = pipelines
        self._lock = threading.Lock()

    def detect(self, text: str, ctx: DetectionContext) -> list[Span]:
        nlp = self.pipelines.get(ctx.language or "fr") or self.pipelines["fr"]
        with self._lock:
            doc = nlp(text)
        spans: list[Span] = []
        for ent in doc.ents:
            label = _LABELS.get(ent.label_)
            if label is None:
                continue
            value = ent.text.strip()
            if label is Label.PERSONNE and not _plausible_person(value):
                continue
            score = SCORE_PERSON if label is Label.PERSONNE else SCORE_OTHER
            start = ent.start_char + (len(ent.text) - len(ent.text.lstrip()))
            spans.append(Span(start, start + len(value), label, score, self.name))
        return spans


def _plausible_person(value: str) -> bool:
    if len(value) < 3 or any(c.isdigit() for c in value) or not value[0].isupper():
        return False
    if value.casefold() in _STOPWORDS:
        return False
    return not (value.isupper() and len(value) <= 5)  # sigles courts


def load(settings: Settings) -> tuple[SpacyDetector, dict[str, str]]:
    import spacy

    from ..model_store import MODELS, local_path

    pipelines = {
        "fr": spacy.load(local_path("spacy_fr"), exclude=_EXCLUDED_FR),
        "en": spacy.load(local_path("spacy_en"), exclude=_EXCLUDED_EN),
    }
    detail = {
        "fr": f"{MODELS['spacy_fr'].repo_id} ({MODELS['spacy_fr'].license})",
        "en": f"{MODELS['spacy_en'].repo_id} ({MODELS['spacy_en'].license})",
    }
    return SpacyDetector(pipelines), detail
