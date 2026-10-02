---
description: Compte les données sensibles d'un fichier sans les révéler au modèle
argument-hint: <chemin du fichier>
allowed-tools: Bash(sh:*)
---
Résultat de l'analyse locale de `$ARGUMENTS` par RGPD Guard (comptages par type uniquement, aucune valeur) :

!`sh "${CLAUDE_PLUGIN_ROOT}/scripts/scan.sh" "$ARGUMENTS"`

Présente ce résultat en français : nombre de données sensibles par type et décision. Ne lis pas le fichier toi-même pour vérifier.
