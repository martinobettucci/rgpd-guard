# RGPD Guard

Plugin Claude Code qui vérifie, **en local et sur CPU uniquement**, que vous n'êtes pas en train d'envoyer des données personnelles (RGPD) ou des secrets à votre moteur d'IA.

Projet P2Enjoy SAS, construit selon le socle [P2Enjoy/software-factory-base](https://github.com/P2Enjoy/software-factory-base).

## État du projet

Version 0.1.0 en construction. L'état réel de chaque unité est tenu dans [docs/BACKLOG.md](docs/BACKLOG.md).

| Brique | État |
|---|---|
| Socle d'usine logicielle (méthode, hooks Git, CI) | en place |
| Plugin Claude Code, marketplace, client de hook fail-closed | implémenté, vérifié en E2E avec Claude Code réel |
| Moteur : règles et validateurs, secrets, pseudonymisation réversible, politique, audit, authentification | implémenté, vérifié en E2E |
| Moteur : spaCy, Laya, GLiNER (CPU, hors ligne) | implémenté, mesuré par le banc d'évaluation |
| Corpus seedé et banc d'évaluation | en place |
| Dashboard React + Vite | à venir |
| Conteneurisation dev, staging, prod | à venir |

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
- Dashboard : React, Vite, TypeScript (à venir).
- Conteneurs : Docker Compose (à venir).

## Prérequis

- Git, Bash, `curl`.
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
uv run python -m rgpd_guard.model_store ../models-cache   # environ 1,9 Go, une seule fois
```

## Lancer le moteur en développement (natif, en attendant Docker)

```bash
cd engine
RGPD_GUARD_TOKEN=dev-token-local RGPD_GUARD_HMAC_KEY=dev-hmac-local \
RGPD_GUARD_DATA_DIR=../data RGPD_GUARD_WORKSPACE_ROOT="$HOME" RGPD_GUARD_HOST=127.0.0.1 \
HF_HOME=../models-cache HF_HUB_OFFLINE=1 \
uv run python -m rgpd_guard
```

Le moteur écoute sur http://127.0.0.1:8742 (`GET /health` pour vérifier) ; le chargement des modèles prend environ une minute. Sans modèles, ajouter `RGPD_GUARD_ENABLED_DETECTORS=rules,secrets RGPD_GUARD_PROFILE=rapide`.

## Seeds et banc d'évaluation

```bash
cd engine
uv run python ../seeds/generate.py                       # corpus déterministe dans seeds/out/
HF_HOME=../models-cache HF_HUB_OFFLINE=1 uv run python -m rgpd_guard.bench ../seeds/out/corpus.jsonl --out ../data/bench/latest.json
```

Résultats de référence (4 vCPU) : profil `rapide` F1 0,68 en moins d'une milliseconde (aucun nom de personne), `equilibre` F1 0,98 en 0,75 s (p50), `max` F1 0,99 en 1,0 s (p50). Détail dans [le journal](docs/JOURNAL.md).

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
| Tests unitaires et API du moteur | `cd engine && uv run pytest` |
| Tests d'inférence sur les modèles réels | `cd engine && HF_HOME=../models-cache HF_HUB_OFFLINE=1 uv run pytest -m models` |
| Lint, format, typage | `cd engine && uv run ruff check . && uv run ruff format --check . && uv run mypy` |
| Contrats du client de hook | `cd engine && uv run pytest ../e2e/claude/test_hook_client.py` |
| E2E Claude Code réel (faux serveur API, aucune clé requise) | `cd engine && uv run pytest ../e2e/claude/test_claude_e2e.py` |
| Hooks du socle | `tests/git-hooks/test-hooks` |
| Contrôles rapides du projet | `scripts/project-pre-commit --all` |
| Validation du plugin et de la marketplace | `claude plugin validate plugins/rgpd-guard && claude plugin validate .` |

## Variables d'environnement du moteur

| Variable | Rôle | Obligatoire | Exemple |
|---|---|---|---|
| `RGPD_GUARD_TOKEN` | jeton des hooks et du dashboard | oui | chaîne aléatoire de 32 caractères |
| `RGPD_GUARD_HMAC_KEY` | clé des empreintes du journal | oui | chaîne aléatoire |
| `RGPD_GUARD_ENV` | `dev`, `staging`, `prod` | non | `dev` |
| `RGPD_GUARD_PROFILE` | profil par défaut | non | `equilibre` |
| `RGPD_GUARD_ENABLED_DETECTORS` | composants chargés | non | `rules,secrets,spacy,laya,gliner` |
| `RGPD_GUARD_DATA_DIR` | dossier de la base SQLite | non | `/data` |
| `RGPD_GUARD_WORKSPACE_ROOT` | dossier lisible pour les mentions `@` et `/rgpd-guard:scan` | non | `/home/moi` |
| `RGPD_GUARD_AUDIT_RETENTION_DAYS` | rétention du journal | non | `30` |
| `RGPD_GUARD_AUDIT_PREVIEW` | conserver un aperçu masqué | non | `true` |
| `RGPD_GUARD_VAULT_TTL_SECONDS` | durée de vie des pseudonymes | non | `43200` |
| `RGPD_GUARD_ALLOWED_HOSTS` | en-têtes Host acceptés | non | `127.0.0.1,localhost,engine` |
| `RGPD_GUARD_CORS_ORIGINS` | origines autorisées à modifier | non | `http://127.0.0.1:8743` |
| `RGPD_GUARD_HOST`, `RGPD_GUARD_PORT` | écoute | non | `0.0.0.0`, `8742` |
| `RGPD_GUARD_TORCH_THREADS` | fils CPU de torch (Laya, GLiNER) | non | `4` |
| `HF_HOME`, `HF_HUB_OFFLINE` | cache local des modèles, interdiction de tout téléchargement | oui avec modèles | `/models`, `1` |

## Structure du dépôt

```text
.
├── .claude-plugin/marketplace.json   # marketplace "p2enjoy"
├── plugins/rgpd-guard/               # plugin Claude Code (manifeste, hooks, client sh, commandes)
├── engine/                           # moteur Python (détecteurs, modèles CPU, politique, coffre, audit, API, banc)
│   ├── rgpd_guard/
│   └── tests/                        # tests unitaires et API, fixtures de payloads réels
├── seeds/                            # générateur déterministe du corpus étiqueté
├── e2e/claude/                       # faux serveur API, contrats du client, E2E Claude Code
├── docs/                             # DAT, BACKLOG, JOURNAL, SCHEMA, AUTOMATION, design system
├── CLAUDE.md, AGENTS.md, .claude/, .codex/      # méthode du socle P2Enjoy (MPL-2.0)
├── .githooks/, scripts/git-hooks/, tests/git-hooks/   # garde-fous Git du socle
└── scripts/project-pre-commit        # contrôles rapides propres au projet
```

## Limites connues

- Dashboard et conteneurs pas encore livrés.
- En profil `rapide`, les noms de personnes en texte libre ne sont pas détectés.
- Catégories sensibles (Laya, zero-shot) : rappel mesuré de 60 %, aucune reconnaissance des données concernant un mineur ; à considérer comme une couche complémentaire (bêta).
- Non couverts par conception (voir [DAT §14](docs/DAT.md#compromis)) : images collées, contenus injectés par Claude Code sans hook (CLAUDE.md, mémoire, état git), télémétrie de Claude Code (`DISABLE_TELEMETRY=1` recommandé), contenu analysé côté serveur par WebFetch.
- Une commande en échec dont la sortie contient une donnée arrête la boucle (filet `PostToolBatch`) ; le résultat reste dans la conversation locale et doit être retiré avec `/rewind`.
- Un Edit dont l'`old_string` contient un jeton est refusé par Claude Code avant tout hook ; Claude est guidé pour choisir un texte voisin ou réécrire le fichier.

## Licence

Code du projet sous licence MIT ([LICENSE](LICENSE)). Les fichiers de méthode importés du socle P2Enjoy (`CLAUDE.md`, `AGENTS.md`, `.claude/agents/factory-*`, `.codex/`, `.githooks/`, `scripts/git-hooks/`, `tests/git-hooks/`, `docs/CloudWorker.md`, `docs/.routine`, `docs/DESIGN_SYSTEM.md`, `.gitignore`) restent sous Mozilla Public License 2.0 ([LICENSES/MPL-2.0.txt](LICENSES/MPL-2.0.txt)).

https://p2enjoy.studio
