#!/usr/bin/env python3
# @spec docs/BACKLOG.md#RG-017 | docs/DAT.md#donnees-dev
"""Générateur déterministe du corpus étiqueté de RGPD Guard (graine fixe, données 100 % synthétiques).

Chaque enregistrement : {id, lang, kind, code, text, spans:[{start, end, label}], categories:[...]}.
Les identifiants ont une somme de contrôle valide mais sont fictifs ; les faux secrets sont assemblés
à l'exécution (aucun n'est écrit dans le dépôt) ; la sortie est ignorée par git.

Usage : python seeds/generate.py [--seed 20261002] [--out seeds/out/corpus.jsonl]
"""

from __future__ import annotations

import argparse
import json
import random
import string
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from faker import Faker
from stdnum import iban as std_iban
from stdnum import luhn
from stdnum.fr import nir as std_nir

DEFAULT_SEED = 20261002


@dataclass
class Builder:
    """Assemble un texte à partir de fragments et mémorise la position des valeurs étiquetées."""

    parts: list[str] = field(default_factory=list)
    spans: list[dict[str, Any]] = field(default_factory=list)
    length: int = 0

    def add(self, text: str, label: str | None = None) -> Builder:
        if label:
            self.spans.append({"start": self.length, "end": self.length + len(text), "label": label})
        self.parts.append(text)
        self.length += len(text)
        return self

    @property
    def text(self) -> str:
        return "".join(self.parts)


class Synth:
    def __init__(self, seed: int) -> None:
        self.rnd = random.Random(seed)  # noqa: S311 (données de test déterministes)
        self.fr = Faker("fr_FR")
        self.en = Faker("en_US")
        self.fr.seed_instance(seed)
        self.en.seed_instance(seed + 1)

    def digits(self, n: int) -> str:
        return "".join(self.rnd.choice(string.digits) for _ in range(n))

    def iban(self) -> str:
        bban = self.digits(23)
        return f"FR{std_iban.calc_check_digits('FR00' + bban)}{bban}"

    def iban_spaced(self) -> str:
        value = self.iban()
        return " ".join(value[i : i + 4] for i in range(0, len(value), 4))

    def nir(self) -> str:
        body = f"{self.rnd.choice('12')}{self.rnd.randint(50, 99):02d}{self.rnd.randint(1, 12):02d}75{self.digits(3)}{self.digits(3)}"
        value = body + std_nir.calc_check_digits(body)
        return f"{value[0]} {value[1:3]} {value[3:5]} {value[5:7]} {value[7:10]} {value[10:13]} {value[13:]}"

    def siret(self) -> str:
        base = self.digits(13)
        return base + luhn.calc_check_digit(base)

    def card(self) -> str:
        base = "4" + self.digits(14)
        value = base + luhn.calc_check_digit(base)
        return " ".join(value[i : i + 4] for i in range(0, 16, 4))

    def phone_fr(self) -> str:
        # Tranches fictives réservées par l'ARCEP (06 39 98, 01 99 00).
        prefix = self.rnd.choice(["06 39 98", "01 99 00"])
        return f"{prefix} {self.digits(2)} {self.digits(2)}"

    def plate(self) -> str:
        letters = "ABCDEFGHJKLMNPQRSTVWXYZ"  # lettres SIV (sans I, O, U)
        return f"{self.rnd.choice(letters)}{self.rnd.choice(letters)}-{self.digits(3)}-{self.rnd.choice(letters)}{self.rnd.choice(letters)}"

    def email(self, name: str) -> str:
        local = name.lower().replace(" ", ".").replace("'", "")
        local = "".join(c for c in local if c.isascii() and (c.isalnum() or c == "."))
        domain = self.rnd.choice(["courriel-fictif.fr", "messagerie-test.fr", "mail-demo.eu"])
        return f"{local}@{domain}"

    def github_token(self) -> str:
        return "gh" + "p_" + "".join(self.rnd.choice(string.ascii_letters + string.digits) for _ in range(36))

    def aws_key(self) -> str:
        return "AK" + "IA" + "".join(self.rnd.choice(string.ascii_uppercase + string.digits) for _ in range(16))

    def share_token(self) -> str:
        # Jeton de partage opaque : minuscule, majuscule et chiffre garantis, puis 21 caractères aléatoires.
        alphabet = string.ascii_letters + string.digits
        return (
            self.rnd.choice(string.ascii_lowercase)
            + self.rnd.choice(string.ascii_uppercase)
            + self.rnd.choice(string.digits)
            + "".join(self.rnd.choice(alphabet) for _ in range(21))
        )

    def password(self) -> str:
        alphabet = string.ascii_letters + string.digits + "!#%&*"
        return "".join(self.rnd.choice(alphabet) for _ in range(14))


def person_records(s: Synth, n: int) -> list[dict[str, Any]]:
    records = []
    for i in range(n):
        lang = "fr" if i % 3 else "en"
        fk = s.fr if lang == "fr" else s.en
        name = f"{fk.first_name()} {fk.last_name()}"
        b = Builder()
        if lang == "fr":
            variant = i % 6
            if variant == 0:
                b.add("Peux-tu écrire un mail de relance à ").add(name, "PERSONNE").add(" (").add(
                    s.email(name), "EMAIL"
                )
                b.add(") pour sa facture impayée ?")
            elif variant == 1:
                b.add("Le dossier de ").add(name, "PERSONNE").add(", né le ").add(
                    fk.date_of_birth(minimum_age=20, maximum_age=80).strftime("%d/%m/%Y"), "DATE_NAISSANCE"
                )
                b.add(", numéro de sécurité sociale ").add(s.nir(), "NIR").add(", est incomplet.")
            elif variant == 2:
                b.add("Rembourse ").add(name, "PERSONNE").add(" sur l'IBAN ").add(s.iban_spaced(), "IBAN").add(
                    " avant vendredi."
                )
            elif variant == 3:
                address = f"{s.rnd.randint(1, 120)} rue {fk.last_name()}, {fk.postcode()} {fk.city()}"
                b.add("Livraison chez ").add(name, "PERSONNE").add(", ").add(address, "ADRESSE").add(", tel ").add(
                    s.phone_fr(), "TELEPHONE"
                ).add(".")
            elif variant == 4:
                b.add("Paiement refusé pour la carte ").add(s.card(), "CARTE_BANCAIRE").add(" de ").add(
                    name, "PERSONNE"
                ).add(", à relancer.")
            else:
                b.add("Le véhicule ").add(s.plate(), "PLAQUE").add(" appartient à ").add(name, "PERSONNE").add(
                    ", joignable au "
                ).add(s.phone_fr(), "TELEPHONE").add(".")
        else:
            variant = i % 4
            if variant == 0:
                b.add("Please draft a reply to ").add(name, "PERSONNE").add(" at ").add(s.email(name), "EMAIL").add(
                    " about the delayed order."
                )
            elif variant == 1:
                b.add("Customer ").add(name, "PERSONNE").add(", date of birth ").add(
                    fk.date_of_birth(minimum_age=20, maximum_age=80).strftime("%B %d, %Y").replace(" 0", " "),
                    "DATE_NAISSANCE",
                )
                b.add(", asked for a refund.")
            elif variant == 2:
                b.add("Wire the deposit to ").add(s.iban(), "IBAN").add(" on behalf of ").add(name, "PERSONNE").add(".")
            else:
                b.add("Login from ").add(fk.ipv4_public(), "IP").add(" for account of ").add(name, "PERSONNE").add(
                    " looked suspicious."
                )
        records.append(
            {"lang": lang, "kind": "positif", "code": False, "text": b.text, "spans": b.spans, "categories": []}
        )
    return records


def company_records(s: Synth) -> list[dict[str, Any]]:
    b = Builder().add("Merci de vérifier le SIRET ").add(s.siret(), "SIRET").add(" du fournisseur avant paiement.")
    return [{"lang": "fr", "kind": "positif", "code": False, "text": b.text, "spans": b.spans, "categories": []}]


def secret_records(s: Synth) -> list[dict[str, Any]]:
    records = []
    b = (
        Builder()
        .add("Voici mon .env, pourquoi ça ne marche pas ?\nGITHUB_TOKEN=")
        .add(s.github_token(), "SECRET")
        .add("\nDEBUG=true\n")
    )
    records.append({"lang": "fr", "kind": "positif", "code": True, "text": b.text, "spans": b.spans, "categories": []})
    b = Builder().add("aws_access_key_id = ").add(s.aws_key(), "SECRET").add("\nregion = eu-west-3\n")
    records.append({"lang": "en", "kind": "positif", "code": True, "text": b.text, "spans": b.spans, "categories": []})
    b = Builder().add('db = connect(host="db.local", password="').add(s.password(), "SECRET").add('")\n')
    records.append({"lang": "en", "kind": "positif", "code": True, "text": b.text, "spans": b.spans, "categories": []})
    return records


def url_records(s: Synth) -> list[dict[str, Any]]:
    """URL porteuses d'un mot de passe (secret) ou d'un jeton de partage opaque (URL sensible)."""
    records = []
    b = (
        Builder()
        .add("Le script d'export échoue : curl https://admin:")
        .add(s.password(), "SECRET")
        .add("@intranet.exemple.fr/export.csv, tu vois pourquoi ?")
    )
    records.append({"lang": "fr", "kind": "positif", "code": False, "text": b.text, "spans": b.spans, "categories": []})
    b = (
        Builder()
        .add("Here is the shared folder https://drive.exemple.fr/s/")
        .add(s.share_token(), "URL_SENSIBLE")
        .add(" with the client files.")
    )
    records.append({"lang": "en", "kind": "positif", "code": False, "text": b.text, "spans": b.spans, "categories": []})
    return records


CATEGORY_TEMPLATES: list[tuple[str, str, str]] = [
    ("SANTE", "fr", "{name} a été hospitalisé pour une dépression sévère et suit un traitement depuis mars."),
    ("SANTE", "en", "{name} was diagnosed with type 1 diabetes and needs insulin at work."),
    ("SANTE", "fr", "Ma collègue {name} est enceinte et en arrêt maladie jusqu'en juin."),
    ("OPINION_POLITIQUE", "fr", "{name} est adhérent au Parti communiste et milite chaque week-end."),
    ("OPINION_POLITIQUE", "en", "{name} is a member of the Green Party and campaigns for them."),
    ("RELIGION", "fr", "{name} est musulman pratiquant et demande un aménagement pendant le ramadan."),
    ("ORIENTATION_SEXUELLE", "fr", "{name} a fait son coming out : il est homosexuel."),
    ("SYNDICAT", "fr", "{name} est délégué syndical CGT dans l'entrepôt de Lille."),
    ("JUDICIAIRE", "fr", "{name} a été condamné l'an dernier pour conduite en état d'ivresse."),
    ("JUDICIAIRE", "en", "{name} was arrested last week and is awaiting trial for fraud."),
    ("DONNEES_RH", "fr", "Le salaire de {name} passe à 48 000 euros et son entretien annuel est insuffisant."),
    ("DONNEES_RH", "en", "{name} received a final written warning and will be dismissed if late again."),
    ("MINEUR", "fr", "Mon fils {name}, 9 ans, est en CE2 à l'école Jules Ferry et souffre d'allergies."),
]
CATEGORY_NEGATIVES: list[tuple[str, str]] = [
    ("fr", "Le diabète de type 2 touche plusieurs millions de personnes en France selon les études publiées."),
    ("fr", "Explique-moi la différence entre un syndicat et une association loi 1901."),
    ("en", "What are the main political parties in Germany and how do coalitions work?"),
    ("fr", "Quelles sont les règles du code du travail sur les entretiens annuels ?"),
    ("en", "Summarise the history of religious tolerance in Europe in five bullet points."),
]
CONFIDENTIAL = [
    ("fr", "Document interne, ne pas diffuser : le chiffre d'affaires du T3, non publié, recule de 18 %."),
    ("en", "Confidential: the acquisition of our competitor will be announced next month, keep it internal."),
]


def category_records(s: Synth) -> list[dict[str, Any]]:
    records = []
    for category, lang, template in CATEGORY_TEMPLATES:
        fk = s.fr if lang == "fr" else s.en
        name = f"{fk.first_name()} {fk.last_name()}"
        before, after = template.split("{name}")
        b = Builder().add(before).add(name, "PERSONNE").add(after)
        records.append(
            {"lang": lang, "kind": "positif", "code": False, "text": b.text, "spans": b.spans, "categories": [category]}
        )
    for lang, text in CONFIDENTIAL:
        records.append(
            {"lang": lang, "kind": "positif", "code": False, "text": text, "spans": [], "categories": ["CONFIDENTIEL"]}
        )
    for lang, text in CATEGORY_NEGATIVES:
        records.append({"lang": lang, "kind": "negatif", "code": False, "text": text, "spans": [], "categories": []})
    return records


NEGATIVES: list[tuple[str, bool, str]] = [
    ("fr", False, "Peux-tu m'expliquer comment fonctionne un tri fusion en Python ?"),
    ("fr", False, "Rédige un plan de formation sur la blockchain pour des étudiants de master."),
    ("en", False, "Write unit tests for the parser module and keep coverage above 90 percent."),
    ("fr", False, "Pour l'exemple, utilise l'adresse jean.dupont@example.com dans la documentation."),
    (
        "en",
        True,
        "class UserManager:\n    def find_user(self, user_id: str) -> User:\n        return self.repo.get(user_id)\n",
    ),
    (
        "en",
        True,
        "const commit = '3f786850e387550fdab836ed7e6dc881de23001b';\nconst id = '123e4567-e89b-12d3-a456-426614174000';\n",
    ),
    ("en", True, "server:\n  host: 10.0.0.12\n  port: 8080\n  version: 1.2.3.4\n"),
    ("fr", False, "La réunion de suivi est fixée au 12/03/2026 à 14 h dans la salle Turing."),
    ("fr", False, "Le contact ⟦EMAIL_1⟧ doit recevoir le devis ⟦PERSONNE_2⟧ demain."),
    ("en", False, "password = changeme and token = <your-token> are placeholders in the template."),
    ("en", False, "See https://github.com/org/repo/commit/3f786850e387550fdab836ed7e6dc881de23001b for the fix."),
    ("fr", True, "GET https://api.exemple.fr/v1/clients/123e4567-e89b-12d3-a456-426614174000/commandes\n"),
    (
        "fr",
        False,
        "Lis l'article https://exemple.fr/blog/comment-proteger-ses-donnees-personnelles-2025 avant la réunion.",
    ),
]


def negative_records() -> list[dict[str, Any]]:
    return [
        {"lang": lang, "kind": "negatif", "code": code, "text": text, "spans": [], "categories": []}
        for lang, code, text in NEGATIVES
    ]


def generate(seed: int = DEFAULT_SEED) -> list[dict[str, Any]]:
    s = Synth(seed)
    records = (
        person_records(s, 36)
        + company_records(s)
        + secret_records(s)
        + url_records(s)
        + category_records(s)
        + negative_records()
    )
    for index, record in enumerate(records, start=1):
        record["id"] = f"C{index:03d}"
    return records


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--out", type=Path, default=Path(__file__).resolve().parent / "out" / "corpus.jsonl")
    args = parser.parse_args()
    records = generate(args.seed)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    print(f"{len(records)} enregistrements écrits dans {args.out}")


if __name__ == "__main__":
    main()
