# Schéma de données

Base SQLite du moteur (`${RGPD_GUARD_DATA_DIR}/rgpd-guard.db`), en mode WAL. Les migrations sont des fichiers SQL versionnés dans `engine/rgpd_guard/migrations/`, appliqués au démarrage dans l'ordre de leur préfixe numérique et enregistrés dans `schema_migrations`. Chaque migration s'exécute dans une transaction unique.

Aucune table ne contient de valeur détectée en clair, de prompt ni de contenu de fichier.

<a id="migrations"></a>
## Migrations

| Version | Fichier | Objet | Retour arrière |
|---|---|---|---|
| 1 | `001_init.sql` | journal d'audit, entités, politiques | suppression du fichier de base (données de journal uniquement) |

<a id="migration-001"></a>
### 001 : initialisation

Crée `audit_events`, `audit_entities` et `policies`.

<a id="tables"></a>
## Tables

### `schema_migrations`

| Colonne | Type | Rôle |
|---|---|---|
| `version` | INTEGER, clé | numéro de migration appliquée |
| `applied_at` | TEXT | date ISO 8601 UTC |

### `audit_events`

Un événement de hook traité par le moteur.

| Colonne | Type | Rôle |
|---|---|---|
| `id` | INTEGER, clé | identifiant |
| `ts` | TEXT | date ISO 8601 UTC, sert à la purge par rétention |
| `session_hash` | TEXT | HMAC tronqué du `session_id` Claude Code |
| `subagent` | INTEGER | 1 si l'événement provient d'un sous-agent |
| `event` | TEXT | `user_prompt_submit`, `pre_tool_use`, `post_tool_use`, `post_tool_use_failure`, `post_tool_batch`, `analyze` |
| `tool` | TEXT | nom de l'outil le cas échéant |
| `decision` | TEXT | `block`, `warn`, `pseudonymize`, `allow`, `deny`, `rehydrate`, `leak` |
| `profile` | TEXT | profil appliqué |
| `latency_ms` | REAL | durée de traitement |
| `entity_count` | INTEGER | nombre d'entités retenues |
| `categories` | TEXT | JSON `[{category, probability, action}]` |
| `bypass` | INTEGER | 1 si le préfixe de contournement a été utilisé |
| `partial` | INTEGER | 1 si une partie des détecteurs n'a pas pu s'exécuter (taille, échéance, erreur) |
| `note` | TEXT | motif court rédigé par le moteur, jamais une valeur |

### `audit_entities`

| Colonne | Type | Rôle |
|---|---|---|
| `event_id` | INTEGER | événement parent (suppression en cascade) |
| `label` | TEXT | type de donnée (taxonomie du DAT) |
| `detector` | TEXT | détecteur à l'origine du span |
| `score` | REAL | score de détection |
| `action` | TEXT | action décidée par la politique |
| `value_hmac` | TEXT | HMAC tronqué de la valeur, clé `RGPD_GUARD_HMAC_KEY` (déduplication statistique) |
| `preview` | TEXT | aperçu masqué (au plus deux caractères d'origine), NULL si `RGPD_GUARD_AUDIT_PREVIEW=false` |

### `policies`

| Colonne | Type | Rôle |
|---|---|---|
| `version` | INTEGER | version du document de politique |
| `document` | TEXT | politique complète validée (JSON) |
| `updated_at` | TEXT | date ISO 8601 UTC |

La politique active est la dernière ligne ; à défaut, la politique par défaut du paquet.
