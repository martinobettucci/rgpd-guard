# Registre d'incohérences

Défauts constatés hors de l'unité en cours, à résoudre par la boucle dédiée (CLAUDE.md §5) dans l'ordre ci-dessous. Chaque entrée quitte le registre avec son issue : corrigée, tranchée sans changement (motif au [journal](JOURNAL.md)) ou convertie en unité du [backlog](BACKLOG.md).

Origine : audit en lecture seule de la v0.1.0 avant la campagne de clôture, constats revérifiés à la main.

## IR-08 Chiffres du banc antérieurs au masquage avant Laya

- Constat : README (latences et rappel des catégories), DAT (§ modèles), BACKLOG RG-022 et JOURNAL citent un banc mesuré avant le commit `422558f`, qui a changé le texte soumis aux classificateurs. Aucun banc postérieur n'est consigné.
- Concerne : RG-017, README, DAT, JOURNAL.

## IR-09 Variables d'environnement non documentées ou inutilisées

- Constat :
  - lues mais absentes du README : moteur `RGPD_GUARD_POLICY_FILE`, `_DEADLINE_MS`, `_MAX_NER_CHARS`, `_MAX_TEXT_CHARS`, `_BYPASS_PREFIX` (`config.py`), `_RELOAD`, `_LOG_LEVEL` (`__main__.py`) ; client `RGPD_GUARD_URL`, `_CONFIG`, `_FAIL_MODE`, `_PROFILE` (`plugins/rgpd-guard/scripts/common.sh`) ; tableau de bord `RGPD_GUARD_ENGINE_URL` (`vite.config.ts`) ; lanceurs `ENGINE_PORT`, `DASHBOARD_PORT`, `BUILD_CA_BUNDLE` (`scripts/stack.sh`) ;
  - déclarées mais jamais lues : `models_dir` et `test_endpoints` (`config.py`), alors que `engine/Dockerfile` et `e2e/claude/harness.py` posent `RGPD_GUARD_MODELS_DIR`.
- Concerne : RG-010, RG-018, README, fichiers `.env.example`.

## IR-10 Routes de session absentes du DAT, critère « `/health` seul public » inexact

- Constat : le tableau du [DAT §10](DAT.md#api) omet `GET /v1/auth/session` et `POST /v1/policies/reset` (`api.py:223`, `api.py:271`) ; le critère de RG-012 affirme que `/health` est la seule route publique, alors que l'ouverture, la lecture et la fermeture de session le sont par nature.
- Concerne : RG-012, RG-015, DAT.

## IR-11 Délais emboîtés : règle énoncée pour tous les hooks

- Constat : le [DAT §3](DAT.md#flux-hooks) affirme que chaque délai contient le suivant, jusqu'à l'échéance du moteur (15 s). Or `curl --max-time` vaut 10 s pour PreToolUse et 5 s pour SessionStart et SubagentStart (`hooks/hooks.json`).
- Mesure : ces trois gestionnaires (`hooks.py:92-96`, `hooks.py:168`) ne lancent aucune détection ; l'échéance du moteur ne s'applique qu'aux hooks qui analysent un texte (UserPromptSubmit 25 s, PostToolUse 55 s, PostToolUseFailure 25 s, PostToolBatch 55 s).
- Concerne : DAT.

## IR-12 SCHEMA.md décalé de la migration

- Constat : `audit_events.event` cite une valeur `analyze` qu'aucun code n'écrit (le bac à sable ne journalise pas) ; les colonnes `id` de `audit_entities` et `policies` (`migrations/001_init.sql:23,36`) manquent.
- Concerne : RG-011, [SCHEMA](SCHEMA.md).

## IR-13 Commande `/rgpd-guard:dashboard` et aide de connexion divergentes

- Constat : `plugins/rgpd-guard/commands/dashboard.md` renvoie à `./runProd.sh token` seul, l'aide de la page d'accueil (`dashboard/src/i18n/fr.ts:28`) à `./runDev.sh token` puis aux autres lanceurs.
- Concerne : RG-001, RG-013.

## IR-14 Références `@spec` sans section

- Constat : `dashboard/src/pages/Sandbox.tsx:1`, `dashboard/src/i18n/index.ts:1`, `dashboard/index.html:2` et `dashboard/scripts/check-i18n.mjs:1` citent `docs/DESIGN_SYSTEM.md` sans chapitre, contrairement à CLAUDE.md §5 ; `scripts/check-spec-refs` ne contrôle que les références ancrées et laisse passer.
- Concerne : RG-000, RG-013, RG-014.

## IR-15 `THIRD_PARTY_NOTICES.md` incomplet

- Constat : les dépendances npm livrées dans l'image du tableau de bord (React, React Router, Lucide) et l'image de base nginx n'y figurent pas.
- Concerne : RG-013, RG-018.

## IR-16 Dérives de documentation

- Constat :
  - README « État du projet » : « implémenté, vérifié en E2E » alors que le BACKLOG garde toutes les unités à `[~]` ;
  - README : `./runDev.sh test` présenté comme « toute la batterie », alors qu'il n'exécute ni l'E2E Claude Code, ni les harnais des lanceurs et des hooks ;
  - arborescence du README sans `tests/launchers/` ni `config/` ;
  - BACKLOG RG-001 : chemin `scripts/guard-hook.sh` au lieu de `plugins/rgpd-guard/scripts/guard-hook.sh` ;
  - JOURNAL (décisions du cadrage) : environnements exécutables côte à côte, alors que dev et prod partagent les ports 8742 et 8743.
- Concerne : README, BACKLOG, JOURNAL.

## IR-17 Version 0.1.0 absente du CHANGELOG et de la marketplace

- Constat : les manifestes portent tous 0.1.0, le CHANGELOG n'a pas d'entrée 0.1.0 et l'entrée du plugin dans `.claude-plugin/marketplace.json` n'a pas de version.
- Concerne : RG-001, CHANGELOG.
