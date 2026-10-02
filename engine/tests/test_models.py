# @spec docs/BACKLOG.md#RG-007 | docs/BACKLOG.md#RG-008 | docs/BACKLOG.md#RG-009 | docs/DAT.md#moteur
# @verifies docs/BACKLOG.md#RG-007 | docs/BACKLOG.md#RG-008 | docs/BACKLOG.md#RG-009 | docs/DAT.md#moteur
"""Détecteurs à modèles CPU : logique pure toujours testée, inférence réelle si les modèles sont présents.

Pour l'inférence : HF_HOME=../models-cache HF_HUB_OFFLINE=1 uv run pytest -m models
"""

from __future__ import annotations

from functools import cache
from typing import Any

import pytest

from rgpd_guard.config import Settings
from rgpd_guard.detectors.gliner_pii import windows
from rgpd_guard.detectors.spacy_ner import _plausible_person
from rgpd_guard.models import DetectionContext
from rgpd_guard.taxonomy import Category, Label


def test_windows_cover_text_with_overlap() -> None:
    text = " ".join(f"mot{i}" for i in range(600))
    parts = windows(text, size=250, overlap=40)
    assert parts[0][0] == 0 and parts[-1][1] == len(text)
    assert all(parts[i + 1][0] < parts[i][1] for i in range(len(parts) - 1))
    assert windows("court texte") == [(0, len("court texte"))]


@pytest.mark.parametrize(
    ("value", "expected"),
    [("Camille Martin", True), ("Bonjour", False), ("NASA", False), ("jean", False), ("R2D2", False)],
)
def test_person_plausibility(value: str, expected: bool) -> None:
    assert _plausible_person(value) is expected


@cache
def _load(name: str) -> Any:
    settings = Settings(token="t", hmac_key="k")
    if name == "spacy":
        from rgpd_guard.detectors.spacy_ner import load
    elif name == "gliner":
        from rgpd_guard.detectors.gliner_pii import load
    else:
        from rgpd_guard.classifiers.laya import load
    try:
        component, _ = load(settings)
    except Exception as exc:  # modèles absents : test ignoré, jamais faussement vert
        pytest.skip(f"modèle {name} indisponible : {exc}")
    return component


@pytest.mark.models
def test_spacy_finds_people_fr_en() -> None:
    detector = _load("spacy")
    fr = detector.detect("Je travaille avec Camille Martin à Lyon.", DetectionContext(language="fr"))
    en = detector.detect("I met John Smith in Manchester.", DetectionContext(language="en"))
    assert any(s.label is Label.PERSONNE for s in fr) and any(s.label is Label.PERSONNE for s in en)


@pytest.mark.models
def test_gliner_finds_birth_date_and_address() -> None:
    detector = _load("gliner")
    text = "Né le 3 mars 1984, Paul habite 12 rue des Lilas 75011 Paris."
    labels = {s.label for s in detector.detect(text, DetectionContext())}
    assert {Label.DATE_NAISSANCE, Label.ADRESSE} <= labels


@pytest.mark.models
def test_laya_returns_calibrated_probabilities() -> None:
    classifier = _load("laya")
    scores = {s.category: s.probability for s in classifier.classify("Explique le tri fusion.", DetectionContext())}
    assert set(scores) == set(Category) and all(0.0 <= p <= 1.0 for p in scores.values())
    health = classifier.classify("Anaïs a été hospitalisée pour une dépression sévère.", DetectionContext())
    assert {s.category: s.probability for s in health}[Category.SANTE] > 0.4
