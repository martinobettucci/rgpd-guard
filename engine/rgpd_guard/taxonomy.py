# @spec docs/BACKLOG.md#RG-002 | docs/BACKLOG.md#RG-008 | docs/DAT.md#moteur
"""Taxonomie des types de données détectées et des catégories sensibles."""

from __future__ import annotations

from enum import StrEnum


class Label(StrEnum):
    """Types de spans localisés dans un texte."""

    PERSONNE = "PERSONNE"
    EMAIL = "EMAIL"
    TELEPHONE = "TELEPHONE"
    ADRESSE = "ADRESSE"
    IBAN = "IBAN"
    CARTE_BANCAIRE = "CARTE_BANCAIRE"
    NIR = "NIR"
    SIREN = "SIREN"
    SIRET = "SIRET"
    IP = "IP"
    PLAQUE = "PLAQUE"
    DATE_NAISSANCE = "DATE_NAISSANCE"
    URL_SENSIBLE = "URL_SENSIBLE"
    SECRET = "SECRET"  # noqa: S105 (libellé de type)
    LIEU = "LIEU"
    ORGANISATION = "ORGANISATION"


class Category(StrEnum):
    """Catégories sensibles estimées sur l'ensemble d'un texte."""

    SANTE = "SANTE"
    OPINION_POLITIQUE = "OPINION_POLITIQUE"
    RELIGION = "RELIGION"
    ORIENTATION_SEXUELLE = "ORIENTATION_SEXUELLE"
    ORIGINE_ETHNIQUE = "ORIGINE_ETHNIQUE"
    SYNDICAT = "SYNDICAT"
    JUDICIAIRE = "JUDICIAIRE"
    DONNEES_RH = "DONNEES_RH"
    MINEUR = "MINEUR"
    CONFIDENTIEL = "CONFIDENTIEL"


LABEL_NAMES: dict[Label, str] = {
    Label.PERSONNE: "nom de personne",
    Label.EMAIL: "adresse email",
    Label.TELEPHONE: "numéro de téléphone",
    Label.ADRESSE: "adresse postale",
    Label.IBAN: "IBAN",
    Label.CARTE_BANCAIRE: "numéro de carte bancaire",
    Label.NIR: "numéro de sécurité sociale (NIR)",
    Label.SIREN: "SIREN",
    Label.SIRET: "SIRET",
    Label.IP: "adresse IP publique",
    Label.PLAQUE: "plaque d'immatriculation",
    Label.DATE_NAISSANCE: "date de naissance",
    Label.URL_SENSIBLE: "URL contenant un identifiant ou un jeton",
    Label.SECRET: "secret (clé, jeton, mot de passe)",
    Label.LIEU: "lieu",
    Label.ORGANISATION: "organisation",
}

CATEGORY_NAMES: dict[Category, str] = {
    Category.SANTE: "santé",
    Category.OPINION_POLITIQUE: "opinions politiques",
    Category.RELIGION: "convictions religieuses ou philosophiques",
    Category.ORIENTATION_SEXUELLE: "vie ou orientation sexuelle",
    Category.ORIGINE_ETHNIQUE: "origine raciale ou ethnique",
    Category.SYNDICAT: "appartenance syndicale",
    Category.JUDICIAIRE: "condamnations et infractions",
    Category.DONNEES_RH: "données RH (salaire, évaluation, sanction)",
    Category.MINEUR: "données concernant un mineur",
    Category.CONFIDENTIEL: "information confidentielle d'entreprise",
}

# Identifiants directs : leur présence avec une catégorie sensible rend la donnée bloquante.
DIRECT_IDENTIFIERS: frozenset[Label] = frozenset(
    {
        Label.PERSONNE,
        Label.EMAIL,
        Label.TELEPHONE,
        Label.ADRESSE,
        Label.IBAN,
        Label.CARTE_BANCAIRE,
        Label.NIR,
        Label.PLAQUE,
        Label.DATE_NAISSANCE,
    }
)

# Marqueurs neutres substitués aux identifiants structurés dans le texte soumis aux classificateurs de
# catégories : les longues suites de chiffres, adresses email et jetons ⟦TYPE_N⟧ diluent ou détournent
# le signal sémantique, alors qu'un marqueur garde la structure de la phrase. Restent en clair les noms
# de personnes (langage naturel, leur masquage ajoutait des faux positifs sur le banc), les lieux et
# les organisations (ils portent souvent la catégorie elle-même : hôpital, syndicat, parti).
CLASSIFIER_PLACEHOLDERS: dict[Label, str] = {
    Label.EMAIL: "[email]",
    Label.TELEPHONE: "[téléphone]",
    Label.ADRESSE: "[adresse]",
    Label.IBAN: "[IBAN]",
    Label.CARTE_BANCAIRE: "[carte bancaire]",
    Label.NIR: "[numéro de sécurité sociale]",
    Label.SIREN: "[SIREN]",
    Label.SIRET: "[SIRET]",
    Label.IP: "[adresse IP]",
    Label.PLAQUE: "[plaque]",
    Label.DATE_NAISSANCE: "[date de naissance]",
    Label.URL_SENSIBLE: "[URL]",
    Label.SECRET: "[secret]",
}
