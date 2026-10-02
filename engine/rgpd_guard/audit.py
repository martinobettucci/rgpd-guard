# @spec docs/BACKLOG.md#RG-011 | docs/BACKLOG.md#RG-010 | docs/DAT.md#donnees | docs/SCHEMA.md#tables
"""Stockage SQLite : journal d'audit minimisé, surcharges de politique, migrations versionnées."""

from __future__ import annotations

import hashlib
import hmac
import json
import sqlite3
import threading
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from importlib import resources
from pathlib import Path
from typing import Any

from .models import Action, Analysis, Finding

PURGE_INTERVAL_SECONDS = 3600


def mask(value: str) -> str:
    """Aperçu masqué : jamais plus de deux caractères d'origine."""
    if "@" in value and value.count("@") == 1:
        local, domain = value.split("@")
        tld = domain.rsplit(".", 1)[-1] if "." in domain else ""
        return f"{local[:1]}***@{domain[:1]}***{'.' + tld if tld else ''}"
    compact = value.strip()
    if len(compact) <= 4:
        return "****"
    return f"{compact[0]}{'*' * min(len(compact) - 2, 8)}{compact[-1]}"


@dataclass
class AuditRecord:
    session_id: str
    event: str
    decision: str
    profile: str
    latency_ms: float
    findings: list[Finding] = field(default_factory=list)
    categories: list[dict[str, Any]] = field(default_factory=list)
    tool: str | None = None
    subagent: bool = False
    bypass: bool = False
    partial: bool = False
    note: str | None = None


class Store:
    def __init__(self, path: Path, hmac_key: str, retention_days: int, keep_preview: bool) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(path), check_same_thread=False, isolation_level=None)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._lock = threading.Lock()
        self._key = hmac_key.encode()
        self.retention_days = retention_days
        self.keep_preview = keep_preview
        self._last_purge = 0.0
        self.migrate()

    # Migrations -----------------------------------------------------------------------------
    def migrate(self) -> list[int]:
        applied: list[int] = []
        with self._lock:
            self._conn.execute(
                "CREATE TABLE IF NOT EXISTS schema_migrations (version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL)"
            )
            done = {row[0] for row in self._conn.execute("SELECT version FROM schema_migrations")}
            scripts = sorted(
                (p for p in resources.files("rgpd_guard.migrations").iterdir() if p.name.endswith(".sql")),
                key=lambda p: p.name,
            )
            for script in scripts:
                version = int(script.name.split("_", 1)[0])
                if version in done:
                    continue
                # executescript valide toute transaction ouverte : la migration et son enregistrement
                # forment donc un seul script transactionnel.
                body = script.read_text(encoding="utf-8")
                record = f"INSERT INTO schema_migrations(version, applied_at) VALUES ({version}, '{_now()}');"  # noqa: S608 (valeurs internes)
                try:
                    self._conn.executescript(f"BEGIN;\n{body}\n{record}\nCOMMIT;")
                except Exception:
                    if self._conn.in_transaction:
                        self._conn.execute("ROLLBACK")
                    raise
                applied.append(version)
        return applied

    # Empreintes -------------------------------------------------------------------------------
    def digest(self, value: str) -> str:
        return hmac.new(self._key, value.encode(), hashlib.sha256).hexdigest()[:16]

    # Journal ----------------------------------------------------------------------------------
    def record(self, rec: AuditRecord) -> int:
        with self._lock:
            cur = self._conn.execute(
                "INSERT INTO audit_events(ts, session_hash, subagent, event, tool, decision, profile, latency_ms,"
                " entity_count, categories, bypass, partial, note) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    _now(),
                    self.digest(rec.session_id),
                    int(rec.subagent),
                    rec.event,
                    rec.tool,
                    rec.decision,
                    rec.profile,
                    round(rec.latency_ms, 2),
                    len(rec.findings),
                    json.dumps(rec.categories, ensure_ascii=False),
                    int(rec.bypass),
                    int(rec.partial),
                    rec.note,
                ),
            )
            event_id = int(cur.lastrowid or 0)
            self._conn.executemany(
                "INSERT INTO audit_entities(event_id, label, detector, score, action, value_hmac, preview)"
                " VALUES (?,?,?,?,?,?,?)",
                [
                    (
                        event_id,
                        f.span.label.value,
                        f.span.detector,
                        round(f.span.score, 3),
                        f.action.value,
                        self.digest(f.value),
                        mask(f.value) if self.keep_preview else None,
                    )
                    for f in rec.findings
                ],
            )
        self.purge_if_due()
        return event_id

    def purge_if_due(self) -> int:
        if time.monotonic() - self._last_purge < PURGE_INTERVAL_SECONDS:
            return 0
        return self.purge()

    def purge(self) -> int:
        limit = (datetime.now(UTC) - timedelta(days=self.retention_days)).isoformat(timespec="seconds")
        with self._lock:
            self._last_purge = time.monotonic()
            cur = self._conn.execute("DELETE FROM audit_events WHERE ts < ?", (limit,))
            return cur.rowcount

    def list_events(
        self,
        limit: int = 50,
        offset: int = 0,
        decision: str | None = None,
        event: str | None = None,
        label: str | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        where = []
        params: list[Any] = []
        if decision:
            where.append("e.decision = ?")
            params.append(decision)
        if event:
            where.append("e.event = ?")
            params.append(event)
        if label:
            where.append("EXISTS (SELECT 1 FROM audit_entities x WHERE x.event_id = e.id AND x.label = ?)")
            params.append(label)
        clause = f"WHERE {' AND '.join(where)}" if where else ""
        with self._lock:
            total = self._conn.execute(f"SELECT COUNT(*) FROM audit_events e {clause}", params).fetchone()[0]  # noqa: S608
            rows = self._conn.execute(
                f"SELECT * FROM audit_events e {clause} ORDER BY e.id DESC LIMIT ? OFFSET ?",  # noqa: S608
                [*params, limit, offset],
            ).fetchall()
            events = []
            for row in rows:
                entities = self._conn.execute(
                    "SELECT label, detector, score, action, preview FROM audit_entities WHERE event_id = ? ORDER BY id",
                    (row["id"],),
                ).fetchall()
                item = dict(row)
                item["categories"] = json.loads(item["categories"])
                item["bypass"] = bool(item["bypass"])
                item["partial"] = bool(item["partial"])
                item["subagent"] = bool(item["subagent"])
                item["entities"] = [dict(e) for e in entities]
                events.append(item)
        return events, int(total)

    def stats(self) -> dict[str, Any]:
        with self._lock:
            by_decision = {
                r[0]: r[1] for r in self._conn.execute("SELECT decision, COUNT(*) FROM audit_events GROUP BY decision")
            }
            by_label = {
                r[0]: r[1]
                for r in self._conn.execute(
                    "SELECT label, COUNT(*) FROM audit_entities GROUP BY label ORDER BY COUNT(*) DESC"
                )
            }
            total = self._conn.execute("SELECT COUNT(*) FROM audit_events").fetchone()[0]
        return {"total": total, "by_decision": by_decision, "by_label": by_label}

    # Politique ---------------------------------------------------------------------------------
    def latest_policy(self) -> dict[str, Any] | None:
        with self._lock:
            row = self._conn.execute("SELECT document FROM policies ORDER BY id DESC LIMIT 1").fetchone()
        return json.loads(row[0]) if row else None

    def save_policy(self, document: dict[str, Any], version: int) -> None:
        with self._lock:
            self._conn.execute(
                "INSERT INTO policies(version, document, updated_at) VALUES (?,?,?)",
                (version, json.dumps(document, ensure_ascii=False), _now()),
            )

    def close(self) -> None:
        with self._lock:
            self._conn.close()


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def decision_of(analysis: Analysis) -> str:
    if analysis.is_blocking:
        return Action.BLOCK.value
    if analysis.warnings or analysis.warning_categories:
        return Action.WARN.value
    if analysis.to_pseudonymize:
        return Action.PSEUDONYMIZE.value
    return Action.ALLOW.value
