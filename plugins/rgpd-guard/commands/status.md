---
description: Affiche l'état du moteur RGPD Guard local (profil, détecteurs prêts)
allowed-tools: Bash(sh:*)
---
État du moteur RGPD Guard (aucune donnée personnelle dans cette sortie) :

!`sh "${CLAUDE_PLUGIN_ROOT}/scripts/status.sh"`

Résume cet état en français en deux ou trois phrases : le moteur répond-il, quel profil est actif, quels détecteurs manquent éventuellement. Si le moteur ne répond pas, rappelle de lancer `./runProd.sh up` depuis le dépôt rgpd-guard.
