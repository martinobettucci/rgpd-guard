# Registre d'incohérences

Défauts constatés hors de l'unité en cours, à résoudre par la boucle dédiée (CLAUDE.md §5) dans l'ordre ci-dessous. Chaque entrée quitte le registre avec son issue : corrigée, tranchée sans changement (motif au [journal](JOURNAL.md)) ou convertie en unité du [backlog](BACKLOG.md).

Origine : relecture des critères d'acceptation avant le passage des unités à `[x]`, après la campagne de clôture.

## IR-19 URL porteuses d'identifiants : fragment de mot de passe transmis, type URL_SENSIBLE jamais produit

- Constat : RG-002, le DAT (§6.1, taxonomie) et la politique par défaut prévoient le type `URL_SENSIBLE` (identifiants ou jetons dans l'URL), mais aucun détecteur ne le produit.
- Mesure, profil `rapide`, analyse d'un prompt :
  - `https://admin:Zq8!vL3pW9@intranet.exemple.fr/export` : le détecteur de règles voit un email `vL3pW9@intranet.exemple.fr` qui chevauche le secret `Zq8!vL3pW9` ; la fusion garde l'email, la version pseudonymisée laisserait passer `admin:Zq8!`, un fragment du mot de passe ;
  - `https://drive.exemple.fr/partage/s/<jeton de 26 caractères>` : aucune détection ;
  - un jeton en paramètre (`?access_token=…`) et un email en paramètre sont, eux, détectés (secret, email).
- Le corpus seedé du banc ne contient aucune URL.
- Concerne : RG-002, RG-003, RG-017, `engine/rgpd_guard/detectors/rules.py`, [DAT §6](DAT.md#moteur).
