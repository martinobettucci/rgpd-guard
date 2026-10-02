# Composants tiers

RGPD Guard est distribué sous licence MIT. Il s'appuie sur les composants tiers suivants, utilisés sans modification. Les modèles ne sont jamais versionnés dans ce dépôt : ils sont téléchargés à la construction de l'image ou par `python -m rgpd_guard.model_store`, à une révision épinglée.

## Modèles

| Modèle | Révision | Licence | Usage |
|---|---|---|---|
| `fr_core_news_md` (roue Explosion) | 3.8.0 | LGPL-LR (Lesser General Public License for Linguistic Resources) | détecteur spaCy, français |
| `en_core_web_md` (roue Explosion) | 3.8.0 | MIT | détecteur spaCy, anglais |
| `convaiinnovations/laya-multilingual` | `e4e9ddf` | Apache-2.0 | classificateur de catégories sensibles |
| `urchade/gliner_multi_pii-v1` | `1fcf13e` | Apache-2.0 | détecteur GLiNER |
| `microsoft/mdeberta-v3-base` (configuration et tokenizer seulement) | `a048466` | MIT | encodeur de GLiNER |

## Bibliothèques Python du moteur

| Bibliothèque | Licence |
|---|---|
| fastapi | MIT |
| uvicorn | BSD-3-Clause |
| pydantic, pydantic-settings | MIT |
| python-stdnum | LGPL-2.1 ou ultérieure (bibliothèque utilisée sans modification) |
| phonenumbers | Apache-2.0 |
| PyYAML | MIT |
| spaCy | MIT |
| laya | Apache-2.0 |
| gliner | Apache-2.0 |
| torch (version CPU) | BSD-3-Clause |
| transformers, huggingface-hub, sentencepiece | Apache-2.0 |
| protobuf | BSD-3-Clause |
| Faker (données de développement uniquement) | MIT |

## Règles de détection

Les motifs de secrets à préfixe connu s'inspirent des règles publiques de [gitleaks](https://github.com/gitleaks/gitleaks) (MIT). Aucune règle de trufflehog (AGPL-3.0) n'est reprise.

## Socle de méthode

Les fichiers de méthode importés de [P2Enjoy/software-factory-base](https://github.com/P2Enjoy/software-factory-base) sont sous Mozilla Public License 2.0 ([LICENSES/MPL-2.0.txt](LICENSES/MPL-2.0.txt)).
