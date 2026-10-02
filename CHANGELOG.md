# Changelog

Toutes les évolutions notables de RGPD Guard sont consignées ici.

## [Non publié]

### Ajouté

- Socle d'usine logicielle P2Enjoy : contrat de méthode, adaptateur Codex, sous-agents bornés, hooks Git versionnés et leur harnais de test, contrat du worker planifié, design system global.
- Documentation projet : règles locales, contrat des garde-fous, dossier d'architecture technique, backlog de la version 0.1.0 et journal de cadrage (choix des moteurs CPU, contrat des hooks Claude Code).
- Contrôles rapides propres au projet et intégration continue.
- Capture réelle du contrat des hooks Claude Code (faux serveur API, payloads conservés en fixtures).
- Plugin Claude Code `rgpd-guard` et marketplace `p2enjoy` : hooks SessionStart, UserPromptSubmit, PreToolUse, PostToolUse, PostToolUseFailure, PostToolBatch et SubagentStart ; client `sh` + `curl` fail-closed ; commandes `/rgpd-guard:status`, `/rgpd-guard:scan`, `/rgpd-guard:dashboard`.
- Moteur local : détecteur de règles (email, téléphone, IBAN, carte, NIR, SIREN, SIRET, IP publique, plaque, date de naissance, adresse), détecteur de secrets, pseudonymisation réversible `⟦TYPE_N⟧` avec coffre en mémoire, politique configurable, journal d'audit SQLite minimisé, authentification par jeton et session, résolution des mentions `@fichier`, analyse de fichier par comptages.
- Tests unitaires, API, contrats du client et E2E Claude Code réel prouvant qu'aucune valeur canari n'atteint le fournisseur.
- Détecteurs à modèles CPU, hors ligne et épinglés : spaCy (FR, EN), GLiNER multilingue (profil `max`) et classificateur calibré Laya pour les catégories sensibles (art. 9, RH, mineurs, confidentialité).
- Corpus seedé déterministe, banc d'évaluation par profil (précision, rappel, F1, latences) et seuils de catégories calibrés.
- Contrôle de traçabilité : chaque référence `@spec` ou `@verifies` doit désigner une ancre existante.
- Inventaire des licences tierces (THIRD_PARTY_NOTICES.md).
- Tableau de bord React + Vite aux couleurs P2Enjoy : accueil et connexion par jeton, Journal filtrable et paginé, Bac à sable (texte annoté, version pseudonymisée, latences), Politiques (modale par section, rétablissement confirmé), Moteurs (composants, profils, banc).
- Conteneurisation : images moteur (dev, prod avec modèles intégrés) et tableau de bord (Vite, nginx non root), Compose dev, staging et prod, lanceurs `runDev.sh`, `runStaging.sh`, `runProd.sh`, fichiers d'environnement commentés, seed rejoué à travers les vrais hooks.
- Parcours E2E Playwright du tableau de bord (captures JPEG, vidéos webm).
- Classification des catégories sur une copie du texte où les identifiants structurés et les jetons sont remplacés par des marqueurs neutres (moins de faux positifs, plus de catégories reconnues quand des identifiants sont mêlés au texte).
- Page Moteurs : classificateurs de catégories affichés pour chaque profil.
- `./runDev.sh test` exécute aussi les contrats du client de hook dans le conteneur.

### Modifié

- Traçabilité : chaque référence `@spec` / `@verifies` nomme une section (ancres explicites de DESIGN_SYSTEM_APP, numéros de section du design system global) ; `scripts/check-spec-refs` refuse les références sans section, avec son harnais de test.
- Pipelines spaCy `fr_core_news_md` et `en_core_web_md` 3.8.0, publiés par Explosion pour spaCy 3.8 et installés avec l'extra `nlp` (roues épinglées par empreinte) : fin de l'avertissement W095 émis par les versions 3.7 du Hub Hugging Face.
- `scripts/project-pre-commit` vérifie que les fichiers importés du socle restent identiques à leurs empreintes amont (`config/socle-files.txt`).
- Erreurs de validation de l'API traduites en français par type d'erreur ; message d'expression régulière invalide sans texte anglais.

### Corrigé

- Numéro de version précédé de `version:` pris pour une adresse IP publique.
- Rechargement à chaud du moteur dev qui scrutait l'environnement virtuel monté et occupait un cœur en continu.
- Accueil du tableau de bord et commande `/rgpd-guard:dashboard` : même indication pour obtenir le jeton (`./runProd.sh token`, ou le lanceur de l'environnement démarré).
- SCHEMA.md aligné sur la migration (colonnes `id`, aucun événement `analyze`) et protégé par un test qui compare tables et colonnes documentées à la base migrée.
- DAT : la règle des délais emboîtés vaut pour les hooks qui analysent un texte ; un test du client la vérifie à partir de `hooks.json`.
- DAT et critère de RG-012 : routes de session (publiques, la lecture ne renvoie que l'état de connexion) et rétablissement de la politique documentés ; tests d'accès direct étendus aux écritures de la politique.
- Variables d'environnement : README complété (moteur, client de hook, lanceurs, serveur Vite) et protégé par un test ; réglages `models_dir` et `test_endpoints` jamais lus retirés.
- Chiffres du banc d'évaluation cités par le README et le DAT : remplacés par ceux du banc rejoué après le masquage avant Laya et le passage à spaCy 3.8.0 (latences p50 394 ms en `equilibre`, 496 ms en `max`).
- Page Moteurs : le temps de chargement n'apparaissait pour aucun composant (masqué par la liste des modèles, et non mesuré pour `rules` et `secrets`) ; il est désormais mesuré et affiché pour chaque composant prêt.
- Tableau de bord : une durée mesurée sous la demi-milliseconde (p50 du profil Rapide, réinjections du journal) s'affichait « 0 » ; elle s'écrit désormais « < 1 ».
- `./runDev.sh e2e` pile arrêtée : le garde-fou ne bloquait jamais (`docker compose ps` réussit sans conteneur) et Playwright échouait plus loin sur une erreur réseau ; le refus « pile arrêtée » est désormais immédiat.
- `./runStaging.sh bench` et `./runProd.sh bench` échouaient faute de générateur seedé : le banc est désormais réservé au dev avec un message explicite, et la page Moteurs indique comment le mesurer quand aucun banc n'est enregistré.
- `.gitignore` du socle modifié par des règles du projet : restauré à l'identique de l'amont, règles du projet déplacées dans des `.gitignore` imbriqués, caches locaux regroupés sous `.cache/` (`models-cache/` devient `.cache/models/`).
- Construction impossible depuis un clone neuf : le paquet CA vide utilisé par défaut était exclu par le `.gitignore` ; il est désormais suivi sous `config/ca/empty.pem`.
- Tableau de bord : liste des types détectés décalée, barre de navigation mobile incomplète, en-tête mobile empilé, faux espace avant la ponctuation dans le texte annoté.

## [Publié]

_Aucune version publiée pour le moment._
