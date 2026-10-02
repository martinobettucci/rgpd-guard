# @spec docs/BACKLOG.md#RG-002 | docs/DAT.md#moteur
"""Détecteur de règles : identifiants structurés validés par somme de contrôle quand elle existe."""

from __future__ import annotations

import ipaddress
import re

import phonenumbers
from stdnum import iban as std_iban
from stdnum import luhn
from stdnum.fr import nir as std_nir

from ..models import DetectionContext, Span
from ..taxonomy import Label

_EMAIL_RE = re.compile(
    r"(?<![\w.+-])[A-Za-z0-9][A-Za-z0-9._%+-]{0,63}@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,24}\b"
)
_IBAN_RE = re.compile(r"\b[A-Z]{2}\d{2}(?:[ ]?[A-Z0-9]{4}){2,7}(?:[ ]?[A-Z0-9]{1,4})?\b")
_CARD_RE = re.compile(r"(?<![\d-])(?:\d[ -]?){12,18}\d(?![\d-])")
_NIR_RE = re.compile(
    r"(?<!\d)[12][ .]?\d{2}[ .]?(?:0[1-9]|1[0-2]|[2-9]\d)[ .]?(?:\d{2}|2[AB])[ .]?\d{3}[ .]?\d{3}[ .]?\d{2}(?!\d)"
)
_SIRET_RE = re.compile(r"(?<!\d)\d{3}[ .]?\d{3}[ .]?\d{3}[ .]?\d{5}(?!\d)")
_SIREN_RE = re.compile(r"(?<!\d)\d{3}[ .]?\d{3}[ .]?\d{3}(?![\d ]?\d)")
_COMPANY_CONTEXT_RE = re.compile(r"\b(siren|siret|rcs|r\.c\.s|immatricul\w*|n°\s*tva|tva\s+intra\w*)\b", re.IGNORECASE)
_IPV4_RE = re.compile(
    r"(?<![\d.])(?:(?:25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)\.){3}(?:25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(?![\d.])"
)
_IPV6_RE = re.compile(r"(?<![\w:])(?:[0-9a-fA-F]{1,4}:){2,7}[0-9a-fA-F]{0,4}(?::[0-9a-fA-F]{1,4})*(?![\w:])")
_VERSION_CONTEXT_RE = re.compile(r"(version|v|release|ver\.?)\s*$", re.IGNORECASE)
# Format français, y compris les tranches récentes ou fictives absentes des métadonnées de libphonenumber.
_FR_PHONE_RE = re.compile(r"(?<![\d+])(?:\+33\s?|0033\s?|0)[1-9](?:[ .-]?\d{2}){4}(?!\d)")
_PLATE_RE = re.compile(r"\b(?!SS|WW)[A-HJ-NP-TV-Z]{2}[- ]\d{3}[- ](?!SS)[A-HJ-NP-TV-Z]{2}\b")
_PLATE_BARE_RE = re.compile(r"\b(?!SS|WW)[A-HJ-NP-TV-Z]{2}\d{3}(?!SS)[A-HJ-NP-TV-Z]{2}\b")
_PLATE_CONTEXT_RE = re.compile(r"\b(immatricul\w*|plaque|license\s+plate|plate)\b", re.IGNORECASE)

_MONTHS = (
    r"janvier|février|fevrier|mars|avril|mai|juin|juillet|août|aout|septembre|octobre|novembre|décembre|decembre|"
    r"january|february|march|april|may|june|july|august|september|october|november|december"
)
_DATE_RE = re.compile(
    r"\b(?:(?:0?[1-9]|[12]\d|3[01])[/.-](?:0?[1-9]|1[0-2])[/.-](?:19|20)\d{2}"
    r"|(?:19|20)\d{2}-(?:0[1-9]|1[0-2])-(?:0[1-9]|[12]\d|3[01])"
    r"|(?:1er|[12]?\d|3[01])\s+(?:" + _MONTHS + r")\s+(?:19|20)\d{2}"
    r"|(?:" + _MONTHS + r")\s+(?:[12]?\d|3[01]),?\s+(?:19|20)\d{2})\b",
    re.IGNORECASE,
)
_BIRTH_CONTEXT_RE = re.compile(
    r"(n[ée]e?\s+le|date\s+de\s+naissance|naissance|né\(e\)|ddn|date\s+of\s+birth|d\.?o\.?b\.?|born(\s+on)?|birth\s*date"
    r"|birthday|anniversaire)\W{0,5}[\w\s,:]{0,12}$",
    re.IGNORECASE,
)

_STREET_TYPES = (
    r"rue|avenue|av\.|boulevard|bd|allée|allee|impasse|place|chemin|route|quai|cours|square|résidence|residence"
    r"|lotissement|faubourg|passage|voie|sentier|hameau|parvis|esplanade|street|st\.|road|rd\.|lane|drive|way"
)
_ADDRESS_RE = re.compile(
    r"\b\d{1,4}(?:\s?(?:bis|ter|quater|[a-dA-D]))?,?\s+(?:" + _STREET_TYPES + r")\s+"
    r"[A-Za-zÀ-ÖØ-öø-ÿ'’\- ]{2,60}"
    r"(?:,?\s+\d{5}(?:\s+[A-ZÀ-Ö][A-Za-zÀ-ÖØ-öø-ÿ'’\- ]{1,40}[A-Za-zÀ-ÖØ-öø-ÿ])?)?(?=[\s,.;:)\]]|$)",
    re.IGNORECASE,
)

_CARD_PREFIXES = re.compile(r"^(4|5[1-5]|2(2[2-9]|[3-6]\d|7[01]|720)|3[47]|6011|65|64[4-9]|35|30[0-5]|36|38|62)")


def _digits(value: str) -> str:
    return re.sub(r"\D", "", value)


class RulesDetector:
    """Expressions régulières et validateurs (python-stdnum, phonenumbers). Aucune dépendance à un modèle."""

    name = "rules"
    uses_model = False

    def __init__(self, default_region: str = "FR") -> None:
        self.default_region = default_region

    def detect(self, text: str, ctx: DetectionContext) -> list[Span]:
        spans: list[Span] = []
        spans += self._emails(text)
        spans += self._ibans(text)
        spans += self._nirs(text)
        spans += self._cards(text)
        spans += self._company_ids(text)
        spans += self._phones(text)
        spans += self._ips(text)
        spans += self._plates(text)
        spans += self._birth_dates(text)
        if not ctx.code_mode:
            spans += self._addresses(text)
        return spans

    def _emails(self, text: str) -> list[Span]:
        return [Span(m.start(), m.end(), Label.EMAIL, 0.99, self.name, True) for m in _EMAIL_RE.finditer(text)]

    def _ibans(self, text: str) -> list[Span]:
        spans = []
        for m in _IBAN_RE.finditer(text):
            value = m.group(0).replace(" ", "")
            if std_iban.is_valid(value):
                spans.append(Span(m.start(), m.end(), Label.IBAN, 0.99, self.name, True))
        return spans

    def _nirs(self, text: str) -> list[Span]:
        spans = []
        for m in _NIR_RE.finditer(text):
            value = re.sub(r"[ .]", "", m.group(0))
            if std_nir.is_valid(value):
                spans.append(Span(m.start(), m.end(), Label.NIR, 0.99, self.name, True))
        return spans

    def _cards(self, text: str) -> list[Span]:
        spans = []
        for m in _CARD_RE.finditer(text):
            digits = _digits(m.group(0))
            if len(digits) not in (13, 15, 16, 19) or not _CARD_PREFIXES.match(digits):
                continue
            if luhn.is_valid(digits):
                spans.append(Span(m.start(), m.end(), Label.CARTE_BANCAIRE, 0.97, self.name, True))
        return spans

    def _company_ids(self, text: str) -> list[Span]:
        spans = []
        for regex, label, size in ((_SIRET_RE, Label.SIRET, 14), (_SIREN_RE, Label.SIREN, 9)):
            for m in regex.finditer(text):
                digits = _digits(m.group(0))
                if len(digits) != size or not luhn.is_valid(digits):
                    continue
                window = text[max(0, m.start() - 40) : m.start()]
                if _COMPANY_CONTEXT_RE.search(window):
                    spans.append(Span(m.start(), m.end(), label, 0.95, self.name, True))
        return spans

    def _phones(self, text: str) -> list[Span]:
        spans = []
        matcher = phonenumbers.PhoneNumberMatcher(text, self.default_region, leniency=phonenumbers.Leniency.VALID)
        for match in matcher:
            spans.append(Span(match.start, match.end, Label.TELEPHONE, 0.95, self.name, True))
        for m in _FR_PHONE_RE.finditer(text):
            if not any(m.start() < s.end and s.start < m.end() for s in spans):
                spans.append(Span(m.start(), m.end(), Label.TELEPHONE, 0.85, self.name))
        return spans

    def _ips(self, text: str) -> list[Span]:
        spans = []
        for m in _IPV4_RE.finditer(text):
            if _VERSION_CONTEXT_RE.search(text[max(0, m.start() - 10) : m.start()]):
                continue
            if ipaddress.ip_address(m.group(0)).is_global:
                spans.append(Span(m.start(), m.end(), Label.IP, 0.9, self.name, True))
        for m in _IPV6_RE.finditer(text):
            try:
                address = ipaddress.ip_address(m.group(0))
            except ValueError:
                continue
            if address.version == 6 and address.is_global:
                spans.append(Span(m.start(), m.end(), Label.IP, 0.9, self.name, True))
        return spans

    def _plates(self, text: str) -> list[Span]:
        spans = [Span(m.start(), m.end(), Label.PLAQUE, 0.85, self.name) for m in _PLATE_RE.finditer(text)]
        for m in _PLATE_BARE_RE.finditer(text):
            if _PLATE_CONTEXT_RE.search(text[max(0, m.start() - 40) : m.start()]):
                spans.append(Span(m.start(), m.end(), Label.PLAQUE, 0.8, self.name))
        return spans

    def _birth_dates(self, text: str) -> list[Span]:
        spans = []
        for m in _DATE_RE.finditer(text):
            if _BIRTH_CONTEXT_RE.search(text[max(0, m.start() - 40) : m.start()]):
                spans.append(Span(m.start(), m.end(), Label.DATE_NAISSANCE, 0.9, self.name))
        return spans

    def _addresses(self, text: str) -> list[Span]:
        spans = []
        for m in _ADDRESS_RE.finditer(text):
            value = m.group(0).rstrip(" ,.")
            spans.append(Span(m.start(), m.start() + len(value), Label.ADRESSE, 0.85, self.name))
        return spans
