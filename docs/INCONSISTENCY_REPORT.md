# Registre d'incohérences

Défauts constatés hors de l'unité en cours, à résoudre par la boucle dédiée (CLAUDE.md §5) dans l'ordre ci-dessous. Chaque entrée quitte le registre avec son issue : corrigée, tranchée sans changement (motif au [journal](JOURNAL.md)) ou convertie en unité du [backlog](BACKLOG.md).

Origine : audit en lecture seule de la v0.1.0 avant la campagne de clôture, constats revérifiés à la main.

## IR-18 Cache des modèles illisible en partie par le moteur

- Constat : à chaque démarrage et à chaque banc, le moteur journalise « Ignoring corrupted tree cache file … [Errno 13] Permission denied » pour Laya, GLiNER et l'encodeur de GLiNER (12 lignes au démarrage de la pile dev).
- Mesure : `huggingface_hub` 1.33 écrit les fichiers `trees/<révision>.json` en mode 600 (propriétaire root, utilisateur du téléchargement) ; le moteur tourne sous l'uid 10001 et ne peut pas les lire. Même situation dans l'image de production, dont l'étape `models` télécharge en root. Le chargement aboutit, les journaux sont pollués.
- Concerne : RG-008, RG-009, `engine/rgpd_guard/model_store.py`, [DAT §15](DAT.md#dependances).
