# @spec docs/BACKLOG.md#RG-005 | docs/BACKLOG.md#RG-006 | docs/BACKLOG.md#RG-001 | docs/DAT.md#flux
# @verifies docs/BACKLOG.md#RG-001 | docs/BACKLOG.md#RG-005 | docs/BACKLOG.md#RG-006 | docs/DAT.md#flux
"""E2E Claude Code réel + plugin + moteur réel : aucune valeur canari n'atteint le faux serveur API."""

from __future__ import annotations

import random
import string
from collections.abc import Iterator
from pathlib import Path

import pytest
from stdnum import iban as std_iban

from harness import Engine, run_claude, start_engine, text, tool_use

pytestmark = pytest.mark.e2e


def canary_iban(seed: int) -> str:
    rnd = random.Random(seed)  # noqa: S311 (données de test)
    bban = "".join(rnd.choice(string.digits) for _ in range(23))
    return f"FR{std_iban.calc_check_digits('FR00' + bban)}{bban}"


CANARY_EMAIL = "camille.canari@courriel-fictif.fr"
CANARY_PHONE = "06 39 98 12 34"


@pytest.fixture(scope="module")
def workspace(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return tmp_path_factory.mktemp("espace")


@pytest.fixture(scope="module")
def engine(tmp_path_factory: pytest.TempPathFactory, workspace: Path) -> Iterator[Engine]:
    eng = start_engine(tmp_path_factory.mktemp("moteur"), workspace)
    yield eng
    eng.stop()


def test_sensitive_prompt_never_reaches_api(engine: Engine, workspace: Path, tmp_path: Path) -> None:
    iban = canary_iban(1)
    result = run_claude(tmp_path, workspace, f"Vire 100 euros sur {iban} stp", [[text("ok")]], engine.url)
    assert result.messages_bodies == []
    assert "RGPD Guard a bloqué ce prompt" in result.result_text
    assert "⟦IBAN_1⟧" in result.result_text and iban not in result.result_text


def test_read_output_is_pseudonymized(engine: Engine, workspace: Path, tmp_path: Path) -> None:
    iban = canary_iban(2)
    target = workspace / "client.txt"
    target.write_text(f"Contact : {CANARY_EMAIL}\nTel : {CANARY_PHONE}\nIBAN : {iban}\n", encoding="utf-8")
    steps = [[tool_use("Read", {"file_path": str(target)})], [text("Lu.")]]
    result = run_claude(tmp_path, workspace, "lis client.txt", steps, engine.url)
    assert len(result.messages_bodies) == 2
    for canary in (iban, CANARY_EMAIL, CANARY_PHONE):
        assert not result.sent(canary), canary
    assert result.sent("⟦IBAN_1⟧") and result.sent("⟦EMAIL_1⟧")


def test_edit_is_rehydrated_on_disk(engine: Engine, workspace: Path, tmp_path: Path) -> None:
    target = workspace / "fiche.txt"
    target.write_text(f"Email : {CANARY_EMAIL}\nStatut : prospect\n", encoding="utf-8")
    steps = [
        [tool_use("Read", {"file_path": str(target)})],
        [
            tool_use(
                "Edit",
                {
                    "file_path": str(target),
                    "old_string": "Statut : prospect",
                    "new_string": "Statut : client\nRelance : ⟦EMAIL_1⟧",
                },
            )
        ],
        [text("Fait.")],
    ]
    result = run_claude(tmp_path, workspace, "passe la fiche en client", steps, engine.url)
    assert target.read_text(encoding="utf-8") == f"Email : {CANARY_EMAIL}\nStatut : client\nRelance : {CANARY_EMAIL}\n"
    assert not result.sent(CANARY_EMAIL)


def test_failed_command_output_stopped_by_batch_guard(engine: Engine, workspace: Path, tmp_path: Path) -> None:
    iban = canary_iban(3)
    target = workspace / "virements.txt"
    target.write_text(f"IBAN {iban}\n", encoding="utf-8")
    steps = [[tool_use("Bash", {"command": f"cat {target}; exit 3", "description": "lecture"})], [text("ok")]]
    result = run_claude(tmp_path, workspace, "affiche les virements", steps, engine.url)
    assert len(result.messages_bodies) == 1 and not result.sent(iban)


def test_at_mention_with_sensitive_file_blocked(engine: Engine, workspace: Path, tmp_path: Path) -> None:
    iban = canary_iban(4)
    (workspace / "rib.txt").write_text(f"IBAN {iban}\n", encoding="utf-8")
    result = run_claude(tmp_path, workspace, "résume @rib.txt", [[text("ok")]], engine.url)
    assert result.messages_bodies == [] and "@rib.txt" in result.result_text


def test_secret_file_read_denied(engine: Engine, workspace: Path, tmp_path: Path) -> None:
    env_file = workspace / ".env"
    env_file.write_text("DB_PASSWORD=Zq8!vL3#pW9x\n", encoding="utf-8")
    steps = [[tool_use("Read", {"file_path": str(env_file)})], [text("ok")]]
    result = run_claude(tmp_path, workspace, "lis le .env", steps, engine.url)
    assert not result.sent("Zq8!vL3#pW9x") and result.sent("fichier de secrets")


def test_engine_down_fails_closed(workspace: Path, tmp_path: Path) -> None:
    result = run_claude(tmp_path, workspace, "bonjour", [[text("ok")]], engine_url=None)
    assert result.messages_bodies == [] and "moteur injoignable" in result.result_text
