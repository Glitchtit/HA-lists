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
    _migrate(conn)
    tables = conn.execute(
        "SELECT count(*) FROM sqlite_master WHERE type='table'"
    ).fetchone()[0]
    logger.info("Database initialized with %d tables", tables)
    return tables


def _migrate(conn: sqlite3.Connection) -> None:
    """Idempotent migrations for existing databases that predate newer features."""
    cols = {r["name"] for r in conn.execute("PRAGMA table_info(board_nodes)").fetchall()}
    # The base SCHEMA already emits the latest definition, so cols is the
    # target state on fresh installs. On upgrades, we rebuild if a newer
    # column is missing, or if the kind CHECK constraint lacks a new literal.
    table_sql_row = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='board_nodes'"
    ).fetchone()
    table_sql = (table_sql_row["sql"] if table_sql_row else "") or ""
    kind_literals_missing = "'board'" not in table_sql  # v0.9.2 added 'board' portal
    if "parent_group_id" not in cols or kind_literals_missing:
        # Rebuild board_nodes to extend the kind CHECK constraint
        # (SQLite can't ALTER an existing CHECK) and add the new columns.
        # FK references from board_edges.source_node_id / target_node_id are
        # preserved because we re-use ids via INSERT SELECT and keep the
        # renamed table under the original name. We toggle foreign_keys OFF
        # during the swap per SQLite's recommended table-redefinition recipe.
        logger.info("Migrating board_nodes: extend kind literals + columns")
        has_media = "media_filename" in cols
        has_parent = "parent_group_id" in cols
        media_sel = (
            "media_filename, media_mime, media_size, media_alt"
            if has_media
            else "NULL, NULL, NULL, NULL"
        )
        parent_sel = "parent_group_id" if has_parent else "NULL"
        conn.execute("PRAGMA foreign_keys = OFF")
        conn.executescript(
            f"""
            BEGIN;
            CREATE TABLE board_nodes_new (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                board_id        INTEGER NOT NULL REFERENCES boards(id) ON DELETE CASCADE,
                kind            TEXT NOT NULL
                                CHECK (kind IN ('list','note','card','image','file','group','board')),
                ref_id          INTEGER,
                title           TEXT    DEFAULT '',
                body            TEXT    DEFAULT '',
                color           TEXT    DEFAULT '',
                x               REAL    NOT NULL DEFAULT 0,
                y               REAL    NOT NULL DEFAULT 0,
                width           REAL    NOT NULL DEFAULT 240,
                height          REAL    NOT NULL DEFAULT 160,
                z               INTEGER DEFAULT 0,
                media_filename  TEXT,
                media_mime      TEXT,
                media_size      INTEGER,
                media_alt       TEXT,
                parent_group_id INTEGER REFERENCES board_nodes(id) ON DELETE SET NULL,
                created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            INSERT INTO board_nodes_new
                (id, board_id, kind, ref_id, title, body, color,
                 x, y, width, height, z,
                 media_filename, media_mime, media_size, media_alt,
                 parent_group_id,
                 created_at, updated_at)
                SELECT id, board_id, kind, ref_id, title, body, color,
                       x, y, width, height, z, {media_sel},
                       {parent_sel},
                       created_at, updated_at
                FROM board_nodes;
            DROP TABLE board_nodes;
            ALTER TABLE board_nodes_new RENAME TO board_nodes;
            CREATE INDEX IF NOT EXISTS idx_board_nodes_board ON board_nodes(board_id);
            CREATE INDEX IF NOT EXISTS idx_board_nodes_parent ON board_nodes(parent_group_id);
            COMMIT;
            """
        )
        conn.execute("PRAGMA foreign_keys = ON")


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

CREATE TABLE IF NOT EXISTS notes (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    folder_id    INTEGER REFERENCES folders(id) ON DELETE SET NULL,
    title        TEXT    NOT NULL,
    body         TEXT    NOT NULL DEFAULT '',
    icon         TEXT    DEFAULT '📝',
    color        TEXT    DEFAULT '',
    pinned       INTEGER DEFAULT 0,
    archived     INTEGER DEFAULT 0,
    sort_order   INTEGER DEFAULT 0,
    ai_generated INTEGER DEFAULT 0,
    created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_notes_folder ON notes(folder_id);
CREATE INDEX IF NOT EXISTS idx_notes_title  ON notes(title);

CREATE TABLE IF NOT EXISTS note_links (
    source_note_id INTEGER NOT NULL REFERENCES notes(id) ON DELETE CASCADE,
    target_title   TEXT    NOT NULL,
    link_type      TEXT    NOT NULL CHECK (link_type IN ('wikilink','embed')),
    UNIQUE(source_note_id, target_title, link_type)
);
CREATE INDEX IF NOT EXISTS idx_note_links_target ON note_links(target_title);

CREATE TABLE IF NOT EXISTS boards (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    folder_id   INTEGER REFERENCES folders(id) ON DELETE SET NULL,
    name        TEXT    NOT NULL,
    icon        TEXT    DEFAULT '🧩',
    color       TEXT    DEFAULT '',
    pinned      INTEGER DEFAULT 0,
    archived    INTEGER DEFAULT 0,
    sort_order  INTEGER DEFAULT 0,
    viewport    TEXT    DEFAULT '{"x":0,"y":0,"zoom":1}',
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_boards_folder ON boards(folder_id);

CREATE TABLE IF NOT EXISTS board_nodes (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    board_id        INTEGER NOT NULL REFERENCES boards(id) ON DELETE CASCADE,
    kind            TEXT NOT NULL
                    CHECK (kind IN ('list','note','card','image','file','group','board')),
    ref_id          INTEGER,
    title           TEXT    DEFAULT '',
    body            TEXT    DEFAULT '',
    color           TEXT    DEFAULT '',
    x               REAL    NOT NULL DEFAULT 0,
    y               REAL    NOT NULL DEFAULT 0,
    width           REAL    NOT NULL DEFAULT 240,
    height          REAL    NOT NULL DEFAULT 160,
    z               INTEGER DEFAULT 0,
    media_filename  TEXT,
    media_mime      TEXT,
    media_size      INTEGER,
    media_alt       TEXT,
    parent_group_id INTEGER REFERENCES board_nodes(id) ON DELETE SET NULL,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_board_nodes_board ON board_nodes(board_id);
CREATE INDEX IF NOT EXISTS idx_board_nodes_parent ON board_nodes(parent_group_id);

CREATE TABLE IF NOT EXISTS board_edges (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    board_id        INTEGER NOT NULL REFERENCES boards(id) ON DELETE CASCADE,
    source_node_id  INTEGER NOT NULL REFERENCES board_nodes(id) ON DELETE CASCADE,
    target_node_id  INTEGER NOT NULL REFERENCES board_nodes(id) ON DELETE CASCADE,
    label           TEXT    DEFAULT '',
    style           TEXT    DEFAULT 'default',
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_board_edges_board ON board_edges(board_id);
"""
