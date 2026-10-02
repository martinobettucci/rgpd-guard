# Design System Extension : RGPD Guard

Référence complémentaire à [DESIGN_SYSTEM.md](DESIGN_SYSTEM.md), lue intégralement avant toute modification de l'interface. Seules les règles propres au tableau de bord de RGPD Guard sont documentées ici.

## 1. Architecture spécifique

- **Accueil (`/`)**, surface autonome sans navigation applicative (DS §6.17) : marque, titre, phrase explicative, état du moteur (pilule « Moteur en ligne » ou « Moteur injoignable », profil actif), formulaire de connexion par jeton. Une session ouverte redirige vers le Journal.
- **Application**, barre latérale de premier degré (DS §5.4) avec quatre destinations, chacune une URL :
  - **Journal** (`/journal`) : événements traités par le moteur ;
  - **Bac à sable** (`/bac-a-sable`) : analyse d'un texte saisi ;
  - **Politiques** (`/politiques`) : règles de décision ;
  - **Moteurs** (`/moteurs`) : état des détecteurs et banc d'évaluation.
- En-tête de zone principale : titre de la destination, à droite la commande « Se déconnecter ».
- Pied de page : lien en clair vers https://p2enjoy.studio.
- Aucune donnée n'est stockée dans le navigateur : la session est un cookie `HttpOnly` posé par le moteur, sans persistance (CLAUDE.md §11).

## 2. Terminologie métier

| Terme technique | Libellé affiché |
|---|---|
| `block` | Bloqué |
| `warn` | Avertissement |
| `pseudonymize` | Pseudonymisé |
| `allow` | Autorisé |
| `deny` | Refusé |
| `rehydrate` | Réinjecté |
| `leak` | Fuite arrêtée |
| `user_prompt_submit` | Prompt |
| `pre_tool_use` | Avant outil |
| `post_tool_use` | Sortie d'outil |
| `post_tool_use_failure` | Échec d'outil |
| `post_tool_batch` | Contrôle final |
| profils `rapide`, `equilibre`, `max` | Rapide, Équilibré, Maximal |

Les types de données et catégories sensibles utilisent les libellés fournis par l'API (`/v1/policies`), source unique avec le moteur.

## 3. Composants métier

- **Badge de décision** : pilule (DS §6.8) avec icône et libellé ; correspondance unique dans `dashboard/src/lib/decisions.ts` : Bloqué, Refusé et Fuite arrêtée en `danger` ; Avertissement en `accent` ; Pseudonymisé et Réinjecté en `brand` ; Autorisé en `success`.
- **Texte annoté** (Bac à sable) : le texte analysé est rendu en texte brut, chaque valeur détectée est un `mark` coloré selon son action, suivi d'une étiquette lisible portant le type (jamais la couleur seule, DS §1.5). Les valeurs ne sont jamais interprétées comme HTML.
- **Jeton de pseudonymisation** : rendu en police à chasse fixe (DS §3.1).
- **Section de politique** : fenêtre en lecture découpée en sections (Types de données, Catégories sensibles, Liste blanche, Fichiers secrets) ; chaque section porte sa commande « Modifier » qui ouvre une modale limitée à cette section (DS §6.27). « Rétablir la politique par défaut » est une action sensible confirmée dans le flux (DS §6.22, §6.23).

## 4. Règles de visualisation particulières

- Les aperçus de valeurs du journal sont déjà masqués par le moteur (au plus deux caractères d'origine) ; l'interface ne cherche jamais à les reconstituer.
- Les scores et probabilités s'affichent avec deux décimales, les latences en millisecondes entières, en chiffres tabulaires.
- Une mesure de banc absente est nommée « Aucun banc d'évaluation enregistré » (DS §14.6), jamais rendue par zéro.

## 5. Responsive spécifique

- Sous 1024 px, la barre latérale devient une barre inférieure à libellés visibles (DS §5.4).
- Le tableau du journal défile dans son propre conteneur avec indication de débordement (DS §8.2).

## 6. Écarts au design system commun

Aucun écart à ce jour.

## 7. Captures de référence

Produites par les tests Playwright du parcours canonique dans `e2e/playwright/captures/` (JPEG) et `e2e/playwright/videos/` (webm), régénérées à chaque changement d'apparence.
