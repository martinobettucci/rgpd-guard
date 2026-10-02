# @spec docs/BACKLOG.md#RG-010 | docs/BACKLOG.md#RG-012 | docs/BACKLOG.md#RG-018 | docs/DAT.md#securite
"""Configuration centralisée du moteur, lue dans les variables d'environnement `RGPD_GUARD_*`."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="RGPD_GUARD_", extra="ignore")

    env: str = Field(default="dev", description="dev, staging ou prod")
    token: str = Field(default="", description="Jeton d'accès des hooks et du dashboard (obligatoire)")
    hmac_key: str = Field(default="", description="Clé locale des empreintes HMAC du journal (obligatoire)")
    profile: str = Field(default="equilibre", description="Profil par défaut : rapide, equilibre ou max")
    data_dir: Path = Field(default=Path("/data"), description="Dossier de la base SQLite")
    policy_file: Path | None = Field(default=None, description="Politique par défaut ; à défaut, celle du paquet")
    models_dir: Path = Field(default=Path("/models"), description="Modèles CPU téléchargés à la construction")
    enabled_detectors: str = Field(
        default="rules,secrets,spacy,laya,gliner",
        description="Détecteurs chargés au démarrage, séparés par des virgules",
    )
    audit_retention_days: int = Field(default=30, ge=1)
    audit_preview: bool = Field(default=True, description="Conserver un aperçu masqué des valeurs")
    vault_ttl_seconds: int = Field(default=12 * 3600, ge=60)
    bypass_prefix: str = Field(default="#rgpd-ok")
    allowed_hosts: str = Field(default="127.0.0.1,localhost,engine")
    cors_origins: str = Field(default="")
    workspace_root: Path | None = Field(default=None, description="Racine montée en lecture seule pour les mentions @")
    deadline_ms: int = Field(default=15000, ge=100, description="Échéance d'analyse, au-delà profil rapide seul")
    max_ner_chars: int = Field(default=20000, ge=1000, description="Taille maximale d'un texte soumis aux modèles")
    max_text_chars: int = Field(default=2_000_000, ge=10000, description="Au-delà, le texte est remplacé par un avis")
    torch_threads: int = Field(default=4, ge=1, le=64, description="Fils CPU utilisés par torch (Laya, GLiNER)")
    test_endpoints: bool = Field(default=False, description="Endpoints de test (dev uniquement)")

    @property
    def allowed_hosts_list(self) -> list[str]:
        return [h.strip() for h in self.allowed_hosts.split(",") if h.strip()]

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def detectors_list(self) -> list[str]:
        return [d.strip() for d in self.enabled_detectors.split(",") if d.strip()]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
