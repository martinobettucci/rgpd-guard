# @spec docs/BACKLOG.md#RG-010 | docs/BACKLOG.md#RG-007 | docs/BACKLOG.md#RG-008 | docs/BACKLOG.md#RG-009 | docs/DAT.md#composants
"""Assemblage du moteur : configuration, détecteurs, politique, coffre, stockage et adaptateurs."""

from __future__ import annotations

import importlib
import logging
import threading
import time
from typing import Any

from .audit import Store
from .config import Settings
from .detectors.rules import RulesDetector
from .detectors.secrets import SecretsDetector
from .hooks import HookAdapter
from .pipeline import Pipeline, Registry
from .policy import Policy, PolicyEngine, load_policy_file
from .vault import Vault

log = logging.getLogger(__name__)

# Composants à modèle : module, fabrique, type. Chargés seulement s'ils sont activés et installés.
MODEL_COMPONENTS: dict[str, tuple[str, str, str]] = {
    "spacy": ("rgpd_guard.detectors.spacy_ner", "load", "detecteur"),
    "gliner": ("rgpd_guard.detectors.gliner_pii", "load", "detecteur"),
    "laya": ("rgpd_guard.classifiers.laya", "load", "classificateur"),
}


def build_registry(settings: Settings) -> Registry:
    registry = Registry()
    registry.add_detector(RulesDetector())
    registry.add_detector(SecretsDetector())
    enabled = settings.detectors_list
    for name, (module_name, factory, kind) in MODEL_COMPONENTS.items():
        if name not in enabled:
            continue
        started = time.perf_counter()
        try:
            module = importlib.import_module(module_name)
            component, detail = getattr(module, factory)(settings)
        except Exception as exc:  # modèle absent ou dépendance non installée : état visible, pas de plantage
            log.warning("composant %s indisponible : %s", name, exc)
            registry.mark_failed(name, kind, f"{type(exc).__name__}: {exc}"[:300])
            continue
        load_ms = round((time.perf_counter() - started) * 1000, 1)
        if kind == "detecteur":
            registry.add_detector(component, load_ms, detail)
        else:
            registry.add_classifier(component, load_ms, detail)
    return registry


class Engine:
    """État partagé du processus (un seul worker : le coffre vit en mémoire)."""

    def __init__(self, settings: Settings, registry: Registry | None = None) -> None:
        self.settings = settings
        self.store = Store(
            settings.data_dir / "rgpd-guard.db",
            settings.hmac_key,
            settings.audit_retention_days,
            settings.audit_preview,
        )
        self.default_policy = load_policy_file(settings.policy_file)
        stored = self.store.latest_policy()
        policy = Policy.model_validate(stored) if stored else self.default_policy
        self.policy_source = "custom" if stored else "default"
        self.registry = registry or build_registry(settings)
        self.vault = Vault(settings.vault_ttl_seconds)
        self.pipeline = Pipeline(self.registry, PolicyEngine(policy), settings.deadline_ms, settings.max_ner_chars)
        self.hooks = HookAdapter(
            self.pipeline,
            self.vault,
            self.store,
            settings.profile,
            settings.bypass_prefix,
            settings.workspace_root,
            settings.max_text_chars,
        )
        self._lock = threading.Lock()

    @property
    def policy(self) -> Policy:
        return self.pipeline.policy.policy

    def set_policy(self, policy: Policy, source: str = "custom") -> None:
        with self._lock:
            self.store.save_policy(policy.model_dump(mode="json"), policy.version)
            self.pipeline.policy = PolicyEngine(policy)
            self.policy_source = source

    def components(self) -> list[dict[str, Any]]:
        return [
            {
                "name": s.name,
                "kind": s.kind,
                "ready": s.ready,
                "load_ms": s.load_ms,
                "error": s.error,
                "detail": s.detail,
            }
            for s in self.registry.status.values()
        ]
