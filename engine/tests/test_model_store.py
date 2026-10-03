# @spec docs/BACKLOG.md#RG-008 | docs/BACKLOG.md#RG-009 | docs/DAT.md#dependances
# @verifies docs/BACKLOG.md#RG-008 | docs/BACKLOG.md#RG-009 | docs/DAT.md#dependances
"""Magasin de modèles : cache lisible par l'utilisateur du moteur, distinct de celui du téléchargement."""

from __future__ import annotations

import stat
from pathlib import Path

from rgpd_guard.model_store import make_readable


def test_cache_made_readable_by_every_user(tmp_path: Path) -> None:
    trees = tmp_path / "hub" / "models--org--modele" / "trees"
    trees.mkdir(parents=True)
    tree = trees / "revision.json"
    tree.write_text("{}", encoding="utf-8")
    tree.chmod(0o600)  # mode d'écriture de huggingface_hub pour ce cache
    trees.chmod(0o700)
    link = tmp_path / "hub" / "lien"
    link.symlink_to(tree)

    make_readable(tmp_path)

    assert stat.S_IMODE(tree.stat().st_mode) == 0o644
    assert stat.S_IMODE(trees.stat().st_mode) == 0o755
    assert link.is_symlink()
