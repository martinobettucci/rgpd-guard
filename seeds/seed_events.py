#!/usr/bin/env python3
# @spec docs/BACKLOG.md#RG-017 | docs/DAT.md#donnees-dev
"""Journal de démonstration : rejoue le corpus seedé à travers le véritable endpoint de hook du moteur.

Aucune insertion directe en base : chaque événement est produit par le même chemin qu'en usage réel
(prompts, sorties d'outils, refus de fichier secret, réhydratation, filet final). Idempotent : ne fait
rien si le journal contient déjà des événements, sauf avec --force.

Usage : python seeds/seed_events.py --engine http://engine:8742 [--force]
Le jeton est lu dans RGPD_GUARD_TOKEN.
"""

from __future__ import annotations

import argparse
import http.cookiejar
import importlib.util
import json
import os
import sys
import time
import urllib.request
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
SESSIONS = [f"00000000-0000-4000-8000-0000000000{n:02d}" for n in range(1, 6)]


def load_generator() -> Any:
    spec = importlib.util.spec_from_file_location("seeds_generate", HERE / "generate.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules["seeds_generate"] = module
    spec.loader.exec_module(module)
    return module


class Client:
    def __init__(self, base: str, token: str) -> None:
        self.base = base.rstrip("/")
        self.token = token
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))

    def call(self, method: str, path: str, body: Any = None, hook: bool = False) -> Any:
        data = None if body is None else json.dumps(body).encode()
        request = urllib.request.Request(f"{self.base}{path}", data=data, method=method)  # noqa: S310
        request.add_header("Content-Type", "application/json")
        if hook:
            request.add_header("X-RGPD-Guard-Token", self.token)
        with self.opener.open(request, timeout=120) as response:  # noqa: S310 (moteur local)
            payload = response.read()
        return json.loads(payload) if payload else {}

    def hook(self, event: str, payload: dict[str, Any]) -> Any:
        return self.call("POST", f"/v1/hooks/{event}", payload, hook=True)


def wait_ready(client: Client, timeout: float = 600) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            if client.call("GET", "/health").get("status") == "ok":
                return
        except OSError:
            pass
        time.sleep(2)
    raise SystemExit("le moteur ne répond pas")


def seed(client: Client) -> int:
    records = load_generator().generate()
    count = 0
    for index, record in enumerate(records):
        session = SESSIONS[index % len(SESSIONS)]
        base = {"session_id": session, "cwd": "/projet-demo", "permission_mode": "default"}
        if record["code"] or index % 3 == 2:
            # Sortie d'outil : un fichier lu dont le contenu provient du corpus.
            client.hook(
                "post-tool-use",
                base
                | {
                    "hook_event_name": "PostToolUse",
                    "tool_name": "Read",
                    "tool_input": {"file_path": f"/projet-demo/notes-{record['id']}.txt"},
                    "tool_response": {
                        "type": "text",
                        "file": {
                            "filePath": f"/projet-demo/notes-{record['id']}.txt",
                            "content": record["text"],
                            "numLines": record["text"].count("\n") + 1,
                            "startLine": 1,
                            "totalLines": record["text"].count("\n") + 1,
                        },
                    },
                    "tool_use_id": f"toolu_demo_{index:03d}",
                },
            )
        else:
            client.hook("user-prompt-submit", base | {"hook_event_name": "UserPromptSubmit", "prompt": record["text"]})
        count += 1
    demo = {"session_id": SESSIONS[0], "cwd": "/projet-demo", "permission_mode": "default"}
    # Refus de lecture d'un fichier de secrets.
    client.hook(
        "pre-tool-use",
        demo | {"hook_event_name": "PreToolUse", "tool_name": "Read", "tool_input": {"file_path": "/projet-demo/.env"}},
    )
    # Contournement explicite d'un prompt (hors secrets).
    client.hook(
        "user-prompt-submit", demo | {"prompt": "#rgpd-ok Merci de relancer camille.martin@courriel-fictif.fr demain."}
    )
    # Réhydratation : un jeton obtenu par une sortie d'outil est réécrit dans un fichier.
    client.hook(
        "pre-tool-use",
        demo
        | {
            "hook_event_name": "PreToolUse",
            "tool_name": "Write",
            "tool_input": {"file_path": "/projet-demo/relance.txt", "content": "Relancer ⟦EMAIL_1⟧ vendredi."},
        },
    )
    # Filet final : sortie d'une commande en échec contenant encore une donnée.
    client.hook(
        "post-tool-batch",
        demo
        | {
            "hook_event_name": "PostToolBatch",
            "tool_calls": [
                {
                    "tool_name": "Bash",
                    "tool_input": {"command": "cat virements.txt; exit 3"},
                    "tool_response": "Exit code 3\nIBAN FR7630006000011234567890189",
                }
            ],
        },
    )
    return count + 4


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--engine", default=os.environ.get("RGPD_GUARD_URL", "http://127.0.0.1:8742"))
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    token = os.environ.get("RGPD_GUARD_TOKEN", "")
    if not token:
        raise SystemExit("RGPD_GUARD_TOKEN est requis")
    client = Client(args.engine, token)
    wait_ready(client)
    client.call("POST", "/v1/auth/session", {"token": token})
    total = client.call("GET", "/v1/audit/stats")["total"]
    if total and not args.force:
        print(f"journal déjà seedé ({total} événements) : rien à faire")
        return
    calls = seed(client)
    total = client.call("GET", "/v1/audit/stats")["total"]
    # Une sortie d'outil sans donnée n'est pas journalisée (minimisation) : les deux nombres diffèrent.
    print(f"{calls} appels de hooks rejoués, {total} événements journalisés")


if __name__ == "__main__":
    main()
