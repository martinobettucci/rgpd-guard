# @spec docs/BACKLOG.md#RG-007 | docs/BACKLOG.md#RG-008 | docs/BACKLOG.md#RG-009 | docs/DAT.md#dependances
"""Modèles CPU épinglés : téléchargés une fois dans un cache Hugging Face local, puis lus hors ligne.

Usage (construction de l'image ou poste de développement) :
    python -m rgpd_guard.model_store <dossier_cache>
À l'exécution, `HF_HOME` pointe vers ce dossier et `HF_HUB_OFFLINE=1` interdit tout appel réseau.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class PinnedModel:
    repo_id: str
    revision: str
    license: str
    allow_patterns: tuple[str, ...] | None = None
    ignore_patterns: tuple[str, ...] | None = None


MODELS: dict[str, PinnedModel] = {
    "spacy_fr": PinnedModel(
        "spacy/fr_core_news_md", "45238ee04ed39d2488b1da882a9c597c6279b633", "LGPL-LR", ignore_patterns=("*.whl",)
    ),
    "spacy_en": PinnedModel(
        "spacy/en_core_web_md", "22f17ee20cda126e498ea2fb92dc504bea0d111c", "MIT", ignore_patterns=("*.whl",)
    ),
    "laya": PinnedModel(
        "convaiinnovations/laya-multilingual", "e4e9ddf21a7b1903b7acffd8814ad4307bf63a67", "Apache-2.0"
    ),
    "gliner": PinnedModel("urchade/gliner_multi_pii-v1", "1fcf13e85f4eef5394e1fcd406cf2ca9ea82351d", "Apache-2.0"),
    # Tokenizer et configuration de l'encodeur de GLiNER (sans les poids, inutiles).
    "gliner_base": PinnedModel(
        "microsoft/mdeberta-v3-base",
        "a0484667b22365f84929a935b5e50a51f71f159d",
        "MIT",
        allow_patterns=("config.json", "spm.model", "tokenizer_config.json"),
    ),
}

GROUPS: dict[str, tuple[str, ...]] = {
    "spacy": ("spacy_fr", "spacy_en"),
    "laya": ("laya",),
    "gliner": ("gliner", "gliner_base"),
}


def local_path(key: str) -> str:
    """Chemin du modèle dans le cache, sans accès réseau (lève une erreur s'il est absent)."""
    from huggingface_hub import snapshot_download

    model = MODELS[key]
    return str(
        snapshot_download(
            model.repo_id,
            revision=model.revision,
            local_files_only=True,
            allow_patterns=list(model.allow_patterns) if model.allow_patterns else None,
            ignore_patterns=list(model.ignore_patterns) if model.ignore_patterns else None,
        )
    )


def download(cache_dir: Path, groups: list[str]) -> None:
    from huggingface_hub import snapshot_download

    hub_dir = cache_dir / "hub"
    for group in groups:
        for key in GROUPS[group]:
            model = MODELS[key]
            print(f"téléchargement de {model.repo_id}@{model.revision[:10]} ({model.license})", flush=True)
            snapshot_download(
                model.repo_id,
                revision=model.revision,
                allow_patterns=list(model.allow_patterns) if model.allow_patterns else None,
                ignore_patterns=list(model.ignore_patterns) if model.ignore_patterns else None,
                cache_dir=str(hub_dir),
            )
            # Les bibliothèques qui résolvent un modèle par identifiant (tokenizer de GLiNER) lisent la
            # référence `main` : on la fait pointer vers la révision épinglée.
            refs = hub_dir / f"models--{model.repo_id.replace('/', '--')}" / "refs"
            refs.mkdir(parents=True, exist_ok=True)
            (refs / "main").write_text(model.revision, encoding="utf-8")


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit("usage : python -m rgpd_guard.model_store <dossier_cache> [spacy,laya,gliner]")
    groups = sys.argv[2].split(",") if len(sys.argv) > 2 else list(GROUPS)
    download(Path(sys.argv[1]), groups)


if __name__ == "__main__":
    main()
