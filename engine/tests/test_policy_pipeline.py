# @spec docs/BACKLOG.md#RG-010 | docs/DAT.md#profils | docs/DAT.md#moteur
# @verifies docs/BACKLOG.md#RG-010 | docs/BACKLOG.md#RG-008 | docs/DAT.md#profils
"""Politique et pipeline : actions par contexte, liste blanche, fusion, jetons et code exclus, escalade."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from conftest import make_iban
from rgpd_guard.detectors.rules import RulesDetector
from rgpd_guard.detectors.secrets import SecretsDetector
from rgpd_guard.models import Action, CategoryScore, Context, DetectionContext, Span
from rgpd_guard.pipeline import Pipeline, Registry, resolve_overlaps
from rgpd_guard.policy import Policy, PolicyEngine, load_policy_file
from rgpd_guard.taxonomy import Category, Label
from rgpd_guard.textutil import mask_for_classifier


class FakeClassifier:
    """Classificateur simulé (contrat documenté : catégorie et probabilité calibrée)."""

    name = "laya"

    def __init__(self, scores: dict[Category, float]) -> None:
        self.scores = scores
        self.seen: list[str] = []

    def classify(self, text: str, ctx: DetectionContext) -> list[CategoryScore]:
        self.seen.append(text)
        return [CategoryScore(c, p, self.name) for c, p in self.scores.items()]


def make_pipeline(scores: dict[Category, float] | None = None) -> Pipeline:
    registry = Registry()
    registry.add_detector(RulesDetector())
    registry.add_detector(SecretsDetector())
    if scores is not None:
        registry.add_classifier(FakeClassifier(scores))
    return Pipeline(registry, PolicyEngine(load_policy_file()), 15000, 20000)


def test_default_policy_is_complete_and_valid() -> None:
    policy = load_policy_file()
    assert set(policy.labels) == set(Label) and set(policy.categories) == set(Category)


def test_policy_rejects_secret_bypass_and_bad_regex() -> None:
    data = load_policy_file().model_dump(mode="json")
    data["bypass_excluded"] = []
    with pytest.raises(ValidationError):
        Policy.model_validate(data)
    data = load_policy_file().model_dump(mode="json")
    data["allowlist"]["patterns"] = ["(non fermée"]
    with pytest.raises(ValidationError):
        Policy.model_validate(data)


def test_actions_depend_on_context() -> None:
    pipeline = make_pipeline()
    text = f"IBAN {make_iban(1)} SIRET 73282932000074"
    prompt = pipeline.analyze(text, "rapide", Context.PROMPT)
    output = pipeline.analyze(text, "rapide", Context.TOOL_OUTPUT)
    assert {f.span.label: f.action for f in prompt.findings}[Label.IBAN] is Action.BLOCK
    assert {f.span.label: f.action for f in output.findings}[Label.IBAN] is Action.PSEUDONYMIZE


def test_allowlist_example_domains() -> None:
    analysis = make_pipeline().analyze("contact: jean@example.com ou jean@orange.fr", "rapide")
    assert [f.value for f in analysis.findings] == ["jean@orange.fr"]


def test_tokens_are_never_redetected() -> None:
    analysis = make_pipeline().analyze("mail ⟦EMAIL_1⟧ et tel ⟦TELEPHONE_1⟧", "rapide")
    assert analysis.findings == []


def test_resolve_overlaps_prefers_validated() -> None:
    a = Span(0, 10, Label.PERSONNE, 0.99, "spacy")
    b = Span(2, 12, Label.EMAIL, 0.9, "rules", validated=True)
    assert resolve_overlaps([a, b]) == [b]


def test_sensitive_category_blocks_only_with_identifier() -> None:
    pipeline = make_pipeline({Category.SANTE: 0.92})
    with_id = pipeline.analyze("Patient joignable au 06 12 34 56 78, diabète", "equilibre")
    without = pipeline.analyze("Le diabète de type 2 touche des millions de personnes", "equilibre")
    assert [c.action for c in with_id.categories] == [Action.BLOCK]
    assert [c.action for c in without.categories] == [Action.WARN]
    assert with_id.is_blocking and not without.is_blocking


def test_category_below_threshold_ignored() -> None:
    analysis = make_pipeline({Category.SANTE: 0.3}).analyze("texte", "equilibre")
    assert analysis.categories == []


def test_missing_model_detectors_are_reported() -> None:
    registry = make_pipeline().registry
    assert registry.missing_for_name("max") == ["gliner", "laya", "spacy"]


def test_mask_for_classifier_replaces_identifiers_and_tokens() -> None:
    text = "Paul (p@courriel-fictif.fr) au CHU. Voir ⟦DATE_NAISSANCE_2⟧."
    masked = mask_for_classifier(text, [(0, 4, "[personne]"), (6, 26, "[email]"), (31, 34, None)])
    assert masked == "[personne] ([email]) au CHU. Voir [date naissance]."


def test_classifier_receives_masked_text_and_spans_stay_raw() -> None:
    pipeline = make_pipeline({Category.SANTE: 0.9})
    classifier = pipeline.registry.classifiers["laya"]
    assert isinstance(classifier, FakeClassifier)
    iban = make_iban()
    analysis = pipeline.analyze(f"Hospitalisé hier. Virement sur {iban} et contact ⟦EMAIL_1⟧.", "equilibre")
    assert classifier.seen == ["Hospitalisé hier. Virement sur [IBAN] et contact [email]."]
    assert any(f.span.label is Label.IBAN for f in analysis.findings)
    assert [c.action for c in analysis.categories] == [Action.BLOCK]
