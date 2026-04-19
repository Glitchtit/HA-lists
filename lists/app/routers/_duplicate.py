"""HA-lists — deep-duplicate helpers for folders, lists, items.

All three operations share the same logic:
- Copy the row, mutating a subset of fields (new name suffix, target parent).
- Recursively copy children.
- Append to the target parent (sort_order = max + 1).

Each helper works on an open sqlite3 connection and commits at the end.
They return the ID of the newly created row so the router can re-serialize it.
"""

from __future__ import annotations

import sqlite3


def _next_sort_order(conn: sqlite3.Connection, table: str, where: str, params: tuple) -> int:
    row = conn.execute(
        f"SELECT COALESCE(MAX(sort_order), -1) AS m FROM {table} WHERE {where}",
        params,
    ).fetchone()
    return (row["m"] if row["m"] is not None else -1) + 1


def duplicate_item(
    conn: sqlite3.Connection,
    item_id: int,
    *,
    target_list_id: int | None = None,
    name_suffix: str = " (copy)",
) -> int:
    """Deep-copy an item (+ subtasks + tag attachments) into `target_list_id`
    (or the same list if omitted). Returns the new item's id."""
    src = conn.execute("SELECT * FROM items WHERE id = ?", (item_id,)).fetchone()
    if not src:
        raise ValueError(f"item_id {item_id} not found")
    list_id = target_list_id if target_list_id is not None else src["list_id"]
    sort_order = _next_sort_order(conn, "items", "list_id = ?", (list_id,))

    cursor = conn.execute(
        """INSERT INTO items
           (list_id, title, notes, status, assigned_to, due_at, priority,
            estimate_min, estimate_max, spiciness, sort_order)
           VALUES (?, ?, ?, 'open', ?, ?, ?, ?, ?, ?, ?)""",
        (
            list_id,
            (src["title"] or "") + name_suffix,
            src["notes"],
            src["assigned_to"],
            src["due_at"],
            src["priority"],
            src["estimate_min"],
            src["estimate_max"],
            src["spiciness"],
            sort_order,
        ),
    )
    new_item_id = cursor.lastrowid

    # Copy subtasks (status reset to 'open').
    subs = conn.execute(
        "SELECT * FROM subtasks WHERE item_id = ? ORDER BY sort_order, id",
        (item_id,),
    ).fetchall()
    for s in subs:
        conn.execute(
            """INSERT INTO subtasks (item_id, title, status, sort_order, ai_generated)
               VALUES (?, ?, 'open', ?, ?)""",
            (new_item_id, s["title"], s["sort_order"], s["ai_generated"]),
        )

    # Copy tag attachments (preserves tags; each pair is still unique).
    conn.execute(
        """INSERT OR IGNORE INTO item_tags (item_id, tag_id)
           SELECT ?, tag_id FROM item_tags WHERE item_id = ?""",
        (new_item_id, item_id),
    )

    conn.commit()
    return new_item_id


def duplicate_list(
    conn: sqlite3.Connection,
    list_id: int,
    *,
    target_folder_id: int | None = -1,  # sentinel: -1 means "same folder"
    name_suffix: str = " (copy)",
) -> int:
    """Deep-copy a list (+ every item + each item's subtasks + tag attachments)
    into `target_folder_id`. Returns the new list's id.

    ``target_folder_id=None`` places the copy in "Unfiled"; leave as sentinel
    to keep the source folder. The caller is responsible for validating that
    ``target_folder_id`` actually exists.
    """
    src = conn.execute("SELECT * FROM lists WHERE id = ?", (list_id,)).fetchone()
    if not src:
        raise ValueError(f"list_id {list_id} not found")
    folder_id = src["folder_id"] if target_folder_id == -1 else target_folder_id

    if folder_id is None:
        sort_order = _next_sort_order(conn, "lists", "folder_id IS NULL", ())
    else:
        sort_order = _next_sort_order(conn, "lists", "folder_id = ?", (folder_id,))

    cursor = conn.execute(
        """INSERT INTO lists (folder_id, name, icon, color, sort_order)
           VALUES (?, ?, ?, ?, ?)""",
        (
            folder_id,
            (src["name"] or "") + name_suffix,
            src["icon"],
            src["color"],
            sort_order,
        ),
    )
    new_list_id = cursor.lastrowid

    item_ids = [
        r["id"] for r in conn.execute(
            "SELECT id FROM items WHERE list_id = ? ORDER BY sort_order, id",
            (list_id,),
        ).fetchall()
    ]
    for iid in item_ids:
        duplicate_item(conn, iid, target_list_id=new_list_id, name_suffix="")

    conn.commit()
    return new_list_id


def duplicate_folder(
    conn: sqlite3.Connection,
    folder_id: int,
    *,
    name_suffix: str = " (copy)",
) -> int:
    """Deep-copy a folder and all lists within it (which in turn copy items etc)."""
    src = conn.execute("SELECT * FROM folders WHERE id = ?", (folder_id,)).fetchone()
    if not src:
        raise ValueError(f"folder_id {folder_id} not found")

    sort_order = _next_sort_order(conn, "folders", "1 = 1", ())
    cursor = conn.execute(
        "INSERT INTO folders (name, icon, color, sort_order) VALUES (?, ?, ?, ?)",
        (
            (src["name"] or "") + name_suffix,
            src["icon"],
            src["color"],
            sort_order,
        ),
    )
    new_folder_id = cursor.lastrowid

    list_ids = [
        r["id"] for r in conn.execute(
            "SELECT id FROM lists WHERE folder_id = ? ORDER BY sort_order, id",
            (folder_id,),
        ).fetchall()
    ]
    for lid in list_ids:
        duplicate_list(conn, lid, target_folder_id=new_folder_id, name_suffix="")

    conn.commit()
    return new_folder_id
