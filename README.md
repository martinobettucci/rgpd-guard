# RGPD Guard

Plugin Claude Code qui vérifie, **en local et sur CPU uniquement**, que vous n'êtes pas en train d'envoyer des données personnelles (RGPD) ou des secrets à votre moteur d'IA.

Projet P2Enjoy SAS, construit selon le socle [P2Enjoy/software-factory-base](https://github.com/P2Enjoy/software-factory-base).

## État du projet

Version 0.1.0 en construction. L'état réel de chaque unité est tenu dans [docs/BACKLOG.md](docs/BACKLOG.md).

| Brique | État |
|---|---|
| Socle d'usine logicielle (méthode, hooks Git, CI) | en place |
| Plugin Claude Code et marketplace | à venir |
| Moteur de détection (règles, secrets, spaCy, Laya, GLiNER) | à venir |
| Dashboard React + Vite | à venir |
| Conteneurisation dev, staging, prod | à venir |

## Principe

1. Un hook Claude Code transmet chaque prompt et chaque sortie d'outil à un moteur local (conteneur Docker sur 127.0.0.1).
2. Le moteur combine des règles validées par somme de contrôle (IBAN, NIR, SIRET, cartes), un détecteur de secrets, spaCy, le classificateur calibré Laya et GLiNER, selon le profil choisi.
3. Un prompt sensible est bloqué et une version pseudonymisée (`⟦EMAIL_1⟧`, `⟦PERSONNE_1⟧`...) est proposée ; les sorties d'outils sont pseudonymisées avant d'atteindre le modèle, et les vraies valeurs sont réinjectées localement quand Claude écrit un fichier.

Architecture détaillée : [docs/DAT.md](docs/DAT.md). Décisions et investigations : [docs/JOURNAL.md](docs/JOURNAL.md).

## Stack

- Moteur : Python 3.12, uv, FastAPI, SQLite.
- Détection CPU : python-stdnum, phonenumbers, spaCy, Laya, GLiNER.
- Dashboard : React, Vite, TypeScript.
- Plugin : JSON, POSIX `sh`, `curl`.
- Conteneurs : Docker Compose (dev, staging, prod).

## Prérequis

- Git, Bash.
- Docker avec Compose v2 (à partir de l'unité RG-018).
- Claude Code pour utiliser le plugin.

## Installation pour contribuer

```bash
git clone https://github.com/martinobettucci/rgpd-guard.git
cd rgpd-guard
git config --local user.name "<nom du responsable>"
git config --local user.email "<adresse du responsable>"
scripts/git-hooks/install
```

## Commandes disponibles

| Usage | Commande |
|---|---|
| Activer les hooks Git du socle | `scripts/git-hooks/install` |
| Tester les hooks du socle | `tests/git-hooks/test-hooks` |
| Contrôles rapides du projet sur tout le dépôt | `scripts/project-pre-commit --all` |

Les commandes de démarrage, de seed, de test et de build de la pile sont documentées ici dès qu'elles existent.

## Variables d'environnement

Aucune pour le moment. Les fichiers d'environnement vivront dans `config/environments/` (voir [CLAUDE_PROJECT.md](CLAUDE_PROJECT.md)).

## Structure du dépôt

```text
.
├── CLAUDE.md, AGENTS.md          # méthode globale du socle P2Enjoy (MPL-2.0)
├── CLAUDE_PROJECT.md             # règles locales du projet
├── .claude/agents/, .codex/      # sous-agents bornés du socle
├── .githooks/, scripts/git-hooks/, tests/git-hooks/   # garde-fous Git du socle
├── scripts/project-pre-commit    # contrôles rapides propres au projet
├── docs/
│   ├── DAT.md                    # dossier d'architecture technique
│   ├── BACKLOG.md                # unités de travail et état réel
│   ├── JOURNAL.md                # décisions et investigations
│   ├── AUTOMATION.md             # contrat des garde-fous exécutables
│   ├── DESIGN_SYSTEM.md          # design system global P2Enjoy
│   └── CloudWorker.md, .routine  # contrat du worker planifié
└── LICENSES/MPL-2.0.txt
```

## Limites connues

Le produit n'est pas encore utilisable : seul le socle et la spécification sont en place.

## Licence

Code du projet sous licence MIT ([LICENSE](LICENSE)). Les fichiers de méthode importés du socle P2Enjoy (`CLAUDE.md`, `AGENTS.md`, `.claude/agents/factory-*`, `.codex/`, `.githooks/`, `scripts/git-hooks/`, `tests/git-hooks/`, `docs/CloudWorker.md`, `docs/.routine`, `docs/DESIGN_SYSTEM.md`, `.gitignore`) restent sous Mozilla Public License 2.0 ([LICENSES/MPL-2.0.txt](LICENSES/MPL-2.0.txt)).

https://p2enjoy.studio
