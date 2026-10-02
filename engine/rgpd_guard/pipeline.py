# @spec docs/BACKLOG.md#RG-010 | docs/BACKLOG.md#RG-007 | docs/BACKLOG.md#RG-009 | docs/DAT.md#moteur | docs/DAT.md#profils
"""Pipeline d'analyse : profils, exécution des détecteurs, fusion des spans, politique."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field

from .detectors.base import Classifier, Detector
from .models import Analysis, CategoryScore, Context, DetectionContext, Span
from .policy import PolicyEngine
from .textutil import code_block_ranges, guess_language, overlaps, token_ranges

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class Profile:
    name: str
    detectors: tuple[str, ...]
    classifiers_prompt: tuple[str, ...] = ()
    classifiers_output: tuple[str, ...] = ()


PROFILES: dict[str, Profile] = {
    "rapide": Profile("rapide", ("rules", "secrets")),
    "equilibre": Profile("equilibre", ("rules", "secrets", "spacy"), classifiers_prompt=("laya",)),
    "max": Profile(
        "max",
        ("rules", "secrets", "spacy", "gliner"),
        classifiers_prompt=("laya",),
        classifiers_output=("laya",),
    ),
}


@dataclass
class ComponentStatus:
    name: str
    kind: str
    ready: bool
    load_ms: float = 0.0
    error: str | None = None
    detail: dict[str, str] = field(default_factory=dict)


class Registry:
    """Détecteurs et classificateurs chargés au démarrage, avec leur état."""

    def __init__(self) -> None:
        self.detectors: dict[str, Detector] = {}
        self.classifiers: dict[str, Classifier] = {}
        self.status: dict[str, ComponentStatus] = {}

    def add_detector(self, detector: Detector, load_ms: float = 0.0, detail: dict[str, str] | None = None) -> None:
        self.detectors[detector.name] = detector
        self.status[detector.name] = ComponentStatus(detector.name, "detecteur", True, load_ms, None, detail or {})

    def add_classifier(
        self, classifier: Classifier, load_ms: float = 0.0, detail: dict[str, str] | None = None
    ) -> None:
        self.classifiers[classifier.name] = classifier
        self.status[classifier.name] = ComponentStatus(
            classifier.name, "classificateur", True, load_ms, None, detail or {}
        )

    def mark_failed(self, name: str, kind: str, error: str) -> None:
        self.status[name] = ComponentStatus(name, kind, False, 0.0, error)

    def missing_for_name(self, profile_name: str) -> list[str]:
        return self.missing_for(PROFILES.get(profile_name, PROFILES["equilibre"]))

    def missing_for(self, profile: Profile) -> list[str]:
        wanted = list(profile.detectors) + list(profile.classifiers_prompt) + list(profile.classifiers_output)
        return sorted({n for n in wanted if n not in self.detectors and n not in self.classifiers})


def resolve_overlaps(spans: list[Span]) -> list[Span]:
    """Garde les spans prioritaires : validé, puis score, puis longueur ; sans recouvrement."""
    ordered = sorted(spans, key=lambda s: (not s.validated, -s.score, -s.length, s.start))
    kept: list[Span] = []
    for span in ordered:
        if all(span.end <= k.start or k.end <= span.start for k in kept):
            kept.append(span)
    return sorted(kept, key=lambda s: s.start)


class Pipeline:
    def __init__(self, registry: Registry, policy: PolicyEngine, deadline_ms: int, max_ner_chars: int) -> None:
        self.registry = registry
        self.policy = policy
        self.deadline_ms = deadline_ms
        self.max_ner_chars = max_ner_chars

    def analyze(
        self,
        text: str,
        profile_name: str,
        context: Context = Context.PROMPT,
        code_mode: bool = False,
    ) -> Analysis:
        profile = PROFILES.get(profile_name, PROFILES["equilibre"])
        analysis = Analysis(text=text, profile=profile.name)
        if not text.strip():
            return analysis
        started = time.perf_counter()
        ctx = DetectionContext(context=context, code_mode=code_mode, language=guess_language(text))
        excluded = token_ranges(text)
        code_ranges = code_block_ranges(text) if context is Context.PROMPT else []
        models_allowed = not code_mode and len(text) <= self.max_ner_chars

        spans: list[Span] = []
        for name in profile.detectors:
            detector = self.registry.detectors.get(name)
            if detector is None:
                continue
            if detector.uses_model:
                elapsed = (time.perf_counter() - started) * 1000
                if not models_allowed or elapsed > self.deadline_ms:
                    analysis.partial = analysis.partial or len(text) > self.max_ner_chars or elapsed > self.deadline_ms
                    continue
            t0 = time.perf_counter()
            try:
                found = detector.detect(text, ctx)
            except Exception:  # un détecteur défaillant ne doit pas faire tomber l'analyse
                log.exception("détecteur %s en erreur", name)
                analysis.partial = True
                continue
            analysis.timings_ms[name] = round((time.perf_counter() - t0) * 1000, 2)
            for span in found:
                if overlaps(span.start, span.end, excluded):
                    continue
                if detector.uses_model and overlaps(span.start, span.end, code_ranges):
                    continue
                spans.append(span)

        categories: list[CategoryScore] = []
        wanted = profile.classifiers_prompt if context is Context.PROMPT else profile.classifiers_output
        for name in wanted:
            classifier = self.registry.classifiers.get(name)
            if classifier is None or not models_allowed:
                continue
            t0 = time.perf_counter()
            try:
                categories += classifier.classify(text, ctx)
            except Exception:
                log.exception("classificateur %s en erreur", name)
                analysis.partial = True
                continue
            analysis.timings_ms[name] = round((time.perf_counter() - t0) * 1000, 2)

        self.policy.apply(analysis, resolve_overlaps(spans), categories, context)
        analysis.timings_ms["total"] = round((time.perf_counter() - started) * 1000, 2)
        return analysis
