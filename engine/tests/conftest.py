# @spec docs/BACKLOG.md#RG-017 | docs/DAT.md#donnees
# @verifies docs/BACKLOG.md#RG-002 | docs/BACKLOG.md#RG-003 | docs/BACKLOG.md#RG-004 | docs/BACKLOG.md#RG-005 | docs/BACKLOG.md#RG-006
"""Fixtures partagées : moteur sans modèles, données synthétiques à somme de contrôle valide, payloads réels."""

from __future__ import annotations

import json
import random
import string
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from stdnum import iban as std_iban
from stdnum import luhn
from stdnum.fr import nir as std_nir

from rgpd_guard.api import create_app
from rgpd_guard.config import Settings
from rgpd_guard.service import Engine

FIXTURES = Path(__file__).parent / "fixtures" / "hooks"
TOKEN = "jeton-de-test-0123456789"


def load_fixture(name: str) -> dict[str, Any]:
    data: dict[str, Any] = json.loads((FIXTURES / f"{name}.json").read_text(encoding="utf-8"))
    return data


def make_nir(seed: int = 1) -> str:
    rnd = random.Random(seed)
    body = f"{rnd.choice('12')}{rnd.randint(40, 99):02d}{rnd.randint(1, 12):02d}75{rnd.randint(100, 999)}{rnd.randint(100, 999)}"
    return body + std_nir.calc_check_digits(body)


def make_siret(seed: int = 1) -> str:
    rnd = random.Random(seed)
    base = "".join(rnd.choice(string.digits) for _ in range(13))
    return base + luhn.calc_check_digit(base)


def make_siren(seed: int = 1) -> str:
    rnd = random.Random(seed)
    base = "".join(rnd.choice(string.digits) for _ in range(8))
    return base + luhn.calc_check_digit(base)


def make_iban(seed: int = 1) -> str:
    rnd = random.Random(seed)
    bban = "".join(rnd.choice(string.digits) for _ in range(23))
    check = std_iban.calc_check_digits("FR00" + bban)
    return f"FR{check}{bban}"


def make_card(prefix: str = "4", length: int = 16, seed: int = 1) -> str:
    rnd = random.Random(seed)
    base = prefix + "".join(rnd.choice(string.digits) for _ in range(length - len(prefix) - 1))
    return base + luhn.calc_check_digit(base)


def make_github_token(seed: int = 1) -> str:
    rnd = random.Random(seed)
    return "gh" + "p_" + "".join(rnd.choice(string.ascii_letters + string.digits) for _ in range(36))


def make_aws_key(seed: int = 1) -> str:
    rnd = random.Random(seed)
    return "AK" + "IA" + "".join(rnd.choice(string.ascii_uppercase + string.digits) for _ in range(16))


def make_private_key() -> str:
    head = "-----" + "BEGIN " + "RSA PRIVATE KEY" + "-----"
    tail = "-----" + "END " + "RSA PRIVATE KEY" + "-----"
    return f"{head}\nMIIEowIBAAKCAQEAuFAKEfakeFAKEfake0123456789abcdef\n{tail}"


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    return Settings(
        env="test",
        token=TOKEN,
        hmac_key="cle-hmac-de-test",
        data_dir=tmp_path / "data",
        enabled_detectors="rules,secrets",
        profile="rapide",
        allowed_hosts="testserver,127.0.0.1,localhost",
        cors_origins="http://127.0.0.1:8743",
        workspace_root=workspace,
    )


@pytest.fixture
def engine(settings: Settings) -> Iterator[Engine]:
    eng = Engine(settings)
    yield eng
    eng.store.close()


@pytest.fixture
def client(settings: Settings) -> Iterator[TestClient]:
    with TestClient(create_app(settings)) as test_client:
        yield test_client


@pytest.fixture
def auth_headers() -> dict[str, str]:
    return {"X-RGPD-Guard-Token": TOKEN}


@pytest.fixture
def logged_client(client: TestClient) -> TestClient:
    response = client.post("/v1/auth/session", json={"token": TOKEN})
    assert response.status_code == 200
    return client
