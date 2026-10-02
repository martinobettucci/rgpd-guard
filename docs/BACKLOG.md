# Backlog RGPD Guard

Statuts : `[ ]` non commencé, `[~]` en cours ou insuffisamment vérifié, `[x]` terminé et intégralement vérifié.

Chaque unité possède une ancre stable (`#RG-xxx`) citée par les commentaires `@spec` et `@verifies` du code.
Chaque unité exige au minimum un test unitaire spécifique et un test E2E spécifique (CLAUDE.md §15).
La spécification technique détaillée vit dans [le DAT](DAT.md) ; ce fichier porte le découpage, les critères d'acceptation et l'état réel.

## Version 0.1.0

<a id="RG-000"></a>
### [~] RG-000 Socle d'usine logicielle P2Enjoy

Objectif : construire et maintenir le dépôt selon `P2Enjoy/software-factory-base`.

Critères d'acceptation :
- fichiers de méthode du socle importés sans modification (CLAUDE.md, AGENTS.md, agents Claude Code et Codex, hooks Git, scripts, harnais de test, CloudWorker, design system global, `.gitignore`) ;
- identité Git locale du responsable posée, hooks activés en mode standard ;
- documents projet initialisés : README, CHANGELOG, CLAUDE_PROJECT, DAT, BACKLOG, JOURNAL, AUTOMATION ;
- `scripts/project-pre-commit` exécute les contrôles rapides propres au projet (tirets interdits, lint Python, validation du plugin) ;
- intégration continue GitHub Actions rejouant les mêmes contrôles.

Tests : `tests/git-hooks/test-hooks` (unitaire du socle), CI complète (E2E de la chaîne de contrôle).

<a id="RG-001"></a>
### [ ] RG-001 Plugin Claude Code, marketplace et client de hook fail-closed

Objectif : distribuer le plugin `rgpd-guard` par une marketplace hébergée dans ce dépôt et relayer chaque événement de hook vers le moteur local.

Critères d'acceptation :
- `.claude-plugin/marketplace.json` à la racine et `plugins/rgpd-guard/.claude-plugin/plugin.json` valides (`claude plugin validate`) ;
- hooks déclarés : SessionStart, UserPromptSubmit, UserPromptExpansion, PreToolUse, PostToolUse, PostToolUseFailure, PostToolBatch, SubagentStart ([DAT §4](DAT.md#flux-hooks)) ;
- client `scripts/guard-hook.sh` POSIX `sh` + `curl`, sans dépendance, jeton jamais passé en argument de commande, `--noproxy '*'` ;
- moteur injoignable, en erreur ou trop lent : blocage des prompts et refus des outils lorsque `fail_mode=closed` (défaut), avertissement seul lorsque `fail_mode=open` ;
- options utilisateur : `engine_url`, `engine_token` (sensible), `fail_mode`, `profile`.

Tests : contrats du client (moteur démarré, arrêté, lent, réponse invalide) ; E2E Claude Code réel avec faux serveur API.

<a id="RG-002"></a>
### [ ] RG-002 Détecteur de règles et validateurs FR/UE

Objectif : détecter sans modèle les identifiants structurés, avec validation par somme de contrôle lorsqu'elle existe.

Critères d'acceptation :
- EMAIL, TELEPHONE (phonenumbers, FR et international), IBAN (mod 97), CARTE_BANCAIRE (Luhn + préfixes), NIR (clé), SIREN/SIRET (Luhn), IP publique, PLAQUE (SIV), DATE_NAISSANCE (contexte), CODE_POSTAL dans une adresse, URL_SENSIBLE (identifiants ou jetons dans l'URL) ;
- valeurs invalides (checksum faux) non signalées ou signalées avec un score réduit ;
- exclusions par défaut : IP privées et de bouclage, domaines `example.*`, UUID et empreintes.

Tests : unitaires par type (positifs, négatifs, limites) ; E2E via le bac à sable et via le hook de prompt.

<a id="RG-003"></a>
### [ ] RG-003 Détecteur de secrets

Objectif : détecter clés API, jetons et clés privées avant tout envoi.

Critères d'acceptation :
- règles à préfixes connus (fournisseurs cloud, forges, messageries, paiement, IA, JWT, clés privées PEM) inspirées des règles gitleaks (MIT) ;
- détection d'affectations à forte entropie (`password=`, `secret:`, `token =`) uniquement en contexte d'affectation ;
- aucun secret d'apparence réelle écrit en dur dans le dépôt : les fixtures sont construites à l'exécution.

Tests : unitaires (vrais positifs construits, faux positifs courants : hash, UUID, base64 d'image) ; E2E via le hook de prompt.

<a id="RG-004"></a>
### [ ] RG-004 Pseudonymisation réversible et coffre de session

Objectif : remplacer chaque valeur sensible par un jeton stable `⟦TYPE_N⟧` et pouvoir réinjecter la valeur exacte localement.

Critères d'acceptation :
- même valeur, même jeton dans une session ; numérotation par type ;
- coffre en mémoire vive uniquement, par session, avec durée de vie configurable, jamais persisté ni exposé par l'API d'administration ;
- réhydratation exacte (valeur d'origine au caractère près) ; jeton inconnu signalé.

Tests : unitaires (aller-retour, collisions, expiration, concurrence) ; E2E réhydratation d'un Edit sur disque.

<a id="RG-005"></a>
### [ ] RG-005 Blocage des prompts et proposition pseudonymisée

Objectif : bloquer un prompt sensible avant qu'il n'atteigne le modèle et proposer une version pseudonymisée prête à copier.

Critères d'acceptation :
- `decision: block`, motif en français listant les types détectés avec aperçu masqué, prompt pseudonymisé complet, `suppressOriginalPrompt: true` ;
- préfixe de contournement `#rgpd-ok` : laisse passer le prompt, journalise le contournement, ne s'applique jamais aux secrets ;
- détections de niveau `warn` : prompt transmis, message système affiché à l'utilisateur ;
- mentions `@fichier` : traitement conforme au constat de la capture M1 consigné dans le JOURNAL ;
- UserPromptExpansion traité comme un prompt.

Tests : unitaires de l'adaptateur ; E2E Claude Code réel : le faux serveur API ne reçoit jamais la valeur canari.

<a id="RG-006"></a>
### [ ] RG-006 Hooks d'outils : pseudonymisation des sorties, filet final et réhydratation

Objectif : empêcher qu'une sortie d'outil (fichier lu, commande, recherche, MCP) transmette une donnée sensible, sans casser l'édition des fichiers.

Critères d'acceptation :
- PostToolUse : parcours générique de `tool_response`, remplacement des seules feuilles texte, forme strictement conservée, `updatedToolOutput` et note de comptage pour Claude ;
- PostToolBatch : nouveau contrôle (profil `rapide`) du contenu sérialisé final ; donnée résiduelle : `decision: block` avec consigne de retour arrière ;
- PostToolUseFailure : événement journalisé comme fuite probable lorsque l'erreur contient une donnée ;
- PreToolUse : refus des fichiers secrets (`.env*`, `*.pem`, `*.key`, `id_rsa*`, `*.kdbx`...) ; réhydratation des jetons pour Write, Edit, MultiEdit, NotebookEdit et les chemins de Read, Grep, Glob ; jamais pour Bash, WebFetch, WebSearch ni MCP ; jeton inconnu : refus ; décision `allow` seulement en mode `bypassPermissions` ou `acceptEdits`, `ask` sinon ;
- SessionStart et SubagentStart : consigne de conservation des jetons injectée dans le contexte.

Tests : unitaires du parcours de forme et de la réhydratation ; E2E Claude Code réel : Read pseudonymisé, Edit réhydraté sur disque, canari jamais transmis.

<a id="RG-007"></a>
### [ ] RG-007 Détecteur spaCy (FR, EN)

Objectif : localiser les personnes et les lieux dans le texte libre.

Critères d'acceptation : `fr_core_news_md` et `en_core_web_md` chargés au démarrage, choix de langue par heuristique légère, NER désactivée sur le code (fichiers source, blocs de code des prompts), jetons `⟦...⟧` ignorés.

Tests : unitaires sur corpus FR/EN ; E2E bac à sable profil `equilibre`.

<a id="RG-008"></a>
### [ ] RG-008 Classificateur Laya des catégories sensibles

Objectif : estimer avec des probabilités calibrées si un texte révèle une catégorie sensible (art. 9 RGPD, RH, mineurs, confidentialité).

Critères d'acceptation : `convaiinnovations/laya-multilingual` exécuté sur CPU, questions typées `noul` en une seule passe, seuils par catégorie ; règle d'escalade : catégorie sensible et identifiant présent bloquent, catégorie seule avertit.

Tests : unitaires de la règle d'escalade (classificateur simulé par contrat documenté) et intégration réelle du modèle ; E2E bac à sable.

<a id="RG-009"></a>
### [ ] RG-009 Détecteur GLiNER PII (profil max)

Objectif : rappel maximal multilingue sur les entités non structurées.

Critères d'acceptation : `urchade/gliner_multi_pii-v1` sur CPU, labels zero-shot (personne, adresse, date de naissance, numéro d'identité, santé), découpage en fenêtres avec recouvrement, plafond de taille.

Tests : unitaires (fusion, fenêtres) ; E2E bac à sable profil `max`.

<a id="RG-010"></a>
### [ ] RG-010 Profils, politiques et liste blanche

Objectif : rendre la décision configurable sans code.

Critères d'acceptation : profils `rapide`, `equilibre`, `max` ; politique par type (`block`, `warn`, `allow` pour les prompts ; `pseudonymize`, `allow` pour les sorties ; score minimal) ; liste blanche de valeurs et de motifs ; motifs de fichiers secrets ; politique persistée, versionnée, validée côté serveur.

Tests : unitaires de résolution de politique ; API (refus d'une politique invalide) ; E2E page Politiques.

<a id="RG-011"></a>
### [ ] RG-011 Journal d'audit minimisé

Objectif : tracer les décisions sans créer un nouveau gisement de données personnelles.

Critères d'acceptation : SQLite avec migrations versionnées ([SCHEMA](SCHEMA.md)) ; aucune valeur brute ; HMAC à clé locale, aperçu masqué désactivable ; purge par rétention ; session identifiée par empreinte.

Tests : unitaires (aucune valeur brute stockée, purge) ; API ; E2E page Journal.

<a id="RG-012"></a>
### [ ] RG-012 Authentification locale par jeton

Objectif : réserver l'API au client de hook et au dashboard de l'utilisateur.

Critères d'acceptation : jeton en en-tête pour les hooks et l'API ; session dashboard par cookie `HttpOnly`, `SameSite=Strict`, sans persistance ; contrôle de l'en-tête Host et de l'origine ; CORS restreint ; `/health` seul public.

Tests : API directe sans jeton, jeton faux, Host étranger, origine étrangère : refus ; E2E connexion et déconnexion depuis l'accueil.

<a id="RG-013"></a>
### [ ] RG-013 Dashboard : accueil, connexion et Journal

Critères d'acceptation : accueil public avec état du moteur, connexion par jeton, Journal paginé et filtrable (type, décision, événement), statistiques par type.

Tests : unitaires de composants ; E2E Playwright par le parcours canonique avec captures JPEG.

<a id="RG-014"></a>
### [ ] RG-014 Dashboard : Bac à sable

Critères d'acceptation : saisie d'un texte, choix du profil, surlignage des entités, catégories sensibles, texte pseudonymisé, décision, latence par détecteur.

Tests : unitaires ; E2E Playwright avec captures JPEG et vidéo webm.

<a id="RG-015"></a>
### [ ] RG-015 Dashboard : Politiques

Critères d'acceptation : édition des actions et seuils par type, liste blanche, motifs de fichiers secrets, enregistrement validé côté serveur, erreurs explicites.

Tests : unitaires ; E2E Playwright (modification puis effet observable dans le bac à sable).

<a id="RG-016"></a>
### [ ] RG-016 Dashboard : Moteurs

Critères d'acceptation : état et temps de chargement de chaque détecteur, dernier banc d'évaluation (P/R/F1 par type, latence p50/p95 par profil).

Tests : unitaires ; E2E Playwright.

<a id="RG-017"></a>
### [ ] RG-017 Seeds déterministes et banc d'évaluation

Critères d'acceptation : générateur à graine fixe (Faker fr_FR et en_US) produisant un corpus étiqueté, positifs et négatifs ; identifiants à checksum valide mais fictifs ; secrets construits à l'exécution ; événements d'audit créés via le véritable endpoint de hook ; banc d'évaluation par profil.

Tests : unitaires (déterminisme, validité des checksums) ; E2E `./runDev.sh seed` puis Journal non vide.

<a id="RG-018"></a>
### [ ] RG-018 Conteneurisation dev, staging, prod et lanceurs

Critères d'acceptation : `docker-compose.yml` et surcharges `dev`, `staging`, `prod` ; `runDev.sh`, `runStaging.sh`, `runProd.sh` (`up`, `down`, `logs`, `seed`, `test`, `e2e`, `bench`, `token`, `reset`) ; fichiers d'environnement documentés ; ports liés à 127.0.0.1 ; modèles intégrés à l'image, exécution hors ligne ; conteneurs non root.

Tests : unitaire des scripts (mode simulation) ; E2E clone propre puis `./runDev.sh up` sain et seedé.

## Plus tard

<a id="RG-019"></a>
### [ ] RG-019 Modèles de laboratoire

Comparer `fastino/gliner2-privacy-filter-PII-multi` et `OpenMed/privacy-filter-multilingual` (Apache-2.0, FR) dans le banc d'évaluation, derrière une option de build.

<a id="RG-020"></a>
### [ ] RG-020 Affichage local des valeurs réelles

Étudier le hook `MessageDisplay` pour réafficher localement les valeurs réelles à la place des jetons, sans les transmettre au modèle.
