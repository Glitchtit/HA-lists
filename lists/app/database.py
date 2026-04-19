"""HA-lists — SQLite schema and connection management."""

from __future__ import annotations
import logging
import os
import sqlite3

logger = logging.getLogger(__name__)

DB_PATH = os.path.join(os.environ.get("DATA_DIR", "/data"), "lists.db")

_conn: sqlite3.Connection | None = None


def get_connection() -> sqlite3.Connection:
    global _conn
    if _conn is None:
        _conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        _conn.row_factory = sqlite3.Row
        _conn.execute("PRAGMA journal_mode = WAL")
        _conn.execute("PRAGMA foreign_keys = ON")
    return _conn


def close_connection() -> None:
    global _conn
    if _conn is not None:
        _conn.close()
        _conn = None


def initialize() -> int:
    """Create tables; return the table count."""
    conn = get_connection()
    conn.executescript(SCHEMA)
    conn.commit()
    tables = conn.execute(
        "SELECT count(*) FROM sqlite_master WHERE type='table'"
    ).fetchone()[0]
    logger.info("Database initialized with %d tables", tables)
    return tables


SCHEMA = """
CREATE TABLE IF NOT EXISTS folders (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT    NOT NULL,
    icon        TEXT    DEFAULT '📁',
    color       TEXT    DEFAULT '',
    sort_order  INTEGER DEFAULT 0,
    archived    INTEGER DEFAULT 0,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS lists (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    folder_id   INTEGER REFERENCES folders(id) ON DELETE SET NULL,
    name        TEXT    NOT NULL,
    icon        TEXT    DEFAULT '📋',
    color       TEXT    DEFAULT '',
    sort_order  INTEGER DEFAULT 0,
    archived    INTEGER DEFAULT 0,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_lists_folder ON lists(folder_id);

CREATE TABLE IF NOT EXISTS persons (
    entity_id   TEXT    PRIMARY KEY,
    name        TEXT    NOT NULL,
    ha_user_id  TEXT    DEFAULT '',
    avatar_url  TEXT    DEFAULT '',
    active      INTEGER DEFAULT 1,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS items (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    list_id       INTEGER NOT NULL REFERENCES lists(id) ON DELETE CASCADE,
    title         TEXT    NOT NULL,
    notes         TEXT    DEFAULT '',
    status        TEXT    DEFAULT 'open'
                          CHECK (status IN ('open', 'completed', 'archived')),
    assigned_to   TEXT    REFERENCES persons(entity_id) ON DELETE SET NULL,
    due_at        TEXT,
    priority      INTEGER DEFAULT 0,
    estimate_min  INTEGER,
    estimate_max  INTEGER,
    spiciness     INTEGER DEFAULT 3 CHECK (spiciness BETWEEN 1 AND 5),
    sort_order    INTEGER DEFAULT 0,
    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at  TIMESTAMP,
    completed_by  TEXT
);
CREATE INDEX IF NOT EXISTS idx_items_list ON items(list_id);
CREATE INDEX IF NOT EXISTS idx_items_status ON items(status);
CREATE INDEX IF NOT EXISTS idx_items_assigned ON items(assigned_to);
CREATE INDEX IF NOT EXISTS idx_items_due ON items(due_at);

CREATE TABLE IF NOT EXISTS subtasks (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id       INTEGER NOT NULL REFERENCES items(id) ON DELETE CASCADE,
    title         TEXT    NOT NULL,
    status        TEXT    DEFAULT 'open'
                          CHECK (status IN ('open', 'completed')),
    sort_order    INTEGER DEFAULT 0,
    ai_generated  INTEGER DEFAULT 0,
    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at  TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_subtasks_item ON subtasks(item_id);

CREATE TABLE IF NOT EXISTS tags (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT    NOT NULL UNIQUE,
    color       TEXT    DEFAULT '',
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS item_tags (
    item_id  INTEGER NOT NULL REFERENCES items(id) ON DELETE CASCADE,
    tag_id   INTEGER NOT NULL REFERENCES tags(id)  ON DELETE CASCADE,
    PRIMARY KEY (item_id, tag_id)
);
CREATE INDEX IF NOT EXISTS idx_item_tags_tag ON item_tags(tag_id);
"""
