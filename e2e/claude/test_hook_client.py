# @spec docs/BACKLOG.md#RG-001 | docs/DAT.md#client-hook | docs/DAT.md#flux-hooks
# @verifies docs/BACKLOG.md#RG-001 | docs/DAT.md#client-hook | docs/DAT.md#flux-hooks
"""Contrat du client de hook `guard-hook.sh` : relais fidèle, repli fail-closed et fail-open, jeton protégé."""

from __future__ import annotations

import json
import os
import subprocess
import threading
import time
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "plugins" / "rgpd-guard" / "scripts" / "guard-hook.sh"
TOKEN = "jeton-contrat-0123"


class StubState:
    mode = "ok"
    seen_headers: dict[str, str] = {}
    seen_body = b""
    seen_path = ""


def make_server(state: StubState) -> ThreadingHTTPServer:
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_: Any) -> None:
            return

        def do_POST(self) -> None:  # noqa: N802
            state.seen_headers = {k: v for k, v in self.headers.items()}
            state.seen_body = self.rfile.read(int(self.headers.get("Content-Length", "0")))
            state.seen_path = self.path
            if state.mode == "slow":
                time.sleep(3)
            if state.mode == "error":
                self.send_response(500)
                self.end_headers()
                return
            body = b"<html>pas du JSON</html>" if state.mode == "garbage" else b'{"decision":"block","reason":"ok"}'
            self.send_response(200)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    return ThreadingHTTPServer(("127.0.0.1", 0), Handler)


@pytest.fixture
def stub() -> Iterator[tuple[StubState, str]]:
    state = StubState()
    server = make_server(state)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield state, f"http://127.0.0.1:{server.server_address[1]}"
    server.shutdown()


def run_hook(event: str, url: str, payload: dict[str, Any], max_time: str = "2", **env: str) -> dict[str, Any]:
    base = {
        "PATH": os.environ["PATH"],
        "HOME": "/nonexistent",
        "RGPD_GUARD_URL": url,
        "RGPD_GUARD_TOKEN": TOKEN,
        "RGPD_GUARD_CONFIG": "/nonexistent/engine.env",
    }
    base.update(env)
    completed = subprocess.run(  # noqa: S603
        ["sh", str(SCRIPT), event, max_time],  # noqa: S607
        input=json.dumps(payload).encode(),
        capture_output=True,
        env=base,
        timeout=20,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    result: dict[str, Any] = json.loads(completed.stdout)
    return result


def test_relays_payload_and_response(stub: tuple[StubState, str]) -> None:
    state, url = stub
    payload = {"hook_event_name": "UserPromptSubmit", "prompt": "bonjour été"}
    out = run_hook("user-prompt-submit", url, payload, CLAUDE_PLUGIN_OPTION_PROFILE="max")
    assert out == {"decision": "block", "reason": "ok"}
    assert state.seen_path == "/v1/hooks/user-prompt-submit"
    assert json.loads(state.seen_body) == payload
    assert state.seen_headers["X-RGPD-Guard-Token"] == TOKEN
    assert state.seen_headers["X-RGPD-Guard-Profile"] == "max"


def test_plugin_options_override_environment(stub: tuple[StubState, str]) -> None:
    state, url = stub
    run_hook("pre-tool-use", "http://127.0.0.1:9", {}, CLAUDE_PLUGIN_OPTION_ENGINE_URL=url)
    assert state.seen_path == "/v1/hooks/pre-tool-use"


def test_config_file_used_when_nothing_else(stub: tuple[StubState, str], tmp_path: Path) -> None:
    state, url = stub
    config = tmp_path / "engine.env"
    config.write_text(f"RGPD_GUARD_URL={url}\nRGPD_GUARD_TOKEN=depuis-fichier\n", encoding="utf-8")
    env = {"PATH": os.environ["PATH"], "HOME": str(tmp_path), "RGPD_GUARD_CONFIG": str(config)}
    completed = subprocess.run(  # noqa: S603
        ["sh", str(SCRIPT), "session-start", "2"],  # noqa: S607
        input=b"{}",
        capture_output=True,
        env=env,
        timeout=20,
        check=False,
    )
    assert completed.returncode == 0 and state.seen_headers["X-RGPD-Guard-Token"] == "depuis-fichier"


@pytest.mark.parametrize("mode", ["error", "garbage", "slow", "down"])
def test_fail_closed_blocks_prompt_and_tools(stub: tuple[StubState, str], mode: str) -> None:
    state, url = stub
    state.mode = mode
    target = "http://127.0.0.1:9" if mode == "down" else url
    prompt = run_hook("user-prompt-submit", target, {"prompt": "x"}, max_time="1")
    assert prompt["decision"] == "block" and "moteur injoignable" in prompt["reason"]
    tool = run_hook("pre-tool-use", target, {}, max_time="1")
    assert tool["hookSpecificOutput"]["permissionDecision"] == "deny"
    batch = run_hook("post-tool-batch", target, {}, max_time="1")
    assert batch["decision"] == "block"
    start = run_hook("session-start", target, {}, max_time="1")
    assert "systemMessage" in start


def test_fail_open_only_warns() -> None:
    out = run_hook("user-prompt-submit", "http://127.0.0.1:9", {}, max_time="1", CLAUDE_PLUGIN_OPTION_FAIL_MODE="open")
    assert "decision" not in out and "injoignable" in out["systemMessage"]


def test_missing_token_fails_closed(stub: tuple[StubState, str]) -> None:
    _, url = stub
    out = run_hook("user-prompt-submit", url, {}, RGPD_GUARD_TOKEN="")
    assert out["decision"] == "block" and "jeton absent" in out["reason"]


def test_token_not_in_process_arguments(stub: tuple[StubState, str], tmp_path: Path) -> None:
    """Un curl intermédiaire enregistre ses arguments : le jeton ne doit jamais y figurer."""
    state, url = stub
    real_curl = subprocess.run(
        ["sh", "-c", "command -v curl"], capture_output=True, text=True, check=True
    ).stdout.strip()  # noqa: S607
    argv_log = tmp_path / "argv.txt"
    wrapper = tmp_path / "bin" / "curl"
    wrapper.parent.mkdir()
    wrapper.write_text(f'#!/bin/sh\nprintf "%s\\n" "$@" >> "{argv_log}"\nexec "{real_curl}" "$@"\n', encoding="utf-8")
    wrapper.chmod(0o755)
    run_hook("user-prompt-submit", url, {"prompt": "x"}, PATH=f"{wrapper.parent}:{os.environ['PATH']}")
    assert state.seen_headers["X-RGPD-Guard-Token"] == TOKEN
    assert TOKEN not in argv_log.read_text(encoding="utf-8")


# Hooks qui lancent une détection ; SessionStart, SubagentStart et PreToolUse n'analysent aucun texte.
ANALYSING_HOOKS = {"UserPromptSubmit", "PostToolUse", "PostToolUseFailure", "PostToolBatch"}


def test_timeouts_nest_for_hooks_that_analyse_text() -> None:
    """DAT §3 : délai du hook > `curl --max-time` > échéance du moteur, pour chaque hook qui analyse un texte."""
    from rgpd_guard.config import Settings

    deadline_s = Settings(token="t", hmac_key="k").deadline_ms / 1000
    hooks = json.loads((SCRIPT.parents[1] / "hooks" / "hooks.json").read_text(encoding="utf-8"))["hooks"]
    assert ANALYSING_HOOKS <= set(hooks)
    for event, matchers in hooks.items():
        for matcher in matchers:
            for hook in matcher["hooks"]:
                max_time = float(hook["args"][-1])
                assert hook["timeout"] > max_time, event
                if event in ANALYSING_HOOKS:
                    assert max_time > deadline_s, event
