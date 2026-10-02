# @spec docs/BACKLOG.md#RG-018 | docs/DAT.md#deploiement
# @verifies docs/BACKLOG.md#RG-018 | docs/DAT.md#deploiement
"""Configuration : chaque variable lue par le moteur est documentée, aucun réglage déclaré n'est inutilisé."""

from __future__ import annotations

import inspect
import re
from pathlib import Path

import pytest

from rgpd_guard.config import Settings

ENGINE_ROOT = Path(__file__).resolve().parents[1]
README = ENGINE_ROOT.parent / "README.md"
# Variables lues directement par le point d'entrée (uvicorn et journalisation), hors de Settings.
ENTRYPOINT_VARIABLES = {"RGPD_GUARD_HOST", "RGPD_GUARD_PORT", "RGPD_GUARD_RELOAD", "RGPD_GUARD_LOG_LEVEL"}


def engine_variables() -> set[str]:
    return {f"RGPD_GUARD_{name.upper()}" for name in Settings.model_fields} | ENTRYPOINT_VARIABLES


def test_entrypoint_variables_are_the_ones_read() -> None:
    source = (ENGINE_ROOT / "rgpd_guard" / "__main__.py").read_text(encoding="utf-8")
    assert set(re.findall(r'"(RGPD_GUARD_[A-Z_]+)"', source)) == ENTRYPOINT_VARIABLES


def test_every_engine_variable_is_documented() -> None:
    if not README.is_file():
        pytest.skip("README.md absent (moteur testé hors du dépôt complet)")
    documented = set(re.findall(r"`(RGPD_GUARD_[A-Z_]+)`", README.read_text(encoding="utf-8")))
    assert engine_variables() - documented == set()


def readers(field: str) -> set[str]:
    """Le réglage lui-même et les propriétés de Settings qui le lisent (`allowed_hosts_list`...)."""
    names = {field}
    for attribute, value in vars(Settings).items():
        if isinstance(value, property) and value.fget and f"self.{field}" in inspect.getsource(value.fget):
            names.add(attribute)
    return names


def test_every_setting_is_read_by_the_engine() -> None:
    sources = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (ENGINE_ROOT / "rgpd_guard").rglob("*.py")
        if path.name != "config.py"
    )
    unused = {
        field
        for field in Settings.model_fields
        if not any(re.search(rf"\.{name}\b", sources) for name in readers(field))
    }
    assert unused == set()
