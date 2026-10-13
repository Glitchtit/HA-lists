# Copilot Instructions for HA-lists

## Overview

**Lists** is a Home Assistant add-on for ad-hoc task management — inspired by Goblin Tools. Folders → lists → items → subtasks, with spiciness-driven AI breakdown, AI time estimates and brain-dump compile, household assignment, and tagging. It also has Obsidian-style markdown notes (wikilinks, backlinks, daily notes), canvas boards, note/board templates, and global search. Add-on slug: `ha_lists`.

A companion HACS custom integration lives at `custom_components/ha_lists/` (domain `ha_lists`, see [Custom integration](#custom-integration) below).

## Build, test, and lint

### Backend (FastAPI + SQLite)

```bash
cd HA-lists/lists
pip install -r requirements.txt

cd app && python -m pytest tests/ -v
python -m pytest tests/test_api.py::TestItems -v
python -m pytest tests/test_api.py::TestHealth::test_health_returns_ok -v
```

No linter or formatter is configured.

### Frontend (React UI)

```bash
cd HA-lists/lists/frontend
npm install
npm run dev      # dev server — proxies /api to localhost:8100
npm run build    # production build to dist/
```

No tests or linter are configured.

### Integration helper tests

```bash
cd HA-lists
python -m pytest custom_components/ha_lists/tests/ -v   # run from the submodule root
```

Running from inside `custom_components/ha_lists/` fails: the integration's `calendar.py` shadows the stdlib `calendar` module.

## Architecture

Two s6-overlay services:

1. **lists** (nginx on port 8099) — serves React SPA, proxies `/api/*` to the backend, injects ingress path.
2. **lists-api** (FastAPI/uvicorn on port 8100) — REST API, SQLite database.

nginx waits for `/api/health` before starting (30 × 2s retry). nginx forwards `X-Remote-User-Id`, `X-Remote-User-Name`, and `X-Remote-User-Display-Name` headers from HA ingress to the backend — use these for `assigned_to` / `completed_by` without requiring a separate auth step.

## Config options

```json
{
  "debug": false,
  "timezone": "",   // optional; falls back to HA's timezone via Supervisor API
  "ai_provider": "gemini",   // gemini | claude | ollama
  "ai_gemini_api_key": "",
  "ai_gemini_model": "gemini-2.0-flash",
  "ai_claude_api_key": "",
  "ai_claude_model": "claude-3-5-haiku-20241022",
  "ai_ollama_url": "",
  "ai_ollama_model": "llama3"
}
```

AI config is read from `/data/options.json` by `app/ai/storage_client.py` (cached, re-read when the file changes). AI endpoints return 503 when the selected provider is not configured.

## Data model

Four-level hierarchy: **Folder → List → Item → Subtask**. List → Item → Subtask CASCADE on DELETE; deleting a folder sets its lists' `folder_id` to NULL.

Key item fields:
- `spiciness` (1–5): complexity dial — controls how deeply the AI breakdown splits the item.
- `estimate_min` / `estimate_max`: time range in minutes.
- `assigned_to`: `person.entity_id` FK — persons synced from HA on startup and every 6 hours.
- `status`: `open | completed | archived`.
- `tags`: m2m through `item_tags`.

Alongside the task hierarchy:
- **Notes** (`notes`, `note_links`, `note_aliases`) — markdown notes in folders; `[[wikilinks]]` / `![[embeds]]` are parsed by `routers/_wikilinks.py` into `note_links`. A folder can point at a folder note (`folder_note_id`).
- **Boards** (`boards`, `board_nodes`, `board_edges`) — ReactFlow canvases. Node `kind` is one of `list | note | card | image | file | group | board`; image/file uploads are stored under `/data/board_media`.
- **Templates** (`note_templates`, `board_templates`).

Database at `/data/lists.db`. SQLite with WAL + foreign keys enabled.

## Routers

| Router | Prefix | Notes |
|---|---|---|
| `health.py` | `/api` | `GET /api/health` → `{status, version, db_tables}` |
| `folders.py` | `/api/folders` | CRUD + `/duplicate`; `?include_archived=true` to see archived |
| `lists.py` | `/api/lists` | CRUD + `/duplicate`; filter by `?folder_id=` |
| `items.py` | `/api/items` | CRUD + `/complete` + `/reopen` + `/duplicate` + tag attach/detach; filter by `list_id`, `assigned_to`, `status`, `tag` |
| `subtasks.py` | `/api/subtasks` | CRUD + `/toggle`; filter by `?item_id=` |
| `tags.py` | `/api/tags` | CRUD |
| `persons.py` | `/api/persons` | Read + `/me` (current HA user) + `/sync` |
| `ai.py` | `/api/ai` | `breakdown` + `compile` (async jobs, poll `GET /api/ai/jobs/{id}`), `estimate` + `formalize` (sync) |
| `notes_ai.py` | `/api/ai/notes` | `summarize`, `continue`, `rewrite`, `outline`, `extract-tasks` (sync) |
| `notes.py` | `/api/notes` | CRUD + daily notes/calendar, backlinks, outgoing/unlinked mentions, aliases, tags, query, graph, vault stats |
| `boards.py` | `/api/boards` | CRUD + nodes, edges, group translate, bulk positions, viewport, attachments |
| `search.py` | `/api` | `GET /api/search` (SQLite FTS5) + board backlinks |
| `note_templates.py` | `/api/note-templates` | CRUD + `/{id}/apply` |
| `board_templates.py` | `/api/board-templates` | CRUD |

Shared helpers: `routers/_crud.py` — `apply_update()` (dynamic partial UPDATE) and `coerce_bool_cols()` (SQLite INTEGER → Python bool); `routers/_duplicate.py` — deep-duplicate for folders/lists/items; `routers/_wikilinks.py` — wikilink extraction.

AI plumbing lives in `app/ai/`: `provider.py` (Gemini/Claude/Ollama calls), `prompts.py`, `jobs.py` (in-memory job registry, single-flight per kind), `storage_client.py` (options reader).

## Frontend structure

Unlike other apps in the ecosystem, Lists splits UI into components rather than a single `App.jsx`:

- `App.jsx` — state root, loads folders/lists/notes/boards/persons, wires layout.
- `components/Sidebar.jsx` — folder tree with lists, notes and boards.
- `components/ItemList.jsx` — items for selected list.
- `components/ItemDetail.jsx` — item detail panel with subtasks, tags and AI breakdown.
- `components/notes/` — note editor (CodeMirror source view in `NoteSource.jsx`), markdown preview, backlinks, graph, templates.
- `components/boards/` — `BoardView.jsx` (ReactFlow) and per-kind node components in `nodes/`.
- `components/search/CommandPalette.jsx` — global search.
- `api.js` — centralized Axios client; reads `<meta name="ingress-path">` at startup.

## Tests

Fixtures in `tests/conftest.py`:
- `tmp_db` — fresh SQLite file per test via `monkeypatch` + `DATA_DIR` env override.
- `client` — `TestClient` with HA person sync stubbed out (avoids Supervisor socket).

## Key conventions

- **Ingress-aware.** All API calls use `${INGRESS_PATH}/api/...`. nginx forwards the `X-Ingress-Path` header and an `ingress_strip` middleware in `main.py` strips that prefix from the request path.
- **Persons are read-only from the add-on's perspective.** Never write to HA entities — persons are cached locally and refreshed from HA.
- **Spiciness drives AI breakdown.** Items have a `spiciness` field (1–5 peppers) that sets how deeply `POST /api/ai/breakdown` splits a task into subtasks. AI subtasks are flagged with `ai_generated = 1` in the subtasks table; re-running a breakdown replaces the previous AI subtasks.
- **Dark theme, GlitchyRee design system.** Lists uses token-backed Tailwind classes (`bg-surface-*`, `bg-brand-*`, `text-ink-*`) defined in `frontend/tailwind.config.js` and mapped to CSS variables in `src/styles/design-tokens.css`. See `Design system/project/` in the umbrella repo.

## Custom integration

`custom_components/ha_lists/` (HACS, `hacs.json` at the submodule root) polls the add-on every minute (`coordinator.py`) and provides:

- **Sensors** — `Lists Open`, `Lists Overdue`, and an open-item count per person.
- **To-do entities** — one per list and one per person, showing open items. Both support editing title, notes and due date, complete/reopen, and delete; only the per-list entities support creating items (new items land in that list).
- **Calendar** — `Lists`, with every open item that has a due date.
- **Services** (`services.yaml`) — `create_list`, `add_item`, `breakdown_item`, `compile_braindump`, `find_lists`. Breakdown/compile poll the add-on's AI job to completion.

The config flow discovers the add-on through the Supervisor by matching an add-on slug equal to or ending in `_ha_lists`, then uses its hostname on port 8099; the fallback default URL is `http://0a9ed235-ha-lists:8099`. The integration adds no sidebar panel of its own — the add-on's ingress panel is the UI.

## Versioning and changelog

These files must be updated together on every user-facing change:

| File | Field |
|---|---|
| `lists/config.json` | `"version": "X.Y.Z"` |
| `lists/CHANGELOG.md` | New `## X.Y.Z` section |
| `custom_components/ha_lists/manifest.json` | `"version"` — when the integration changes |

Integration changes are noted in `lists/CHANGELOG.md` as bullets prefixed `Integration X.Y.Z:`.

CHANGELOG format: plain `## X.Y.Z` headers, flat bullet list, no dates, no categories. Newest first. The frontend's What's New modal parses these headers at build time (`vite.config.js`).
