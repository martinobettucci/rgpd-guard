# RGPD Guard

Plugin Claude Code qui vérifie, **en local et sur CPU uniquement**, que vous n'êtes pas en train d'envoyer des données personnelles (RGPD) ou des secrets à votre moteur d'IA.

Projet P2Enjoy SAS, construit selon le socle [P2Enjoy/software-factory-base](https://github.com/P2Enjoy/software-factory-base).

## État du projet

Version 0.1.0, non publiée. L'état de chaque unité (non commencée, en cours, terminée et vérifiée) est tenu à un seul endroit : [docs/BACKLOG.md](docs/BACKLOG.md).

Contenu de la version : socle d'usine logicielle (méthode, hooks Git, CI) ; plugin Claude Code, marketplace et client de hook fail-closed ; moteur local (règles et validateurs, secrets, pseudonymisation réversible, politique, audit, authentification) ; détecteurs CPU hors ligne spaCy, Laya et GLiNER ; corpus seedé et banc d'évaluation ; tableau de bord React + Vite (Journal, Bac à sable, Politiques, Moteurs) ; conteneurisation dev, staging, prod et lanceurs.

## Principe

1. Un hook Claude Code transmet chaque prompt et chaque sortie d'outil au moteur local.
2. Le moteur combine des règles validées par somme de contrôle (IBAN, NIR, SIRET, cartes), un détecteur de secrets et, selon le profil, spaCy, le classificateur calibré Laya et GLiNER.
3. Un prompt sensible est bloqué et une version pseudonymisée (`⟦EMAIL_1⟧`, `⟦IBAN_1⟧`...) est proposée ; les sorties d'outils sont pseudonymisées avant d'atteindre le modèle ; les vraies valeurs sont réinjectées localement quand Claude écrit un fichier.
4. Si le moteur ne répond pas, le plugin bloque par défaut (`fail_mode=closed`).

Architecture détaillée : [docs/DAT.md](docs/DAT.md). Décisions et investigations : [docs/JOURNAL.md](docs/JOURNAL.md).

## Stack

- Moteur : Python 3.12, uv, FastAPI, SQLite.
- Détection CPU : python-stdnum, phonenumbers, spaCy, Laya, GLiNER (torch CPU, modèles épinglés et lus hors ligne).
- Plugin : JSON, POSIX `sh`, `curl`.
- Dashboard : React, Vite, TypeScript, lucide-react.
- Conteneurs : Docker Compose (surcharges dev, staging, prod), nginx non root en production.

## Prérequis

- Git, Bash, `curl`.
- Docker avec Compose v2 pour la pile complète.
- [uv](https://docs.astral.sh/uv/) (installe Python 3.12 si besoin).
- Claude Code pour utiliser le plugin et pour les tests E2E.

## Installation pour contribuer

```bash
git clone https://github.com/martinobettucci/rgpd-guard.git
cd rgpd-guard
git config --local user.name "<nom du responsable>"
git config --local user.email "<adresse du responsable>"
scripts/git-hooks/install
cd engine && uv sync --group dev --extra nlp --extra laya --extra gliner
uv run python -m rgpd_guard.model_store ../.cache/models   # environ 1,9 Go, une seule fois
```

## Lancer la pile (Docker)

| Environnement | Démarrer | Moteur | Tableau de bord | Données |
|---|---|---|---|---|
| dev | `./runDev.sh up` | http://127.0.0.1:8742 | http://127.0.0.1:8743 | jeton fixe `dev-token-rgpd-guard`, journal seedé automatiquement |
| staging | `./runStaging.sh up` | http://127.0.0.1:18742 | http://127.0.0.1:18743 | jeton généré, seed de démonstration par `./runStaging.sh seed` |
| prod | `./runProd.sh up` | http://127.0.0.1:8742 | http://127.0.0.1:8743 | jeton généré, aucune donnée seedée |

Sous-commandes communes : `up`, `down`, `logs`, `status`, `seed` (dev et staging), `test` (dev), `e2e` (dev), `bench` (dev), `token`, `reset` (confirmation exigée hors dev).

- Le premier `./runDev.sh up` télécharge les modèles CPU épinglés dans `.cache/models/` (environ 1,9 Go, une fois), puis démarre la pile, attend le chargement des modèles (environ une minute) et rejoue le corpus seedé à travers les vrais hooks.
- Chaque `up` écrit l'adresse et le jeton de l'environnement démarré dans `~/.config/rgpd-guard/engine.env` (mode 600) : le plugin vise automatiquement le dernier environnement démarré.
- En staging et en prod, `config/environments/<env>.env` est créé à partir du modèle `.example` commenté, et le jeton comme la clé HMAC sont générés s'ils sont vides.
- Le dossier personnel est monté en lecture seule dans le moteur (mentions `@` et `/rgpd-guard:scan`) ; le restreindre avec `RGPD_GUARD_WORKSPACE_ROOT=/chemin ./runProd.sh up`.
- Derrière un proxy TLS d'entreprise : `BUILD_CA_BUNDLE=/chemin/ca.pem BUILD_HTTPS_PROXY=http://proxy:port BUILD_NETWORK=host ./runDev.sh up`.
- Arrêt : `./runDev.sh down` ; réinitialisation des données : `./runDev.sh reset`.

## Lancer le moteur sans Docker (développement du moteur)

```bash
cd engine
RGPD_GUARD_TOKEN=dev-token-local RGPD_GUARD_HMAC_KEY=dev-hmac-local \
RGPD_GUARD_DATA_DIR=../.cache/data RGPD_GUARD_WORKSPACE_ROOT="$HOME" RGPD_GUARD_HOST=127.0.0.1 \
HF_HOME=../.cache/models HF_HUB_OFFLINE=1 \
uv run python -m rgpd_guard
```

Le moteur écoute sur http://127.0.0.1:8742 (`GET /health` pour vérifier) ; le chargement des modèles prend environ une minute. Sans modèles, ajouter `RGPD_GUARD_ENABLED_DETECTORS=rules,secrets RGPD_GUARD_PROFILE=rapide`.

## Seeds et banc d'évaluation

```bash
cd engine
uv run python ../seeds/generate.py                       # corpus déterministe dans seeds/out/
HF_HOME=../.cache/models HF_HUB_OFFLINE=1 uv run python -m rgpd_guard.bench ../seeds/out/corpus.jsonl --out ../.cache/data/bench/latest.json
```

Résultats de référence (banc du 2 octobre 2026, 70 textes, 4 vCPU) : profil `rapide` F1 0,68 en moins d'une milliseconde (aucun nom de personne), `equilibre` F1 0,98 en 394 ms (p50, p95 484 ms), `max` F1 0,985 en 496 ms (p50, p95 624 ms) ; catégories sensibles : rappel 60 % (9 sur 15), précision 69 %. Détail dans [le journal](docs/JOURNAL.md).

## Installer le plugin dans Claude Code

```text
/plugin marketplace add martinobettucci/rgpd-guard
/plugin install rgpd-guard@p2enjoy
```

Options du plugin (demandées à l'activation, modifiables dans `/config`) :

| Option | Rôle | Défaut |
|---|---|---|
| `engine_url` | adresse du moteur | fichier `~/.config/rgpd-guard/engine.env`, sinon `http://127.0.0.1:8742` |
| `engine_token` | jeton du moteur (stockage sécurisé) | fichier `~/.config/rgpd-guard/engine.env` |
| `fail_mode` | `closed` : blocage si le moteur ne répond pas ; `open` : avertissement | `closed` |
| `profile` | `defaut`, `rapide`, `equilibre`, `max` | `defaut` (profil du moteur) |

Commandes du plugin : `/rgpd-guard:status`, `/rgpd-guard:scan <fichier>`, `/rgpd-guard:dashboard`. Préfixe `#rgpd-ok` : envoi ponctuel malgré une détection (jamais pour un secret), journalisé.

## Tests

| Usage | Commande |
|---|---|
| Moteur, contrats du client de hook et tableau de bord, dans les conteneurs (les autres suites de ce tableau s'exécutent séparément) | `./runDev.sh test` |
| Parcours E2E du tableau de bord (Playwright, captures JPEG et vidéos webm) | `./runDev.sh e2e` |
| Tests unitaires et API du moteur | `cd engine && uv run pytest` |
| Tableau de bord : typage, tests, textes, contrastes | `cd dashboard && npm run typecheck && npm test && npm run check:i18n && npm run check:contrast` |
| Tests d'inférence sur les modèles réels | `cd engine && HF_HOME=../.cache/models HF_HUB_OFFLINE=1 uv run pytest -m models` |
| Lint, format, typage | `cd engine && uv run ruff check . && uv run ruff format --check . && uv run mypy` |
| Contrats du client de hook | `cd engine && uv run pytest ../e2e/claude/test_hook_client.py` |
| E2E Claude Code réel (faux serveur API, aucune clé requise) | `cd engine && uv run pytest ../e2e/claude/test_claude_e2e.py` |
| Hooks du socle | `tests/git-hooks/test-hooks` |
| Lanceurs `run*.sh` en simulation (faux Docker, aucun conteneur) | `tests/launchers/test-launchers` |
| Contrôle des références de traçabilité | `tests/project/test-check-spec-refs` |
| Contrôles rapides du projet | `scripts/project-pre-commit --all` |
| Validation du plugin et de la marketplace | `claude plugin validate plugins/rgpd-guard && claude plugin validate .` |

## Variables d'environnement

Les fichiers `config/environments/*.env` (dev versionné, modèles `.example` commentés pour staging et prod) portent les valeurs passées aux conteneurs.

### Moteur

| Variable | Rôle | Obligatoire | Exemple |
|---|---|---|---|
| `RGPD_GUARD_TOKEN` | jeton des hooks et du dashboard | oui | chaîne aléatoire de 32 caractères |
| `RGPD_GUARD_HMAC_KEY` | clé des empreintes du journal | oui | chaîne aléatoire |
| `RGPD_GUARD_ENV` | `dev`, `staging`, `prod` | non | `dev` |
| `RGPD_GUARD_PROFILE` | profil par défaut | non | `equilibre` |
| `RGPD_GUARD_ENABLED_DETECTORS` | composants chargés | non | `rules,secrets,spacy,laya,gliner` |
| `RGPD_GUARD_DATA_DIR` | dossier de la base SQLite et du dernier banc | non | `/data` |
| `RGPD_GUARD_POLICY_FILE` | politique par défaut (YAML) ; à défaut, celle du paquet | non | `/etc/rgpd-guard/politique.yaml` |
| `RGPD_GUARD_WORKSPACE_ROOT` | dossier lisible pour les mentions `@` et `/rgpd-guard:scan` | non | `/home/moi` |
| `RGPD_GUARD_AUDIT_RETENTION_DAYS` | rétention du journal | non | `30` |
| `RGPD_GUARD_AUDIT_PREVIEW` | conserver un aperçu masqué | non | `true` |
| `RGPD_GUARD_VAULT_TTL_SECONDS` | durée de vie des pseudonymes | non | `43200` |
| `RGPD_GUARD_BYPASS_PREFIX` | préfixe de contournement ponctuel d'un prompt | non | `#rgpd-ok` |
| `RGPD_GUARD_DEADLINE_MS` | échéance d'une analyse ; au-delà, seuls les détecteurs sans modèle s'appliquent | non | `15000` |
| `RGPD_GUARD_MAX_NER_CHARS` | taille maximale d'un texte soumis aux modèles (au-delà : règles seules, résultat partiel) | non | `20000` |
| `RGPD_GUARD_MAX_TEXT_CHARS` | taille au-delà de laquelle une sortie d'outil est remplacée par un avis | non | `2000000` |
| `RGPD_GUARD_ALLOWED_HOSTS` | en-têtes Host acceptés | non | `127.0.0.1,localhost,engine` |
| `RGPD_GUARD_CORS_ORIGINS` | origines autorisées à modifier | non | `http://127.0.0.1:8743` |
| `RGPD_GUARD_TORCH_THREADS` | fils CPU de torch (Laya, GLiNER) | non | `4` |
| `RGPD_GUARD_HOST`, `RGPD_GUARD_PORT` | écoute | non | `0.0.0.0`, `8742` |
| `RGPD_GUARD_RELOAD` | rechargement à chaud du code (dev) | non | `false` |
| `RGPD_GUARD_LOG_LEVEL` | niveau des journaux | non | `INFO` |
| `HF_HOME`, `HF_HUB_OFFLINE` | cache local des modèles Laya et GLiNER, interdiction de tout téléchargement | oui avec modèles | `/models`, `1` |

### Client de hook (plugin)

Les options du plugin priment ; à défaut, le client lit ces variables dans l'environnement de Claude Code, puis le fichier écrit par le dernier lanceur.

| Variable | Rôle | Défaut |
|---|---|---|
| `RGPD_GUARD_URL` | adresse du moteur | `http://127.0.0.1:8742` |
| `RGPD_GUARD_TOKEN` | jeton du moteur | valeur du fichier du lanceur |
| `RGPD_GUARD_FAIL_MODE` | `closed` ou `open` | `closed` |
| `RGPD_GUARD_PROFILE` | profil demandé au moteur, même sens que côté moteur | profil du moteur |
| `RGPD_GUARD_CONFIG` | fichier écrit par les lanceurs | `~/.config/rgpd-guard/engine.env` |

### Lanceurs et construction

| Variable | Rôle | Défaut |
|---|---|---|
| `ENGINE_PORT`, `DASHBOARD_PORT` | ports publiés sur 127.0.0.1 | dev et prod `8742`, `8743` ; staging `18742`, `18743` |
| `RGPD_GUARD_WORKSPACE_ROOT` | dossier personnel monté en lecture seule dans le moteur | `$HOME` |
| `BUILD_CA_BUNDLE` | paquet CA d'un proxy TLS, transmis en secret de construction | `config/ca/empty.pem` (vide) |
| `BUILD_HTTPS_PROXY` | proxy HTTPS utilisé pendant la construction | aucun |
| `BUILD_NETWORK` | réseau de construction (`host` derrière un proxy local) | `default` |

### Tableau de bord (serveur Vite de développement)

| Variable | Rôle | Défaut |
|---|---|---|
| `RGPD_GUARD_ENGINE_URL` | moteur vers lequel `/api` est relayé | `http://127.0.0.1:8742` |

## Structure du dépôt

```text
.
├── .claude-plugin/marketplace.json   # marketplace "p2enjoy"
├── plugins/rgpd-guard/               # plugin Claude Code (manifeste, hooks, client sh, commandes)
├── engine/                           # moteur Python (détecteurs, modèles CPU, politique, coffre, audit, API, banc)
│   ├── rgpd_guard/
│   └── tests/                        # tests unitaires et API, fixtures de payloads réels
├── seeds/                            # générateur déterministe du corpus étiqueté
├── dashboard/                        # tableau de bord React + Vite (nginx en production)
├── e2e/claude/                       # faux serveur API, contrats du client, E2E Claude Code
├── e2e/playwright/                   # parcours canonique du tableau de bord, captures de référence
├── config/environments/              # dev.env (versionné), modèles staging et prod commentés
├── config/ca/empty.pem               # paquet CA vide par défaut des constructions (proxy TLS facultatif)
├── config/socle-files.txt            # empreintes amont des fichiers du socle, contrôlées avant chaque commit
├── .cache/                           # ignoré : modèles téléchargés (models/), données locales (data/)
├── docker-compose*.yml, run*.sh      # pile conteneurisée et lanceurs (scripts/stack.sh)
├── docs/                             # DAT, BACKLOG, JOURNAL, SCHEMA, AUTOMATION, design system
├── CLAUDE.md, AGENTS.md, .claude/, .codex/      # méthode du socle P2Enjoy (MPL-2.0)
├── .githooks/, scripts/git-hooks/, tests/git-hooks/   # garde-fous Git du socle
├── tests/launchers/, tests/project/  # harnais des lanceurs et du contrôle de traçabilité
└── scripts/project-pre-commit        # contrôles rapides propres au projet
```

## Limites connues

- En profil `rapide`, les noms de personnes en texte libre ne sont pas détectés.
- Catégories sensibles (Laya, zero-shot) : rappel mesuré de 60 %, aucune reconnaissance des données concernant un mineur ; à considérer comme une couche complémentaire (bêta).
- Non couverts par conception (voir [DAT §14](docs/DAT.md#compromis)) : images collées, contenus injectés par Claude Code sans hook (CLAUDE.md, mémoire, état git), télémétrie de Claude Code (`DISABLE_TELEMETRY=1` recommandé), contenu analysé côté serveur par WebFetch.
- Une commande en échec dont la sortie contient une donnée arrête la boucle (filet `PostToolBatch`) ; le résultat reste dans la conversation locale et doit être retiré avec `/rewind`.
- Un Edit dont l'`old_string` contient un jeton est refusé par Claude Code avant tout hook ; Claude est guidé pour choisir un texte voisin ou réécrire le fichier.

## Licence

Code du projet sous licence MIT ([LICENSE](LICENSE)). Les fichiers de méthode importés du socle P2Enjoy (`CLAUDE.md`, `AGENTS.md`, `.claude/agents/factory-*`, `.codex/`, `.githooks/`, `scripts/git-hooks/`, `tests/git-hooks/`, `docs/CloudWorker.md`, `docs/.routine`, `docs/DESIGN_SYSTEM.md`, `.gitignore`) restent sous Mozilla Public License 2.0 ([LICENSES/MPL-2.0.txt](LICENSES/MPL-2.0.txt)).

https://p2enjoy.studio
