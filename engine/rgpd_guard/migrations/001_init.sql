-- @spec docs/BACKLOG.md#RG-011 | docs/BACKLOG.md#RG-010 | docs/SCHEMA.md#migration-001
-- Journal d'audit minimisé (aucune valeur brute) et surcharges de politique.
CREATE TABLE audit_events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts TEXT NOT NULL,
  session_hash TEXT NOT NULL,
  subagent INTEGER NOT NULL DEFAULT 0,
  event TEXT NOT NULL,
  tool TEXT,
  decision TEXT NOT NULL,
  profile TEXT NOT NULL,
  latency_ms REAL NOT NULL,
  entity_count INTEGER NOT NULL,
  categories TEXT NOT NULL,
  bypass INTEGER NOT NULL DEFAULT 0,
  partial INTEGER NOT NULL DEFAULT 0,
  note TEXT
);
CREATE INDEX idx_audit_events_ts ON audit_events(ts);
CREATE INDEX idx_audit_events_decision ON audit_events(decision);

CREATE TABLE audit_entities (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  event_id INTEGER NOT NULL REFERENCES audit_events(id) ON DELETE CASCADE,
  label TEXT NOT NULL,
  detector TEXT NOT NULL,
  score REAL NOT NULL,
  action TEXT NOT NULL,
  value_hmac TEXT NOT NULL,
  preview TEXT
);
CREATE INDEX idx_audit_entities_event ON audit_entities(event_id);
CREATE INDEX idx_audit_entities_label ON audit_entities(label);

CREATE TABLE policies (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  version INTEGER NOT NULL,
  document TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
