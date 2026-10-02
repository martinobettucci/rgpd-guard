# @spec docs/BACKLOG.md#RG-004 | docs/DAT.md#pseudonymisation
# @verifies docs/BACKLOG.md#RG-004 | docs/DAT.md#pseudonymisation
"""Coffre et pseudonymisation : stabilité des jetons, aller-retour exact, expiration, concurrence."""

from __future__ import annotations

import threading

from rgpd_guard.models import Action, Finding, Span
from rgpd_guard.pseudonymizer import pseudonymize, rehydrate
from rgpd_guard.taxonomy import Label
from rgpd_guard.vault import Vault


class FakeClock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


def finding(text: str, value: str, label: Label) -> Finding:
    start = text.index(value)
    return Finding(Span(start, start + len(value), label, 0.99, "rules", True), value, Action.BLOCK)


def test_same_value_same_token_and_numbering_per_type() -> None:
    vault = Vault(3600)
    assert vault.token_for("s", Label.EMAIL, "a@b.fr") == "⟦EMAIL_1⟧"
    assert vault.token_for("s", Label.EMAIL, "c@d.fr") == "⟦EMAIL_2⟧"
    assert vault.token_for("s", Label.EMAIL, "a@b.fr") == "⟦EMAIL_1⟧"
    assert vault.token_for("s", Label.IBAN, "FR76") == "⟦IBAN_1⟧"
    assert vault.token_for("autre", Label.EMAIL, "c@d.fr") == "⟦EMAIL_1⟧"


def test_round_trip_is_exact() -> None:
    vault = Vault(3600)
    text = "Écrire à Camille.Martin@laposte.net ou au 06 12 34 56 78."
    findings = [
        finding(text, "Camille.Martin@laposte.net", Label.EMAIL),
        finding(text, "06 12 34 56 78", Label.TELEPHONE),
    ]
    masked = pseudonymize(text, findings, vault, "s")
    assert "laposte" not in masked and "⟦EMAIL_1⟧" in masked
    restored = rehydrate(masked, vault, "s")
    assert restored.text == text and restored.replaced == 2 and restored.unknown == []


def test_unknown_token_reported() -> None:
    vault = Vault(3600)
    result = rehydrate("bonjour ⟦EMAIL_9⟧", vault, "s")
    assert result.unknown == ["⟦EMAIL_9⟧"] and result.replaced == 0


def test_expiration() -> None:
    clock = FakeClock()
    vault = Vault(60, clock=clock)
    token = vault.token_for("s", Label.EMAIL, "a@b.fr")
    clock.now += 61
    assert vault.purge_expired() == 1
    assert vault.value_for("s", token) is None


def test_stats_expose_no_value() -> None:
    vault = Vault(3600)
    vault.token_for("s", Label.EMAIL, "secret@exemple.fr")
    assert vault.stats() == {"sessions": 1, "tokens": 1}


def test_concurrent_numbering_is_consistent() -> None:
    vault = Vault(3600)
    tokens: list[str] = []
    lock = threading.Lock()

    def worker(i: int) -> None:
        token = vault.token_for("s", Label.EMAIL, f"user{i % 20}@exemple.fr")
        with lock:
            tokens.append(token)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(200)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert len(set(tokens)) == 20
