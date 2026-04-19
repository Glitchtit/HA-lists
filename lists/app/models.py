"""HA-lists — Pydantic request/response models."""

from __future__ import annotations
from typing import Literal

from pydantic import BaseModel, Field


# ── Health ────────────────────────────────────────────────────────────────────


class HealthResponse(BaseModel):
    status: str
    version: str
    db_tables: int


# ── Folders ───────────────────────────────────────────────────────────────────


class FolderCreate(BaseModel):
    name: str
    icon: str = "📁"
    color: str = ""
    sort_order: int = 0


class FolderUpdate(BaseModel):
    name: str | None = None
    icon: str | None = None
    color: str | None = None
    sort_order: int | None = None
    archived: bool | None = None


class Folder(BaseModel):
    id: int
    name: str
    icon: str
    color: str
    sort_order: int
    archived: bool
    created_at: str
    updated_at: str


# ── Lists ─────────────────────────────────────────────────────────────────────


class ListCreate(BaseModel):
    name: str
    folder_id: int | None = None
    icon: str = "📋"
    color: str = ""
    sort_order: int = 0


class ListUpdate(BaseModel):
    name: str | None = None
    folder_id: int | None = None
    icon: str | None = None
    color: str | None = None
    sort_order: int | None = None
    archived: bool | None = None


class List_(BaseModel):
    """Named List_ to avoid shadowing the builtin; serialized as 'list'."""
    id: int
    folder_id: int | None
    name: str
    icon: str
    color: str
    sort_order: int
    archived: bool
    created_at: str
    updated_at: str


# ── Items ─────────────────────────────────────────────────────────────────────


ItemStatus = Literal["open", "completed", "archived"]


class ItemCreate(BaseModel):
    list_id: int
    title: str
    notes: str = ""
    assigned_to: str | None = None
    due_at: str | None = None
    priority: int = 0
    estimate_min: int | None = None
    estimate_max: int | None = None
    spiciness: int = Field(3, ge=1, le=5)
    sort_order: int = 0


class ItemUpdate(BaseModel):
    list_id: int | None = None
    title: str | None = None
    notes: str | None = None
    status: ItemStatus | None = None
    assigned_to: str | None = None
    due_at: str | None = None
    priority: int | None = None
    estimate_min: int | None = None
    estimate_max: int | None = None
    spiciness: int | None = Field(None, ge=1, le=5)
    sort_order: int | None = None


class Item(BaseModel):
    id: int
    list_id: int
    title: str
    notes: str
    status: ItemStatus
    assigned_to: str | None
    due_at: str | None
    priority: int
    estimate_min: int | None
    estimate_max: int | None
    spiciness: int
    sort_order: int
    created_at: str
    updated_at: str
    completed_at: str | None
    completed_by: str | None
    tags: list[str] = []


# ── Subtasks ──────────────────────────────────────────────────────────────────


SubtaskStatus = Literal["open", "completed"]


class SubtaskCreate(BaseModel):
    item_id: int
    title: str
    sort_order: int = 0
    ai_generated: bool = False


class SubtaskUpdate(BaseModel):
    title: str | None = None
    status: SubtaskStatus | None = None
    sort_order: int | None = None


class Subtask(BaseModel):
    id: int
    item_id: int
    title: str
    status: SubtaskStatus
    sort_order: int
    ai_generated: bool
    created_at: str
    completed_at: str | None


# ── Tags ──────────────────────────────────────────────────────────────────────


class TagCreate(BaseModel):
    name: str
    color: str = ""


class TagUpdate(BaseModel):
    name: str | None = None
    color: str | None = None


class Tag(BaseModel):
    id: int
    name: str
    color: str
    created_at: str


# ── Persons ───────────────────────────────────────────────────────────────────


class Person(BaseModel):
    entity_id: str
    name: str
    ha_user_id: str
    avatar_url: str
    active: bool
    created_at: str


# ── Notes ─────────────────────────────────────────────────────────────────────


class NoteCreate(BaseModel):
    title: str
    body: str = ""
    folder_id: int | None = None
    icon: str = "📝"
    color: str = ""
    pinned: bool = False
    sort_order: int = 0


class NoteUpdate(BaseModel):
    title: str | None = None
    body: str | None = None
    folder_id: int | None = None
    icon: str | None = None
    color: str | None = None
    pinned: bool | None = None
    archived: bool | None = None
    sort_order: int | None = None


class Note(BaseModel):
    id: int
    folder_id: int | None
    title: str
    body: str
    icon: str
    color: str
    pinned: bool
    archived: bool
    sort_order: int
    ai_generated: bool
    created_at: str
    updated_at: str


class BacklinkEntry(BaseModel):
    note_id: int
    title: str
    snippet: str
    link_type: str


# ── Boards ────────────────────────────────────────────────────────────────────


class BoardCreate(BaseModel):
    name: str
    folder_id: int | None = None
    icon: str = "🧩"
    color: str = ""
    pinned: bool = False
    sort_order: int = 0


class BoardUpdate(BaseModel):
    name: str | None = None
    folder_id: int | None = None
    icon: str | None = None
    color: str | None = None
    pinned: bool | None = None
    archived: bool | None = None
    sort_order: int | None = None


class Board(BaseModel):
    id: int
    folder_id: int | None
    name: str
    icon: str
    color: str
    pinned: bool
    archived: bool
    sort_order: int
    viewport: dict
    created_at: str
    updated_at: str


class ViewportUpdate(BaseModel):
    x: float = 0
    y: float = 0
    zoom: float = 1


NodeKind = Literal["list", "note", "card"]


class BoardNodeCreate(BaseModel):
    kind: NodeKind
    ref_id: int | None = None
    title: str = ""
    body: str = ""
    color: str = ""
    x: float = 0
    y: float = 0
    width: float = 240
    height: float = 160
    z: int = 0


class BoardNodeUpdate(BaseModel):
    title: str | None = None
    body: str | None = None
    color: str | None = None
    x: float | None = None
    y: float | None = None
    width: float | None = None
    height: float | None = None
    z: int | None = None


class BoardNode(BaseModel):
    id: int
    board_id: int
    kind: NodeKind
    ref_id: int | None
    title: str
    body: str
    color: str
    x: float
    y: float
    width: float
    height: float
    z: int
    ref_summary: dict | None = None
    created_at: str
    updated_at: str


class BoardNodeBulkPositionEntry(BaseModel):
    id: int
    x: float
    y: float


class BoardNodeBulkPositions(BaseModel):
    positions: list[BoardNodeBulkPositionEntry]


class BoardEdgeCreate(BaseModel):
    source_node_id: int
    target_node_id: int
    label: str = ""
    style: str = "default"


class BoardEdgeUpdate(BaseModel):
    label: str | None = None
    style: str | None = None


class BoardEdge(BaseModel):
    id: int
    board_id: int
    source_node_id: int
    target_node_id: int
    label: str
    style: str
    created_at: str


class BoardDetail(BaseModel):
    board: Board
    nodes: list[BoardNode]
    edges: list[BoardEdge]
