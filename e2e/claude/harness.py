# @spec docs/BACKLOG.md#RG-001 | docs/BACKLOG.md#RG-005 | docs/BACKLOG.md#RG-006 | docs/DAT.md#flux-hooks
"""Harnais E2E : moteur réel en sous-processus, faux serveur API, Claude Code isolé avec le plugin."""

from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import sys
import time
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[2]
PLUGIN_DIR = REPO / "plugins" / "rgpd-guard"
MOCK = Path(__file__).resolve().parent / "mock_anthropic.py"
ENGINE_DIR = REPO / "engine"
E2E_TOKEN = "jeton-e2e-0123456789abcdef"


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def wait_http(url: str, timeout: float = 30.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=1) as response:  # noqa: S310 (adresse locale de test)
                if response.status == 200:
                    return
        except OSError:
            time.sleep(0.2)
    raise TimeoutError(f"{url} ne répond pas")


@dataclass
class Engine:
    url: str
    process: subprocess.Popen[bytes]
    data_dir: Path

    def stop(self) -> None:
        self.process.terminate()
        self.process.wait(timeout=10)


def start_engine(tmp: Path, workspace: Path, profile: str = "rapide", detectors: str = "rules,secrets") -> Engine:
    port = free_port()
    data_dir = tmp / "engine-data"
    env = {
        "PATH": os.environ["PATH"],
        "HOME": str(tmp),
        "RGPD_GUARD_ENV": "test",
        "RGPD_GUARD_TOKEN": E2E_TOKEN,
        "RGPD_GUARD_HMAC_KEY": "cle-hmac-e2e",
        "RGPD_GUARD_DATA_DIR": str(data_dir),
        "RGPD_GUARD_PROFILE": profile,
        "RGPD_GUARD_ENABLED_DETECTORS": detectors,
        "RGPD_GUARD_WORKSPACE_ROOT": str(workspace),
        "RGPD_GUARD_ALLOWED_HOSTS": "127.0.0.1,localhost",
        "RGPD_GUARD_HOST": "127.0.0.1",
        "RGPD_GUARD_PORT": str(port),
        "RGPD_GUARD_MODELS_DIR": os.environ.get("RGPD_GUARD_MODELS_DIR", str(tmp / "models")),
    }
    log = open(tmp / "engine.log", "wb")  # noqa: SIM115 (fermé avec le processus)
    process = subprocess.Popen(  # noqa: S603
        [sys.executable, "-m", "rgpd_guard"], cwd=ENGINE_DIR, env=env, stdout=log, stderr=subprocess.STDOUT
    )
    url = f"http://127.0.0.1:{port}"
    wait_http(f"{url}/health", timeout=600)
    return Engine(url, process, data_dir)


@dataclass
class RunResult:
    returncode: int
    requests: list[dict[str, Any]]
    messages_bodies: list[str]
    stdout: str
    stderr: str

    @property
    def result_text(self) -> str:
        for line in reversed(self.stdout.splitlines()):
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if event.get("type") == "result":
                return str(event.get("result", ""))
        return ""

    def sent(self, needle: str) -> bool:
        """Vrai si `needle` apparaît dans une requête reçue par le faux serveur API."""
        return any(needle in body for body in self.messages_bodies)


def run_claude(
    tmp: Path,
    cwd: Path,
    prompt: str,
    steps: list[list[dict[str, Any]]],
    engine_url: str | None,
    permission_mode: str = "bypassPermissions",
    extra_env: dict[str, str] | None = None,
) -> RunResult:
    if shutil.which("claude") is None:
        raise RuntimeError("Claude Code introuvable dans le PATH")
    run_dir = tmp / f"run-{time.monotonic_ns()}"
    (run_dir / "home").mkdir(parents=True)
    scenario = run_dir / "scenario.json"
    scenario.write_text(json.dumps({"steps": steps}, ensure_ascii=False), encoding="utf-8")
    record = run_dir / "requests.jsonl"
    record.touch()
    mock = subprocess.Popen(  # noqa: S603
        [sys.executable, str(MOCK), "--scenario", str(scenario), "--record", str(record)],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    try:
        assert mock.stdout is not None
        port = mock.stdout.readline().decode().strip().removeprefix("PORT=")
        env = {
            "PATH": os.environ["PATH"],
            "HOME": str(run_dir / "home"),
            "IS_SANDBOX": "1",
            "ANTHROPIC_BASE_URL": f"http://127.0.0.1:{port}",
            "ANTHROPIC_API_KEY": "cle-factice-e2e",
            "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1",
            "DISABLE_TELEMETRY": "1",
            "DISABLE_AUTOUPDATER": "1",
            "RGPD_GUARD_CONFIG": str(run_dir / "absent.env"),
            "RGPD_GUARD_TOKEN": E2E_TOKEN,
            "RGPD_GUARD_URL": engine_url or f"http://127.0.0.1:{free_port()}",
        }
        env.update(extra_env or {})
        completed = subprocess.run(  # noqa: S603
            [
                "claude",
                "-p",
                "--plugin-dir",
                str(PLUGIN_DIR),
                "--output-format",
                "stream-json",
                "--verbose",
                "--permission-mode",
                permission_mode,
                prompt,
            ],
            cwd=cwd,
            env=env,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            timeout=180,
            check=False,
        )
    finally:
        mock.terminate()
        mock.wait(timeout=10)
    requests = [json.loads(line) for line in record.read_text(encoding="utf-8").splitlines() if line.strip()]
    bodies = [r["body"] for r in requests if "/v1/messages" in r["path"]]
    return RunResult(
        completed.returncode,
        requests,
        bodies,
        completed.stdout.decode(errors="replace"),
        completed.stderr.decode(errors="replace"),
    )


def tool_use(name: str, tool_input: dict[str, Any]) -> dict[str, Any]:
    return {"type": "tool_use", "name": name, "input": tool_input}


def text(value: str) -> dict[str, Any]:
    return {"type": "text", "text": value}
