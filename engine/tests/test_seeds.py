# @spec docs/BACKLOG.md#RG-017 | docs/DAT.md#donnees-dev
# @verifies docs/BACKLOG.md#RG-017 | docs/DAT.md#donnees-dev
"""Corpus seedé : déterministe, étiquettes cohérentes, identifiants à somme de contrôle valide."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

from stdnum import iban as std_iban
from stdnum.fr import nir as std_nir

GENERATOR = Path(__file__).resolve().parents[2] / "seeds" / "generate.py"


def load_generator() -> ModuleType:
    spec = importlib.util.spec_from_file_location("seeds_generate", GENERATOR)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules["seeds_generate"] = module
    spec.loader.exec_module(module)
    return module


def test_corpus_is_deterministic_and_well_formed() -> None:
    generator = load_generator()
    first, second = generator.generate(42), generator.generate(42)
    assert first == second and generator.generate(43) != first
    ids = [r["id"] for r in first]
    assert len(ids) == len(set(ids))
    for record in first:
        for span in record["spans"]:
            assert 0 <= span["start"] < span["end"] <= len(record["text"])


def test_identifiers_are_valid_and_both_kinds_present() -> None:
    records = load_generator().generate()
    kinds = {r["kind"] for r in records}
    assert kinds == {"positif", "negatif"}
    for record in records:
        for span in record["spans"]:
            value = record["text"][span["start"] : span["end"]]
            if span["label"] == "IBAN":
                assert std_iban.is_valid(value.replace(" ", ""))
            if span["label"] == "NIR":
                assert std_nir.is_valid(value.replace(" ", ""))
