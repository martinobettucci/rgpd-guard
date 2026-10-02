# @spec docs/BACKLOG.md#RG-002 | docs/DAT.md#moteur
"""Contrat commun des détecteurs (spans) et des classificateurs (catégories)."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from ..models import CategoryScore, DetectionContext, Span


@runtime_checkable
class Detector(Protocol):
    """Localise des valeurs sensibles. Doit être sûr en concurrence (lecture seule après chargement)."""

    name: str
    uses_model: bool

    def detect(self, text: str, ctx: DetectionContext) -> list[Span]: ...


@runtime_checkable
class Classifier(Protocol):
    """Estime la probabilité de catégories sensibles sur l'ensemble d'un texte."""

    name: str

    def classify(self, text: str, ctx: DetectionContext) -> list[CategoryScore]: ...
