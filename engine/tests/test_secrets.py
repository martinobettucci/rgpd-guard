# @spec docs/BACKLOG.md#RG-003 | docs/DAT.md#moteur
# @verifies docs/BACKLOG.md#RG-003 | docs/DAT.md#moteur
"""Détecteur de secrets : préfixes connus, clés PEM, affectations, faux positifs courants."""

from __future__ import annotations

import pytest

from conftest import make_aws_key, make_github_token, make_private_key
from rgpd_guard.detectors.secrets import SecretsDetector
from rgpd_guard.models import DetectionContext

DETECTOR = SecretsDetector()


def values(text: str) -> list[str]:
    return [text[s.start : s.end] for s in DETECTOR.detect(text, DetectionContext())]


def test_prefixed_tokens() -> None:
    gh = make_github_token(1)
    aws = make_aws_key(2)
    assert values(f"export GITHUB_TOKEN={gh}") == [gh]
    assert aws in values(f"aws_access_key_id = {aws}")


def test_private_key_block_is_one_span() -> None:
    key = make_private_key()
    found = values(f"voici la clé :\n{key}\nfin")
    assert found == [key]


def test_assignment_with_entropy() -> None:
    assert values('DB_PASSWORD="Xk9#pL2v!Qz7"') == ["Xk9#pL2v!Qz7"]


def test_connection_string_password() -> None:
    assert values("postgres://app:S3cr3tPassw0rd@db.internal:5432/app") == ["S3cr3tPassw0rd"]


@pytest.mark.parametrize(
    "text",
    [
        "password = changeme",
        "password: ${DB_PASSWORD}",
        "token = <votre-jeton>",
        "secret = xxxxxxxxxx",
        "commit 3f786850e387550fdab836ed7e6dc881de23001b",
        "id 123e4567-e89b-12d3-a456-426614174000",
        "token = ⟦SECRET_1⟧",
    ],
)
def test_common_false_positives(text: str) -> None:
    assert values(text) == []
