# @spec docs/BACKLOG.md#RG-002 | docs/DAT.md#moteur
# @verifies docs/BACKLOG.md#RG-002 | docs/DAT.md#moteur
"""Détecteur de règles : positifs validés, négatifs à somme de contrôle fausse, exclusions."""

from __future__ import annotations

import pytest

from conftest import make_card, make_iban, make_nir, make_siren, make_siret
from rgpd_guard.detectors.rules import RulesDetector
from rgpd_guard.models import DetectionContext
from rgpd_guard.taxonomy import Label

DETECTOR = RulesDetector()


def labels(text: str, code: bool = False) -> dict[Label, list[str]]:
    found: dict[Label, list[str]] = {}
    for span in DETECTOR.detect(text, DetectionContext(code_mode=code)):
        found.setdefault(span.label, []).append(text[span.start : span.end])
    return found


def test_email() -> None:
    assert labels("Écrire à camille.martin@laposte.net svp")[Label.EMAIL] == ["camille.martin@laposte.net"]


def test_iban_valid_with_and_without_spaces() -> None:
    iban = make_iban(3)
    spaced = " ".join(iban[i : i + 4] for i in range(0, len(iban), 4))
    assert labels(f"IBAN {iban}")[Label.IBAN] == [iban]
    assert labels(f"IBAN : {spaced}.")[Label.IBAN] == [spaced]


def test_iban_wrong_checksum_ignored() -> None:
    iban = make_iban(3)
    broken = iban[:-1] + ("0" if iban[-1] != "0" else "1")
    assert Label.IBAN not in labels(f"IBAN {broken}")


def test_nir_valid_and_spaced() -> None:
    nir = make_nir(7)
    spaced = f"{nir[0]} {nir[1:3]} {nir[3:5]} {nir[5:7]} {nir[7:10]} {nir[10:13]} {nir[13:]}"
    assert labels(f"Mon numéro de sécu est {spaced}")[Label.NIR] == [spaced]


def test_nir_wrong_key_ignored() -> None:
    nir = make_nir(7)
    wrong = nir[:-2] + f"{(int(nir[-2:]) + 1) % 97:02d}"
    assert Label.NIR not in labels(f"NIR {wrong}")


def test_card_luhn() -> None:
    card = make_card("4", 16, 5)
    spaced = " ".join(card[i : i + 4] for i in range(0, 16, 4))
    assert labels(f"Carte {spaced} exp 12/29")[Label.CARTE_BANCAIRE] == [spaced]
    broken = card[:-1] + str((int(card[-1]) + 1) % 10)
    assert Label.CARTE_BANCAIRE not in labels(f"Carte {broken}")


def test_siret_requires_context() -> None:
    siret = make_siret(2)
    assert labels(f"SIRET {siret}")[Label.SIRET] == [siret]
    assert Label.SIRET not in labels(f"commande numéro {siret}")


def test_siren_with_context() -> None:
    siren = make_siren(4)
    assert labels(f"RCS Paris {siren[:3]} {siren[3:6]} {siren[6:]}")[Label.SIREN] == [
        f"{siren[:3]} {siren[3:6]} {siren[6:]}"
    ]


def test_phones_fr_and_international() -> None:
    found = labels("Appelle le 06 12 34 56 78 ou le +33 1 23 45 67 89, ou +44 20 7946 0958.")
    assert len(found[Label.TELEPHONE]) == 3


def test_phone_fr_format_outside_metadata() -> None:
    # Tranche fictive ARCEP : absente des métadonnées, mais au format français.
    assert labels("Tel : 06 39 98 12 34")[Label.TELEPHONE] == ["06 39 98 12 34"]
    assert Label.TELEPHONE not in labels("commande 2024-06-12 lot 12345")


@pytest.mark.parametrize("text", ["serveur 10.0.0.12", "localhost 127.0.0.1", "doc 192.0.2.10", "version 1.2.3.4"])
def test_non_public_ip_ignored(text: str) -> None:
    assert Label.IP not in labels(text)


def test_public_ip() -> None:
    assert labels("connexion depuis 81.250.12.34 hier")[Label.IP] == ["81.250.12.34"]


def test_plate_and_context() -> None:
    assert labels("véhicule AB-123-CD gare")[Label.PLAQUE] == ["AB-123-CD"]
    assert labels("immatriculation AB123CD")[Label.PLAQUE] == ["AB123CD"]
    assert Label.PLAQUE not in labels("référence AB123CD")


def test_birth_date_requires_context() -> None:
    assert labels("Il est né le 12/03/1984 à Lyon")[Label.DATE_NAISSANCE] == ["12/03/1984"]
    assert labels("date of birth: March 3, 1984")[Label.DATE_NAISSANCE] == ["March 3, 1984"]
    assert Label.DATE_NAISSANCE not in labels("réunion le 12/03/2024")


def test_address_fr_and_not_in_code() -> None:
    text = "Livrer au 12 bis rue des Lilas, 75011 Paris demain"
    assert labels(text)[Label.ADRESSE][0].startswith("12 bis rue des Lilas")
    assert Label.ADRESSE not in labels(text, code=True)
