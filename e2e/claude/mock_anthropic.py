#!/usr/bin/env python3
# @spec docs/BACKLOG.md#RG-001 | docs/BACKLOG.md#RG-005 | docs/BACKLOG.md#RG-006 | docs/DAT.md#flux-hooks
"""Faux serveur de l'API Messages d'Anthropic pour les tests E2E de Claude Code.

Il rejoue un scénario d'étapes (texte ou appels d'outils) et enregistre chaque requête
reçue, afin de prouver qu'une valeur canari n'est jamais transmise au fournisseur.

Usage : mock_anthropic.py --port 0 --scenario scenario.json --record requests.jsonl
Le port effectif est écrit sur la sortie standard (`PORT=<n>`).
"""

from __future__ import annotations

import argparse
import gzip
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any


class ScenarioState:
    """Distribue les étapes du scénario aux requêtes de la boucle principale."""

    def __init__(self, steps: list[list[dict[str, Any]]]) -> None:
        self.steps = steps
        self.index = 0
        self.lock = threading.Lock()
        self.counter = 0

    def next_content(self) -> list[dict[str, Any]]:
        with self.lock:
            if self.index < len(self.steps):
                content = self.steps[self.index]
                self.index += 1
            else:
                content = [{"type": "text", "text": "Fin du scénario."}]
            return [self._with_id(block) for block in content]

    def _with_id(self, block: dict[str, Any]) -> dict[str, Any]:
        if block.get("type") == "tool_use" and "id" not in block:
            self.counter += 1
            return {**block, "id": f"toolu_mock_{self.counter:04d}"}
        return block


def sse(event: str, data: dict[str, Any]) -> bytes:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n".encode()


def build_stream(content: list[dict[str, Any]], model: str) -> bytes:
    stop_reason = "tool_use" if any(b.get("type") == "tool_use" for b in content) else "end_turn"
    out = [
        sse(
            "message_start",
            {
                "type": "message_start",
                "message": {
                    "id": "msg_mock",
                    "type": "message",
                    "role": "assistant",
                    "model": model,
                    "content": [],
                    "stop_reason": None,
                    "stop_sequence": None,
                    "usage": {"input_tokens": 10, "output_tokens": 1},
                },
            },
        )
    ]
    for index, block in enumerate(content):
        if block["type"] == "text":
            out.append(sse("content_block_start", {"type": "content_block_start", "index": index, "content_block": {"type": "text", "text": ""}}))
            out.append(sse("content_block_delta", {"type": "content_block_delta", "index": index, "delta": {"type": "text_delta", "text": block["text"]}}))
        else:
            start = {"type": "tool_use", "id": block["id"], "name": block["name"], "input": {}}
            out.append(sse("content_block_start", {"type": "content_block_start", "index": index, "content_block": start}))
            partial = json.dumps(block.get("input", {}), ensure_ascii=False)
            out.append(sse("content_block_delta", {"type": "content_block_delta", "index": index, "delta": {"type": "input_json_delta", "partial_json": partial}}))
        out.append(sse("content_block_stop", {"type": "content_block_stop", "index": index}))
    out.append(sse("message_delta", {"type": "message_delta", "delta": {"stop_reason": stop_reason, "stop_sequence": None}, "usage": {"output_tokens": 5}}))
    out.append(sse("message_stop", {"type": "message_stop"}))
    return b"".join(out)


def build_message(content: list[dict[str, Any]], model: str) -> dict[str, Any]:
    stop_reason = "tool_use" if any(b.get("type") == "tool_use" for b in content) else "end_turn"
    return {
        "id": "msg_mock",
        "type": "message",
        "role": "assistant",
        "model": model,
        "content": content,
        "stop_reason": stop_reason,
        "stop_sequence": None,
        "usage": {"input_tokens": 10, "output_tokens": 5},
    }


def make_handler(state: ScenarioState, record_path: str):
    record_lock = threading.Lock()

    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, *_args: Any) -> None:  # silence du journal HTTP standard
            return

        def _record(self, body_text: str) -> None:
            with record_lock, open(record_path, "a", encoding="utf-8") as handle:
                handle.write(json.dumps({"method": self.command, "path": self.path, "body": body_text}, ensure_ascii=False) + "\n")

        def _read_body(self) -> str:
            length = int(self.headers.get("Content-Length") or 0)
            raw = self.rfile.read(length) if length else b""
            if self.headers.get("Content-Encoding") == "gzip":
                raw = gzip.decompress(raw)
            return raw.decode("utf-8", errors="replace")

        def _send(self, status: int, payload: bytes, content_type: str) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def do_GET(self) -> None:  # noqa: N802 (nom imposé par http.server)
            self._record("")
            self._send(200, b"{}", "application/json")

        def do_POST(self) -> None:  # noqa: N802
            body_text = self._read_body()
            self._record(body_text)
            path = self.path.split("?", 1)[0]
            if path.endswith("/count_tokens"):
                self._send(200, b'{"input_tokens": 10}', "application/json")
                return
            if not path.endswith("/v1/messages"):
                self._send(200, b"{}", "application/json")
                return
            try:
                request = json.loads(body_text)
            except json.JSONDecodeError:
                request = {}
            model = request.get("model", "claude-mock")
            # Seules les requêtes de la boucle agentique (avec outils) consomment le scénario.
            if request.get("tools"):
                content = state.next_content()
            else:
                content = [{"type": "text", "text": "Titre de test"}]
            if request.get("stream"):
                self._send(200, build_stream(content, model), "text/event-stream")
            else:
                self._send(200, json.dumps(build_message(content, model)).encode(), "application/json")

    return Handler


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=0)
    parser.add_argument("--scenario", required=True)
    parser.add_argument("--record", required=True)
    args = parser.parse_args()
    with open(args.scenario, encoding="utf-8") as handle:
        steps = json.load(handle)["steps"]
    server = ThreadingHTTPServer(("127.0.0.1", args.port), make_handler(ScenarioState(steps), args.record))
    print(f"PORT={server.server_address[1]}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
