# Journal des décisions et investigations

## 2026-10-02 : cadrage de RGPD Guard

### Problème

Empêcher l'envoi de données personnelles et de secrets à un moteur d'IA depuis Claude Code, avec un classificateur local exécuté sur CPU. La demande cite spaCy et « Maya », puis « Laya ».

### Investigations

**Identification de « Maya » et « Laya ».**
- Maya Data Privacy publie l'AISafe Plugin (MIT) : détection locale de données personnelles dans les interfaces de chat web, modèle GLiNER2 en ONNX servi sur `localhost:8765`, mode d'anonymisation optionnel via leur cloud.
- `convaiinnovations/laya` et `laya-multilingual` (Apache-2.0, septembre 2026, paquet PyPI `laya`) : classificateur de décision non autoregressif. Il répond à des questions typées (`noul`, `choice`, `score`) avec des probabilités calibrées en une passe. Le modèle multilingue (mmBERT base, 322M) couvre le français et annonce 193 à 464 ms par requête sur CPU.
- Lecture retenue : « spaCy et Laya » = spaCy localise les identifiants, Laya qualifie le caractère sensible du texte.

**Candidats de détection vérifiés (licence, langues, taille).**

| Modèle ou outil | Licence | Verdict |
|---|---|---|
| spaCy `fr_core_news_md` | LGPL-LR | retenu (`equilibre`), téléchargé au build |
| spaCy `en_core_web_md` | MIT | retenu (`equilibre`) |
| `urchade/gliner_multi_pii-v1` | Apache-2.0, FR/EN/DE/ES/PT/IT | retenu (`max`) |
| `convaiinnovations/laya-multilingual` | Apache-2.0 | retenu (catégories sensibles) |
| `knowledgator/gliner-pii-*` | Apache-2.0, anglais seul | écarté (pas de français) |
| `fastino/gliner2-privacy-filter-PII-multi` | Apache-2.0, FR | reporté (RG-019), précision faible annoncée |
| `openai/privacy-filter`, `OpenMed/privacy-filter-multilingual` | Apache-2.0 | reporté (RG-019), plus de 1 Go |
| `iiiorg/piiranha-v1-detect-personal-information` | CC-BY-NC-ND-4.0 | écarté (licence) |
| `nvidia/gliner-PII` | licence NVIDIA | écarté (licence, taille) |
| trufflehog | AGPL-3.0 | écarté (licence), règles gitleaks (MIT) préférées |
| Presidio | MIT | non retenu : aucun recognizer français, la couche de règles maison couvre NIR, SIREN et SIRET avec python-stdnum |
| python-stdnum | LGPL-2.1+ | retenu (dépendance non modifiée) |
| phonenumbers | Apache-2.0 | retenu |

**Contrat Claude Code (documentation officielle et transcripts locaux).**
- `UserPromptSubmit` bloque mais ne réécrit pas ; au délai dépassé, le prompt part.
- `updatedToolOutput` (PostToolUse) remplace la sortie vue par Claude pour tous les outils, si la forme est respectée ; sinon la valeur est ignorée sans erreur.
- `PostToolBatch` voit le contenu sérialisé exact envoyé au modèle et peut arrêter la boucle.
- Hook `http` : un échec de connexion laisse passer. Hook `command` : un code de sortie autre que 0 ou 2 laisse passer.
- Formes relevées : Read `{type, file:{filePath, content, numLines, startLine, totalLines}}` ; Bash `{stdout, stderr, interrupted, isImage, ...}` ; Edit `{filePath, content, structuredPatch, originalFile, userModified}`.

### Décisions

1. **Moteur dans Docker, client de hook `sh` + `curl`.** Motif : préférence du responsable pour une application conteneurisée, et un client sans dépendance qui sait bloquer lui-même. Écarté : hook `http` (fail-open), client Python (interpréteur non garanti sous macOS et Windows).
2. **Fail-closed par défaut.** Motif : un garde-fou qui laisse passer en silence quand il est arrêté est pire que son absence. Option `fail_mode=open` documentée.
3. **Prompt bloqué avec proposition pseudonymisée** (choix du responsable). Contournement `#rgpd-ok` journalisé, jamais pour les secrets.
4. **Pseudonymisation réversible des sorties d'outils et réhydratation à l'écriture.** Motif : sans réhydratation, Claude écraserait des fichiers avec des jetons. Réhydratation interdite vers Bash, WebFetch, WebSearch et MCP (voie d'exfiltration) ; refus sur jeton inconnu.
5. **Filet `PostToolBatch` en profil `rapide`.** Motif : coût faible, couvre une réécriture rejetée pour forme non conforme et les sorties de commandes en échec.
6. **Authentification par jeton local et cookie de session.** Motif : un service sur 127.0.0.1 reste joignable par une page web malveillante (requêtes croisées, DNS rebinding) et par les autres comptes du poste ; sans jeton, la politique pourrait être désactivée ou le coffre interrogé.
7. **Fichiers d'environnement sous `config/environments/`.** Motif : le hook pre-commit du socle refuse tout fichier `.env.*` indexé et le `.gitignore` du socle ignore les dossiers `env/`. `dev.env` ne contient aucune valeur sensible ; `staging.env` et `prod.env` sont ignorés, leurs modèles `.example` sont commentés.
8. **Identité Git** `Martino Bettucci <martinobettucci@users.noreply.github.com>`, identique au commit initial. Motif : identité du responsable exigée par le socle, adresse noreply pour éviter un refus de push lié à la confidentialité de l'adresse. Aucun trailer de co-paternité (règle du socle, prioritaire sur le comportement par défaut de l'outillage).
9. **Ports 8742 et 8743**, staging 18742 et 18743. Motif : éviter 8765 (AISafe) et permettre la cohabitation des environnements.
10. **Tests E2E de Claude Code contre un faux serveur API.** Motif : déterministe, sans clé, et permet de prouver qu'une valeur canari n'apparaît dans aucune requête sortante.
11. **`docs/AUTOMATION.md` créé localement.** Constat : les scripts du socle (`@spec docs/AUTOMATION.md#...`) et son README le citent, mais le fichier est absent du dépôt amont au commit `886ba5a`. Il est rédigé ici à partir du comportement réel des scripts, sans y ajouter de règle ; écart à remonter au socle.
12. **Fichiers du socle sous MPL-2.0.** Les fichiers de méthode importés restent sous MPL-2.0 (texte dans `LICENSES/MPL-2.0.txt`), le code du projet sous MIT.

### Conséquences

- Le découpage en unités est persisté dans [BACKLOG.md](BACKLOG.md), l'architecture dans [DAT.md](DAT.md).
- Première étape technique : capture réelle des formes de hooks (M1) avant d'écrire les adaptateurs.

## 2026-10-02 : capture réelle du contrat des hooks (M1)

### Problème

Les adaptateurs du moteur dépendent de formes et de comportements que la documentation ne détaille pas toujours. Les écrire sans les observer reviendrait à coder sur des hypothèses.

### Méthode

Faux serveur de l'API Messages (`e2e/claude/mock_anthropic.py`) rejouant des scénarios d'appels d'outils et enregistrant chaque requête ; plugin de capture enregistrant chaque payload de hook et renvoyant des réponses préparées par outil ; Claude Code 2.1.287 en mode `-p`, dans un environnement isolé (`env -i`, `HOME` temporaire, clé factice). Données 100 % synthétiques, avec valeurs canari. Payloads nettoyés conservés dans `engine/tests/fixtures/hooks/`.

### Observations (mesurées)

| Cas | Résultat |
|---|---|
| Read + `updatedToolOutput` de même forme | le modèle ne reçoit que les jetons, aucune valeur canari dans les requêtes ; `PostToolBatch` voit la version remplacée |
| Bash réussi | `tool_response` = `{stdout, stderr, interrupted, isImage, noOutputExpected}` |
| Bash en échec (code 3) | `PostToolUseFailure` avec `error` = « Exit code 3 » suivi de la sortie complète ; `PostToolBatch` contient ce texte |
| `PostToolBatch` avec `decision: block` | aucune requête n'est envoyée après l'outil : la sortie en échec n'atteint pas le modèle |
| Edit avec un `old_string` contenant un jeton | refusé par la validation de l'outil (« String to replace not found ») **avant** le hook `PreToolUse` : impossible à réhydrater |
| Edit avec `old_string` sans jeton, `new_string` réhydraté par `updatedInput` | fichier écrit avec les vraies valeurs ; le modèle ne reçoit qu'un message de succès fixe |
| Write réhydraté par `updatedInput` | fichier écrit avec les vraies valeurs ; message de succès fixe |
| `updatedInput` **sans** `permissionDecision` | l'entrée modifiée est utilisée et les règles de permission normales sont évaluées sur elle (commande non autorisée refusée en mode `default`) |
| Mention `@data.txt` dans le prompt | contenu du fichier injecté directement dans la requête, **aucun hook d'outil** ; seul `UserPromptSubmit` voit le texte `@data.txt` |
| Sous-agent | hooks d'outils déclenchés avec le même `session_id` et un `agent_id` ; outil nommé `Agent` ; `SubagentStart` disponible |
| Prompt bloqué | aucune requête vers l'API ; résultat « UserPromptSubmit operation blocked by hook » suivi du motif |
| Commande slash avec arguments | `UserPromptExpansion` puis `UserPromptSubmit`, ce dernier reçoit le texte brut complet avec les arguments |
| Outils exposés | pas d'outils Grep ni Glob dans cette version (recherche via Bash) |

### Décisions

1. **Réhydratation par `updatedInput` seul, sans `permissionDecision`.** Motif : la permission normale s'applique à l'entrée réhydratée ; le plugin n'accorde ni ne retire jamais de permission. Remplace la règle `allow`/`ask` du cadrage.
2. **Consigne d'édition injectée à Claude** (SessionStart, SubagentStart) : pour modifier un passage, choisir un `old_string` sans jeton `⟦...⟧`, ou réécrire le fichier avec Write. En cas d'échec d'un Edit dont l'`old_string` contient un jeton, `PostToolUseFailure` rappelle cette consigne. Motif : la validation d'Edit précède les hooks.
3. **Mentions `@fichier` résolues par le moteur.** Le dossier racine de travail (`RGPD_GUARD_WORKSPACE_ROOT`, défaut : dossier personnel) est monté en lecture seule au même chemin dans le conteneur ; le moteur analyse les fichiers mentionnés et bloque le prompt s'ils contiennent une donnée bloquante. Une mention qui désigne un fichier existant hors de portée est bloquée avec la consigne de demander une lecture par l'outil Read. Écarté : blocage systématique de toute mention (coût d'usage élevé pour du code ordinaire).
4. **Pas de hook `UserPromptExpansion`.** Motif : `UserPromptSubmit` voit déjà le texte brut avec les arguments ; un seul chemin de contrôle. Limite : la sortie des commandes `!` exécutées dans le corps d'une commande slash n'est vue par aucun hook.
5. **Pas de pseudonymisation des sorties de Write, Edit, MultiEdit et NotebookEdit dans `PostToolUse`.** Motif : le modèle ne reçoit qu'un message de succès fixe ; `PostToolBatch` reste le juge final si une version future y ajoutait du contenu.
6. **Sorties de commandes en échec** : pas d'enveloppe de commande (elle modifierait l'évaluation des règles de permission) ; le filet `PostToolBatch` bloque avant l'envoi, avec la consigne `/rewind`. Amélioration possible inscrite au backlog (RG-021).
