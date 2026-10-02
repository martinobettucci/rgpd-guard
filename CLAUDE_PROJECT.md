# CLAUDE_PROJECT.md : règles locales de RGPD Guard

Complément local de `CLAUDE.md` (référence globale du socle P2Enjoy, jamais modifiée ici). Ce fichier porte uniquement ce qui n'a de sens que pour ce dépôt.

## Produit

Plugin Claude Code qui bloque ou pseudonymise localement, sur CPU, les données personnelles et les secrets avant leur envoi au modèle. Architecture : [docs/DAT.md](docs/DAT.md). Découpage : [docs/BACKLOG.md](docs/BACKLOG.md).

## Stack effective

- Moteur : Python 3.12, uv, FastAPI, uvicorn, SQLite (`engine/`).
- Détection : python-stdnum, phonenumbers, spaCy, Laya, GLiNER, exécutés sur CPU uniquement.
- Dashboard : React, Vite, TypeScript, Lucide (`dashboard/`).
- Plugin : JSON, POSIX `sh` et `curl` (`plugins/rgpd-guard/`).
- Conteneurs : Docker Compose, surcharges `dev`, `staging`, `prod`.

## Conventions du dépôt

- Langue : documentation, interface, messages de commit, commentaires et motifs affichés en français. Identifiants de code en anglais.
- **Aucun tiret long (U+2014) ni tiret moyen (U+2013)** dans les fichiers du projet, textes comme code. Le tiret n'introduit jamais une précision : utiliser parenthèses, virgules, conjonctions ou deux-points. Contrôle automatique dans `scripts/project-pre-commit`. Les fichiers importés du socle sont exclus de ce contrôle.
- Traçabilité : `@spec docs/BACKLOG.md#RG-xxx | docs/DAT.md#ancre` en tête de chaque fichier de code, `@verifies` en plus pour les tests. Les ancres du DAT sont les identifiants explicites `<a id="...">`.
- Jetons de pseudonymisation : `⟦TYPE_N⟧` (U+27E6, U+27E7). Ne jamais changer ce format sans mettre à jour le moteur, le contexte injecté à Claude et le manuel.
- Données de test et de démonstration **100 % synthétiques**. Aucun secret d'apparence réelle écrit en dur : les fixtures de secrets sont assemblées à l'exécution à partir de fragments (le hook pre-commit et la protection de push de GitHub les refuseraient, à juste titre).
- Fichiers d'environnement dans `config/environments/` : `dev.env` versionné et sans valeur sensible ; `staging.env` et `prod.env` ignorés par git, construits à partir des modèles `.example` commentés. Jamais de `.env` à la racine (refusé par le hook du socle).
- Ports publiés uniquement sur 127.0.0.1 : moteur 8742, dashboard 8743 ; staging 18742, 18743. Le port 8765 est réservé de fait par d'autres outils locaux de protection.

## Commandes

| Usage | Commande |
|---|---|
| Activer les hooks Git | `scripts/git-hooks/install` |
| Tester les hooks du socle | `tests/git-hooks/test-hooks` |
| Tester les lanceurs (simulation, sans Docker) | `tests/launchers/test-launchers` |
| Contrôles rapides du projet | `scripts/project-pre-commit` (`--all` pour tout le dépôt) |
| Références de traçabilité | `scripts/check-spec-refs` |
| Pile de développement | `./runDev.sh up`, `down`, `logs`, `status`, `seed`, `test`, `e2e`, `bench`, `token`, `reset` |
| Staging, production | `./runStaging.sh …`, `./runProd.sh …` (mêmes sous-commandes) |
| E2E Claude Code (faux serveur API) | `cd engine && uv run pytest ../e2e/claude` |

## Environnement d'exécution des agents

- Session cloud : le démon Docker n'est pas lancé ; le démarrer avec `dockerd --host=unix:///var/run/docker.sock > /tmp/dockerd.log 2>&1 &` puis attendre `docker info`.
- Proxy TLS interposé : les constructions d'images reçoivent le paquet CA par la variable `BUILD_CA_BUNDLE` (chemin d'un fichier PEM, facultative) et utilisent le réseau de l'hôte pendant la construction lorsque `BUILD_NETWORK=host`.
- E2E Claude Code : toujours dans un environnement isolé (`HOME` temporaire, `ANTHROPIC_BASE_URL` pointant vers le faux serveur API de `e2e/`, clé factice), jamais avec les variables de la session courante.
