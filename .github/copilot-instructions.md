# Copilot Instructions for HA-lists

## Overview

**Lists** is a Home Assistant add-on for ad-hoc task management — inspired by Goblin Tools. Folders → lists → items → subtasks, with spiciness-driven AI breakdown (planned), time estimates, household assignment, and tagging. Add-on slug: `ha_lists`. **No companion custom integration** — it is an add-on only.

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

## Architecture

Two s6-overlay services:

1. **lists** (nginx on port 8099) — serves React SPA, proxies `/api/*` to the backend, injects ingress path.
2. **lists-api** (FastAPI/uvicorn on port 8100) — REST API, SQLite database.

nginx waits for `/api/health` before starting (30 × 2s retry). nginx forwards `X-Remote-User-Id`, `X-Remote-User-Name`, and `X-Remote-User-Display-Name` headers from HA ingress to the backend — use these for `assigned_to` / `completed_by` without requiring a separate auth step.

## Config options

```json
{
  "debug": false,
  "timezone": ""   // optional; falls back to HA's timezone via Supervisor API
}
```

## Data model

Four-level hierarchy: **Folder → List → Item → Subtask**. All CASCADE on DELETE.

Key item fields:
- `spiciness` (1–5): complexity dial — placeholder for AI breakdown depth.
- `estimate_min` / `estimate_max`: time range in minutes.
- `assigned_to`: `person.entity_id` FK — persons synced from HA on startup and every 6 hours.
- `status`: `open | completed | archived`.
- `tags`: m2m through `item_tags`.

Database at `/data/lists.db`. SQLite with WAL + foreign keys enabled.

## Routers

| Router | Prefix | Notes |
|---|---|---|
| `health.py` | `/api` | `GET /api/health` → `{status, version, db_tables}` |
| `folders.py` | `/api/folders` | CRUD; `?include_archived=true` to see archived |
| `lists.py` | `/api/lists` | CRUD; filter by `?folder_id=` |
| `items.py` | `/api/items` | CRUD + `/complete` + `/reopen` + tag attach/detach |
| `subtasks.py` | `/api/subtasks` | CRUD; filter by `?item_id=` |
| `tags.py` | `/api/tags` | CRUD |
| `persons.py` | `/api/persons` | Read + HA sync trigger |

Shared helpers in `routers/_crud.py`: `apply_update()` (dynamic partial UPDATE) and `coerce_bool_cols()` (SQLite INTEGER → Python bool).

## Frontend structure

Unlike other apps in the ecosystem, Lists splits UI into components rather than a single `App.jsx`:

- `App.jsx` — state root, loads folders/lists/persons, wires layout.
- `components/Sidebar.jsx` — folder tree + list picker.
- `components/ItemList.jsx` — items for selected list.
- `components/ItemDetail.jsx` — item detail panel with subtasks and tags.
- `api.js` — centralized Axios client; reads `<meta name="ingress-path">` at startup.

## Tests

Fixtures in `tests/conftest.py`:
- `tmp_db` — fresh SQLite file per test via `monkeypatch` + `DATA_DIR` env override.
- `client` — `TestClient` with HA person sync stubbed out (avoids Supervisor socket).

## Key conventions

- **Ingress-aware.** All API calls use `${INGRESS_PATH}/api/...`. nginx strips the ingress prefix on the backend side via `X-Ingress-Path` header middleware in `main.py`.
- **Persons are read-only from the add-on's perspective.** Never write to HA entities — persons are cached locally and refreshed from HA.
- **Spiciness is the AI hook.** Items have a `spiciness` field (1–5 peppers) that will drive how deeply the AI breaks down a task into subtasks. AI subtasks are flagged with `ai_generated = True` in the subtasks table.
- **Dark theme, GlitchyRee design system.** `bg-gray-900` root, `bg-gray-800` sidebar/cards. See `Design system/project/` in the umbrella repo.

## Versioning and changelog

Both files must be updated together on every user-facing change:

| File | Field |
|---|---|
| `lists/config.json` | `"version": "X.Y.Z"` |
| `lists/CHANGELOG.md` | New `## X.Y.Z` section |

CHANGELOG format: plain `## X.Y.Z` headers, flat bullet list, no dates, no categories. Newest first.
