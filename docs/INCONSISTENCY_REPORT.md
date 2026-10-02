# Registre d'incohérences

Défauts constatés hors de l'unité en cours, à résoudre par la boucle dédiée (CLAUDE.md §5) dans l'ordre ci-dessous. Chaque entrée quitte le registre avec son issue : corrigée, tranchée sans changement (motif au [journal](JOURNAL.md)) ou convertie en unité du [backlog](BACKLOG.md).

Origine : audit en lecture seule de la v0.1.0 avant la campagne de clôture, constats revérifiés à la main.

## IR-01 Un clone neuf ne peut pas construire les images

- Constat : `docker-compose.yml:44` et `scripts/stack.sh:23` prennent `config/build/ca-empty.pem` comme valeur par défaut de `BUILD_CA_BUNDLE`, mais ce fichier n'est pas suivi : la règle `[Bb]uild/` du `.gitignore` du socle l'ignore.
- Mesure : `git ls-files config/build` est vide ; `git check-ignore -v config/build/ca-empty.pem` renvoie `.gitignore:29:[Bb]uild/`. Le harnais `tests/launchers/test-launchers:57` crée le fichier lui-même, ce qui masque le défaut.
- Concerne : RG-018, [DAT §12](DAT.md#deploiement).

## IR-02 `.gitignore` du socle modifié

- Constat : une section « RGPD Guard (projet) » de 18 lignes a été ajoutée à la fin du `.gitignore` importé (commit `24edff6`). Le socle le présente comme une base générique globale et RG-000 exige un import sans modification.
- Mesure : comparaison des empreintes avec `P2Enjoy/software-factory-base@886ba5a` (HEAD amont) : 24 fichiers de méthode identiques, `.gitignore` différent.
- Concerne : RG-000, séparation global et local (CLAUDE.md §27).

## IR-03 `bench` échoue hors de l'environnement de développement

- Constat : `cmd_bench` (`scripts/stack.sh:169`) exécute `/seeds/generate.py` dans le conteneur du moteur ; staging et prod ne montent pas `/seeds` (`docker-compose.staging.yml`, `docker-compose.prod.yml`) et l'image prod n'a pas Faker (`engine/Dockerfile`, `--no-dev`). BACKLOG RG-018, DAT et CLAUDE_PROJECT annoncent pourtant les mêmes sous-commandes pour les trois lanceurs, alors que `seed` est refusé en prod et `test`, `e2e` réservés au dev.
- Concerne : RG-018, README, [DAT §12](DAT.md#deploiement), CLAUDE_PROJECT.

## IR-04 Le garde-fou de `./runDev.sh e2e` ne bloque jamais

- Constat : `compose ps --status running engine` (`scripts/stack.sh:164`) réussit même quand la pile est arrêtée ; le message « pile arrêtée » n'apparaît jamais et Playwright échoue plus loin sur une erreur réseau.
- Concerne : RG-018.

## IR-05 Le temps de chargement des composants n'est jamais affiché

- Constat : RG-016 exige l'état et le temps de chargement de chaque détecteur. `Engines.tsx:94-95` n'affiche `load_ms` que lorsque `detail` est vide, or spaCy, GLiNER et Laya renvoient toujours un détail ; `rules` et `secrets` sont enregistrés avec `load_ms=0` (`service.py:32-33`).
- Concerne : RG-016, page Moteurs.

## IR-06 Une latence inférieure à 0,5 ms s'affiche « 0 »

- Constat : `formatMs` (`dashboard/src/lib/format.ts:15`) arrondit la p50 du profil `rapide` (0,2 ms) à « 0 », ce qui affiche une durée nulle et contredit le README (« moins d'une milliseconde »).
- Concerne : RG-016, DESIGN_SYSTEM §14.6.

## IR-07 Modèles spaCy 3.7 chargés par spaCy 3.8

- Constat : avertissement W095 à chaque chargement (« trained with spaCy v3.7.0 and may not be 100% compatible with the current version (3.8.16) »).
- Mesure : `meta.json` de `spacy/fr_core_news_md` (3.7.0) et `spacy/en_core_web_md` (3.7.1) sur Hugging Face déclare `spacy_version >=3.7.0,<3.8.0` ; `engine/uv.lock` porte spacy 3.8.16, thinc 8.3.13, numpy 2.5.3. Les roues 3.8.0 sont publiées sur les releases GitHub d'Explosion (`compatibility.json` : spaCy 3.8 → 3.8.0).
- Concerne : RG-007, `engine/rgpd_guard/model_store.py`, `detectors/spacy_ner.py`.

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
