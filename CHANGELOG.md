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

### Corrigé

- Numéro de version précédé de `version:` pris pour une adresse IP publique.

## [Publié]

_Aucune version publiée pour le moment._
