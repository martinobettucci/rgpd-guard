# @spec docs/BACKLOG.md#RG-010 | docs/DAT.md#profils
"""Politique de décision : modèle validé, chargement et résolution des actions."""

from __future__ import annotations

import fnmatch
import re
from enum import StrEnum
from pathlib import Path, PurePath
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .models import Action, Analysis, CategoryFinding, CategoryScore, Context, Finding, Span
from .taxonomy import DIRECT_IDENTIFIERS, Category, Label

DEFAULT_POLICY_PATH = Path(__file__).resolve().parent / "policies" / "default.yaml"


class PromptAction(StrEnum):
    BLOCK = "block"
    WARN = "warn"
    ALLOW = "allow"


class OutputAction(StrEnum):
    PSEUDONYMIZE = "pseudonymize"
    ALLOW = "allow"


class CategoryAction(StrEnum):
    BLOCK_IF_IDENTIFIER = "block_if_identifier"
    WARN = "warn"
    ALLOW = "allow"


class LabelRule(BaseModel):
    model_config = ConfigDict(extra="forbid")
    prompt: PromptAction
    tool_output: OutputAction
    min_score: float = Field(ge=0.0, le=1.0)


class CategoryRule(BaseModel):
    model_config = ConfigDict(extra="forbid")
    threshold: float = Field(ge=0.0, le=1.0)
    action: CategoryAction


class Allowlist(BaseModel):
    model_config = ConfigDict(extra="forbid")
    values: list[str] = Field(default_factory=list, max_length=1000)
    patterns: list[str] = Field(default_factory=list, max_length=200)

    @field_validator("patterns")
    @classmethod
    def _compile(cls, patterns: list[str]) -> list[str]:
        for pattern in patterns:
            try:
                re.compile(pattern)
            except re.error as exc:
                raise ValueError(f"expression régulière invalide « {pattern} » : {exc}") from exc
        return patterns


class Policy(BaseModel):
    model_config = ConfigDict(extra="forbid")
    version: int = Field(ge=1)
    labels: dict[Label, LabelRule]
    categories: dict[Category, CategoryRule]
    allowlist: Allowlist = Field(default_factory=Allowlist)
    secret_files: list[str] = Field(default_factory=list, max_length=200)
    secret_files_exceptions: list[str] = Field(default_factory=list, max_length=200)
    bypass_excluded: list[Label] = Field(default_factory=lambda: [Label.SECRET])

    @model_validator(mode="after")
    def _complete(self) -> Policy:
        missing_labels = [label.value for label in Label if label not in self.labels]
        missing_categories = [c.value for c in Category if c not in self.categories]
        if missing_labels or missing_categories:
            raise ValueError(f"politique incomplète : types {missing_labels}, catégories {missing_categories}")
        if Label.SECRET not in self.bypass_excluded:
            raise ValueError("SECRET doit rester exclu du contournement")
        return self


def load_policy_file(path: Path | None = None) -> Policy:
    with open(path or DEFAULT_POLICY_PATH, encoding="utf-8") as handle:
        data: Any = yaml.safe_load(handle)
    return Policy.model_validate(data)


class PolicyEngine:
    """Applique une politique à des spans et des catégories."""

    def __init__(self, policy: Policy) -> None:
        self.policy = policy
        self._allow_values = {v.casefold() for v in policy.allowlist.values}
        self._allow_patterns = [re.compile(p) for p in policy.allowlist.patterns]

    def is_allowlisted(self, value: str) -> bool:
        if value.casefold() in self._allow_values:
            return True
        return any(p.search(value) for p in self._allow_patterns)

    def span_action(self, span: Span, context: Context) -> Action:
        rule = self.policy.labels[span.label]
        if span.score < rule.min_score:
            return Action.ALLOW
        if context is Context.PROMPT:
            return Action(rule.prompt.value)
        return Action.PSEUDONYMIZE if rule.tool_output is OutputAction.PSEUDONYMIZE else Action.ALLOW

    def apply(self, analysis: Analysis, spans: list[Span], categories: list[CategoryScore], context: Context) -> None:
        """Remplit `analysis.findings` et `analysis.categories` selon la politique."""
        findings: list[Finding] = []
        for span in spans:
            value = analysis.text[span.start : span.end]
            if self.is_allowlisted(value):
                continue
            action = self.span_action(span, context)
            if action is not Action.ALLOW:
                findings.append(Finding(span=span, value=value, action=action))
        analysis.findings = findings
        has_identifier = any(f.span.label in DIRECT_IDENTIFIERS for f in findings)
        resolved: list[CategoryFinding] = []
        for score in categories:
            rule = self.policy.categories[score.category]
            if score.probability < rule.threshold or rule.action is CategoryAction.ALLOW:
                continue
            if rule.action is CategoryAction.BLOCK_IF_IDENTIFIER and has_identifier and context is Context.PROMPT:
                resolved.append(CategoryFinding(score=score, action=Action.BLOCK))
            else:
                resolved.append(CategoryFinding(score=score, action=Action.WARN))
        analysis.categories = resolved

    def is_secret_file(self, path: str) -> bool:
        name = PurePath(path.replace("\\", "/")).name
        if any(fnmatch.fnmatch(name, pattern) for pattern in self.policy.secret_files_exceptions):
            return False
        return any(fnmatch.fnmatch(name, pattern) for pattern in self.policy.secret_files)
