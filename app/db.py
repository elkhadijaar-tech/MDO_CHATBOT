"""Accès SQLite (bibliothèque standard) : schéma, migration avec sauvegarde, connexion."""
import shutil
import sqlite3
import time
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS kb_meta (key TEXT PRIMARY KEY, value TEXT);
CREATE TABLE IF NOT EXISTS kbs (name TEXT PRIMARY KEY, label TEXT NOT NULL, builtin INTEGER NOT NULL DEFAULT 0,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS sources (
  id INTEGER PRIMARY KEY AUTOINCREMENT, kb TEXT NOT NULL, name TEXT NOT NULL, filename TEXT, stored_path TEXT,
  source_type TEXT, sha256 TEXT, builtin INTEGER NOT NULL DEFAULT 0, status TEXT NOT NULL DEFAULT 'indexed',
  chunk_count INTEGER NOT NULL DEFAULT 0, duplicate_count INTEGER NOT NULL DEFAULT 0, report TEXT,
  imported_at TEXT DEFAULT CURRENT_TIMESTAMP, updated_at TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS sections (id TEXT PRIMARY KEY, title TEXT NOT NULL, position INTEGER);
CREATE TABLE IF NOT EXISTS chunks (
  id INTEGER PRIMARY KEY AUTOINCREMENT, section_id TEXT, title TEXT NOT NULL, text TEXT NOT NULL,
  kind TEXT NOT NULL DEFAULT 'item', semester INTEGER,
  kb TEXT NOT NULL DEFAULT 'onboarding', source_id INTEGER, location TEXT, academic_year TEXT,
  verification TEXT NOT NULL DEFAULT 'NEEDS_VERIFICATION', text_hash TEXT);
CREATE TABLE IF NOT EXISTS modules (
  id INTEGER PRIMARY KEY AUTOINCREMENT, semester INTEGER NOT NULL, name TEXT NOT NULL, professor TEXT);
CREATE TABLE IF NOT EXISTS conversations (
  id INTEGER PRIMARY KEY AUTOINCREMENT, created_at TEXT DEFAULT CURRENT_TIMESTAMP, client_id TEXT, title TEXT);
CREATE TABLE IF NOT EXISTS messages (
  id INTEGER PRIMARY KEY AUTOINCREMENT, conversation_id INTEGER NOT NULL, role TEXT NOT NULL,
  content TEXT NOT NULL, mode TEXT, language TEXT, sources TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP,
  model TEXT, kb_used TEXT, tokens_in INTEGER, tokens_out INTEGER, request_id TEXT, feedback INTEGER,
  FOREIGN KEY (conversation_id) REFERENCES conversations(id));
CREATE TABLE IF NOT EXISTS unanswered (
  id INTEGER PRIMARY KEY AUTOINCREMENT, question TEXT NOT NULL, language TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP);
"""

INDEXES = """
CREATE INDEX IF NOT EXISTS idx_chunks_source ON chunks(source_id);
CREATE INDEX IF NOT EXISTS idx_chunks_hash ON chunks(kb, text_hash);
"""

# colonnes ajoutées après la version 1 (migration d'une base existante)
MIGRATIONS = {
    "chunks": [("kb", "TEXT NOT NULL DEFAULT 'onboarding'"), ("source_id", "INTEGER"), ("location", "TEXT"),
               ("academic_year", "TEXT"), ("verification", "TEXT NOT NULL DEFAULT 'NEEDS_VERIFICATION'"),
               ("text_hash", "TEXT")],
    "conversations": [("client_id", "TEXT"), ("title", "TEXT")],
    "messages": [("model", "TEXT"), ("kb_used", "TEXT"), ("tokens_in", "INTEGER"), ("tokens_out", "INTEGER"),
                 ("request_id", "TEXT"), ("feedback", "INTEGER")],
}


def connect(path) -> sqlite3.Connection:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _columns(conn, table):
    return {r["name"] for r in conn.execute(f"PRAGMA table_info({table})")}


def init_db(conn: sqlite3.Connection, db_path=None) -> str:
    """Crée/migre le schéma. Retourne le chemin de la sauvegarde créée (ou '')."""
    backup = ""
    existing = {r["name"] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    needs = [(t, c) for t, cols in MIGRATIONS.items() if t in existing
             for c, _ in cols if c not in _columns(conn, t)]
    if needs and db_path and Path(db_path).exists():
        backup = f"{db_path}.bak-{time.strftime('%Y%m%d%H%M%S')}"
        shutil.copy2(db_path, backup)
    conn.executescript(SCHEMA)
    for table, cols in MIGRATIONS.items():
        have = _columns(conn, table)
        for col, decl in cols:
            if col not in have:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {decl}")
    conn.executescript(INDEXES)
    conn.commit()
    return backup
