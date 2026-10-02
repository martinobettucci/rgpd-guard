# @spec docs/BACKLOG.md#RG-011 | docs/SCHEMA.md#tables
# @verifies docs/BACKLOG.md#RG-011 | docs/SCHEMA.md#tables
"""SCHEMA.md décrit exactement les tables et colonnes créées par les migrations."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from rgpd_guard.audit import Store

SCHEMA = Path(__file__).resolve().parents[2] / "docs" / "SCHEMA.md"


def documented_tables() -> dict[str, set[str]]:
    tables: dict[str, set[str]] = {}
    current: str | None = None
    for line in SCHEMA.read_text(encoding="utf-8").splitlines():
        heading = re.match(r"^### `([a-z_]+)`$", line)
        if heading:
            current = heading.group(1)
            tables[current] = set()
        elif line.startswith("## "):
            current = None
        elif current and (column := re.match(r"^\| `([a-z_]+)` \|", line)):
            tables[current].add(column.group(1))
    return tables


def test_schema_doc_matches_migrations(tmp_path: Path) -> None:
    if not SCHEMA.is_file():
        pytest.skip("docs/SCHEMA.md absent (moteur testé hors du dépôt complet)")
    store = Store(tmp_path / "base.db", "cle", 30, True)
    try:
        conn = store._conn
        names = [
            row[0]
            for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'")
        ]
        actual = {name: {row[1] for row in conn.execute(f"PRAGMA table_info({name})")} for name in names}
    finally:
        store.close()
    assert documented_tables() == actual
