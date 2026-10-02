# @spec docs/BACKLOG.md#RG-005 | docs/BACKLOG.md#RG-006 | docs/DAT.md#flux | docs/DAT.md#flux-hooks
# @verifies docs/BACKLOG.md#RG-005 | docs/BACKLOG.md#RG-006 | docs/BACKLOG.md#RG-011 | docs/DAT.md#flux
"""Adaptateurs de hooks sur les payloads réels capturés (M1)."""

from __future__ import annotations

import copy
import sqlite3
from pathlib import Path

from conftest import load_fixture, make_github_token, make_iban
from rgpd_guard.service import Engine
from rgpd_guard.taxonomy import Label

CANARY_IBAN = "FR7630006000011234567890189"


def test_prompt_with_iban_is_blocked_with_proposal(engine: Engine) -> None:
    out = engine.hooks.handle("user-prompt-submit", load_fixture("user_prompt_submit"))
    assert out["decision"] == "block"
    assert out["hookSpecificOutput"] == {"hookEventName": "UserPromptSubmit", "suppressOriginalPrompt": True}
    assert "mon IBAN ⟦IBAN_1⟧" in out["reason"]
    assert CANARY_IBAN not in out["reason"]


def test_clean_prompt_passes(engine: Engine) -> None:
    payload = load_fixture("user_prompt_submit") | {"prompt": "Explique-moi le RGPD en trois points."}
    assert engine.hooks.handle("user-prompt-submit", payload) == {}


def test_bypass_prefix_allows_but_never_for_secrets(engine: Engine) -> None:
    base = load_fixture("user_prompt_submit")
    allowed = engine.hooks.handle("user-prompt-submit", base | {"prompt": f"#rgpd-ok mon IBAN {make_iban(2)}"})
    assert "decision" not in allowed and "contournement" in allowed["systemMessage"]
    blocked = engine.hooks.handle("user-prompt-submit", base | {"prompt": f"#rgpd-ok token={make_github_token(3)}"})
    assert blocked["decision"] == "block" and "jamais aux secrets" in blocked["reason"]


def test_at_mention_resolved_in_workspace(engine: Engine, settings) -> None:  # type: ignore[no-untyped-def]
    workspace: Path = settings.workspace_root
    (workspace / "clients.txt").write_text(f"IBAN {make_iban(4)}\n", encoding="utf-8")
    (workspace / "notes.md").write_text("rien de sensible\n", encoding="utf-8")
    base = load_fixture("user_prompt_submit_at_mention") | {"cwd": str(workspace)}
    blocked = engine.hooks.handle("user-prompt-submit", base | {"prompt": "résume @clients.txt"})
    assert blocked["decision"] == "block" and "@clients.txt" in blocked["reason"]
    assert engine.hooks.handle("user-prompt-submit", base | {"prompt": "résume @notes.md"}) == {}
    assert engine.hooks.handle("user-prompt-submit", base | {"prompt": "merci @camille pour l'aide"}) == {}
    out_of_reach = engine.hooks.handle("user-prompt-submit", base | {"prompt": "résume @/etc/hostname"})
    assert out_of_reach["decision"] == "block" and "hors du dossier" in out_of_reach["reason"]


def test_read_of_secret_file_denied(engine: Engine) -> None:
    payload = load_fixture("pre_tool_use_read")
    payload["tool_input"] = {"file_path": "/projet/.env"}
    out = engine.hooks.handle("pre-tool-use", payload)
    assert out["hookSpecificOutput"]["permissionDecision"] == "deny"
    payload["tool_input"] = {"file_path": "/projet/.env.example"}
    assert engine.hooks.handle("pre-tool-use", payload) == {}


def test_edit_rehydrated_without_permission_decision(engine: Engine) -> None:
    payload = load_fixture("pre_tool_use_edit")
    engine.vault.token_for(payload["session_id"], Label.EMAIL, "camille.martin@laposte.net")
    out = engine.hooks.handle("pre-tool-use", payload)
    specific = out["hookSpecificOutput"]
    assert "permissionDecision" not in specific
    assert specific["updatedInput"]["new_string"] == "Contact: camille.martin@laposte.net\nIBAN:"
    assert specific["updatedInput"]["file_path"] == payload["tool_input"]["file_path"]


def test_unknown_token_denied(engine: Engine) -> None:
    out = engine.hooks.handle("pre-tool-use", load_fixture("pre_tool_use_edit"))
    assert out["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert "inconnu" in out["hookSpecificOutput"]["permissionDecisionReason"]


def test_bash_never_rehydrated(engine: Engine) -> None:
    payload = load_fixture("pre_tool_use_read") | {"tool_name": "Bash", "tool_input": {"command": "echo ⟦EMAIL_1⟧"}}
    engine.vault.token_for(payload["session_id"], Label.EMAIL, "camille.martin@laposte.net")
    assert engine.hooks.handle("pre-tool-use", payload) == {}


def test_read_output_pseudonymized_with_same_shape(engine: Engine) -> None:
    payload = load_fixture("post_tool_use_read")
    out = engine.hooks.handle("post-tool-use", payload)
    updated = out["hookSpecificOutput"]["updatedToolOutput"]
    original = payload["tool_response"]
    assert updated.keys() == original.keys() and updated["file"].keys() == original["file"].keys()
    assert updated["file"]["filePath"] == original["file"]["filePath"]
    assert updated["file"]["numLines"] == original["file"]["numLines"]
    assert "canari.unique@example.org" in updated["file"]["content"]  # domaine de documentation autorisé
    assert CANARY_IBAN not in updated["file"]["content"] and "⟦IBAN_1⟧" in updated["file"]["content"]
    assert "jetons" in out["hookSpecificOutput"]["additionalContext"]


def test_bash_output_pseudonymized(engine: Engine) -> None:
    out = engine.hooks.handle("post-tool-use", load_fixture("post_tool_use_bash"))
    updated = out["hookSpecificOutput"]["updatedToolOutput"]
    assert CANARY_IBAN not in updated["stdout"] and updated["interrupted"] is False


def test_write_tools_skipped(engine: Engine) -> None:
    assert engine.hooks.handle("post-tool-use", load_fixture("post_tool_use_write")) == {}
    assert engine.hooks.handle("post-tool-use", load_fixture("post_tool_use_edit")) == {}


def test_batch_blocks_residual_and_passes_masked(engine: Engine) -> None:
    raw = load_fixture("post_tool_batch_bash_failure")
    out = engine.hooks.handle("post-tool-batch", raw)
    assert out["decision"] == "block" and "/rewind" in out["reason"] and CANARY_IBAN not in out["reason"]
    masked = copy.deepcopy(raw)
    masked["tool_calls"][0]["tool_response"] = "Exit code 3\nIBAN: ⟦IBAN_1⟧"
    assert engine.hooks.handle("post-tool-batch", masked) == {}


def test_failure_recorded_as_leak(engine: Engine) -> None:
    engine.hooks.handle("post-tool-use-failure", load_fixture("post_tool_use_failure_bash"))
    events, _ = engine.store.list_events(decision="leak")
    assert events and events[0]["event"] == "post_tool_use_failure"


def test_session_start_guidance_and_degraded_warning(engine: Engine) -> None:
    out = engine.hooks.handle("session-start", load_fixture("session_start"), "equilibre")
    assert "⟦TYPE_N⟧" in out["hookSpecificOutput"]["additionalContext"]
    assert "spacy" in out["systemMessage"]
    sub = engine.hooks.handle("subagent-start", load_fixture("subagent_start"), "rapide")
    assert sub["hookSpecificOutput"]["hookEventName"] == "SubagentStart" and "systemMessage" not in sub


def test_audit_never_stores_raw_values(engine: Engine, settings) -> None:  # type: ignore[no-untyped-def]
    engine.hooks.handle("user-prompt-submit", load_fixture("user_prompt_submit"))
    engine.hooks.handle("post-tool-use", load_fixture("post_tool_use_read"))
    engine.store.close()
    db = settings.data_dir / "rgpd-guard.db"
    dump = "\n".join(sqlite3.connect(db).iterdump())
    assert CANARY_IBAN not in dump and "CANARI-PERSONNE" not in dump
