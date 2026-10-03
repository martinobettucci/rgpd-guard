# RGPD Guard (plugin Claude Code)

Bloque ou pseudonymise localement, avant leur envoi au modèle, les données personnelles et les secrets présents dans les prompts et les sorties d'outils. Outil P2Enjoy SAS.

Le plugin ne fait aucune détection lui-même : il relaie chaque événement au moteur RGPD Guard qui tourne sur votre poste. Ce moteur doit être démarré depuis le dépôt :

```bash
git clone https://github.com/martinobettucci/rgpd-guard.git
cd rgpd-guard
./runProd.sh up
```

Sans moteur joignable, le plugin bloque les prompts et refuse les outils (option `fail_mode`, `closed` par défaut).

Commandes : `/rgpd-guard:status`, `/rgpd-guard:scan <fichier>`, `/rgpd-guard:dashboard`.

Manuel complet (installation, options, messages affichés, tableau de bord, dépannage) : https://github.com/martinobettucci/rgpd-guard/blob/main/docs/manual.md

Licence MIT.
