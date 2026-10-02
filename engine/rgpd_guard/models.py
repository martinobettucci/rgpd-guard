# @spec docs/BACKLOG.md#RG-002 | docs/BACKLOG.md#RG-010 | docs/DAT.md#moteur
"""Structures de données échangées entre détecteurs, pipeline, politique et adaptateurs."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from .taxonomy import Category, Label


class Context(StrEnum):
    """Origine du texte analysé : elle détermine l'action applicable."""

    PROMPT = "prompt"
    TOOL_OUTPUT = "tool_output"


class Action(StrEnum):
    BLOCK = "block"
    WARN = "warn"
    ALLOW = "allow"
    PSEUDONYMIZE = "pseudonymize"


@dataclass(frozen=True)
class Span:
    """Valeur sensible localisée : `text[start:end]`."""

    start: int
    end: int
    label: Label
    score: float
    detector: str
    validated: bool = False

    @property
    def length(self) -> int:
        return self.end - self.start


@dataclass(frozen=True)
class CategoryScore:
    category: Category
    probability: float
    classifier: str


@dataclass
class DetectionContext:
    """Paramètres d'une analyse."""

    context: Context = Context.PROMPT
    code_mode: bool = False
    language: str | None = None


@dataclass
class Finding:
    """Span retenu après fusion, liste blanche et seuils, avec l'action décidée par la politique."""

    span: Span
    value: str
    action: Action


@dataclass
class CategoryFinding:
    score: CategoryScore
    action: Action


@dataclass
class Analysis:
    """Résultat complet d'une analyse de texte."""

    text: str
    profile: str
    findings: list[Finding] = field(default_factory=list)
    categories: list[CategoryFinding] = field(default_factory=list)
    timings_ms: dict[str, float] = field(default_factory=dict)
    partial: bool = False

    @property
    def blocking(self) -> list[Finding]:
        return [f for f in self.findings if f.action is Action.BLOCK]

    @property
    def warnings(self) -> list[Finding]:
        return [f for f in self.findings if f.action is Action.WARN]

    @property
    def to_pseudonymize(self) -> list[Finding]:
        return [f for f in self.findings if f.action in (Action.BLOCK, Action.WARN, Action.PSEUDONYMIZE)]

    @property
    def blocking_categories(self) -> list[CategoryFinding]:
        return [c for c in self.categories if c.action is Action.BLOCK]

    @property
    def warning_categories(self) -> list[CategoryFinding]:
        return [c for c in self.categories if c.action is Action.WARN]

    @property
    def is_blocking(self) -> bool:
        return bool(self.blocking or self.blocking_categories)
