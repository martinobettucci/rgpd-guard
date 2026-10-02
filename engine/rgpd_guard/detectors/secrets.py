# @spec docs/BACKLOG.md#RG-003 | docs/DAT.md#moteur
"""Détecteur de secrets : préfixes de fournisseurs connus, clés PEM, JWT, affectations à forte entropie.

Les motifs à préfixe s'inspirent des règles publiques de gitleaks (licence MIT).
"""

from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass

from ..models import DetectionContext, Span
from ..taxonomy import Label


@dataclass(frozen=True)
class SecretRule:
    name: str
    pattern: re.Pattern[str]
    group: int = 0
    score: float = 0.97


_RULES: tuple[SecretRule, ...] = (
    SecretRule(
        "cle-privee-pem",
        re.compile(
            r"-----BEGIN[A-Z ]{0,30}PRIVATE KEY(?: BLOCK)?-----(?:[\s\S]{0,20000}?-----END[A-Z ]{0,30}PRIVATE KEY(?: BLOCK)?-----)?"
        ),
        score=0.99,
    ),
    SecretRule("aws-cle-acces", re.compile(r"\b(?:A3T[A-Z0-9]|AKIA|ASIA|ABIA|ACCA)[A-Z0-9]{16}\b")),
    SecretRule("github-jeton", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36,255}\b")),
    SecretRule("github-jeton-fin", re.compile(r"\bgithub_pat_[A-Za-z0-9_]{60,255}\b")),
    SecretRule("gitlab-jeton", re.compile(r"\bglpat-[A-Za-z0-9_-]{20,}\b")),
    SecretRule("slack-jeton", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,72}\b")),
    SecretRule("slack-webhook", re.compile(r"https://hooks\.slack\.com/services/[A-Za-z0-9/_-]{20,}")),
    SecretRule("stripe-cle", re.compile(r"\b(?:sk|rk)_(?:live|test)_[A-Za-z0-9]{16,99}\b")),
    SecretRule("openai-cle", re.compile(r"\bsk-(?:proj|svcacct|admin)-[A-Za-z0-9_-]{40,}\b")),
    SecretRule("anthropic-cle", re.compile(r"\bsk-ant-(?:api|admin|oat)\d{2}-[A-Za-z0-9_-]{40,}\b")),
    SecretRule("google-cle-api", re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b")),
    SecretRule("google-secret-oauth", re.compile(r"\bGOCSPX-[A-Za-z0-9_-]{28}\b")),
    SecretRule("huggingface-jeton", re.compile(r"\bhf_[A-Za-z]{34}\b")),
    SecretRule("npm-jeton", re.compile(r"\bnpm_[A-Za-z0-9]{36}\b")),
    SecretRule("pypi-jeton", re.compile(r"\bpypi-AgEIcHlwaS5vcmc[A-Za-z0-9_-]{50,}\b")),
    SecretRule("sendgrid-cle", re.compile(r"\bSG\.[A-Za-z0-9_-]{22}\.[A-Za-z0-9_-]{43}\b")),
    SecretRule("azure-cle-stockage", re.compile(r"AccountKey=([A-Za-z0-9+/=]{80,100})"), group=1),
    SecretRule(
        "jwt",
        re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b"),
        score=0.95,
    ),
    SecretRule(
        "url-identifiants",
        re.compile(r"\b[a-z][a-z0-9+.-]{1,20}://[^\s:/@]{1,64}:([^\s@/]{3,128})@[^\s/]+"),
        group=1,
        score=0.95,
    ),
)

_ASSIGNMENT_RE = re.compile(
    r"(?i)(?<![A-Za-z0-9])(password|passwd|pwd|mot[_ ]de[_ ]passe|secret|api[_-]?key|apikey|access[_-]?key|"
    r"auth[_-]?token|access[_-]?token|refresh[_-]?token|token|client[_-]?secret|private[_-]?key|bearer)"
    r"[\"']?\s*(?:[:=]|=>|:=|\s)\s*[\"']?([^\s\"'`,;<>{}()]{8,200})"
)
_URL_PARAM_RE = re.compile(
    r"(?i)[?&](token|key|api_?key|access_token|secret|password|pwd|sig|signature|auth|code)=([^&\s#\"']{8,})"
)
_PLACEHOLDER_RE = re.compile(
    r"(?i)^(x{3,}|\*{3,}|\.{3,}|changeme|change_me|password|secret|example|exemple|dummy|placeholder|redacted|"
    r"your[_-]?.*|<.*>|\$\{.*\}|\{\{.*\}\}|%\(.*\)s|null|none|undefined|true|false|test\w*|mock\w*|fake\w*)$"
)
_TOKEN_CHARS = "\u27e6"  # noqa: S105 (début de jeton)


def shannon_entropy(value: str) -> float:
    counts = Counter(value)
    total = len(value)
    return -sum((c / total) * math.log2(c / total) for c in counts.values())


def _looks_secret(value: str) -> bool:
    if _TOKEN_CHARS in value or _PLACEHOLDER_RE.match(value):
        return False
    if value.isdigit() or value.isalpha() and value.islower():
        return False
    classes = sum((any(c.islower() for c in value), any(c.isupper() for c in value), any(c.isdigit() for c in value)))
    return shannon_entropy(value) >= 3.0 and classes >= 2


class SecretsDetector:
    name = "secrets"
    uses_model = False

    def detect(self, text: str, ctx: DetectionContext) -> list[Span]:
        spans: list[Span] = []
        for rule in _RULES:
            for m in rule.pattern.finditer(text):
                spans.append(Span(m.start(rule.group), m.end(rule.group), Label.SECRET, rule.score, self.name, True))
        for regex, score in ((_ASSIGNMENT_RE, 0.8), (_URL_PARAM_RE, 0.85)):
            for m in regex.finditer(text):
                value = m.group(2)
                start, end = m.start(2), m.end(2)
                if any(start < s.end and s.start < end for s in spans):
                    continue  # déjà couvert par une règle à préfixe connu
                if _looks_secret(value):
                    spans.append(Span(start, end, Label.SECRET, score, self.name))
        return spans
