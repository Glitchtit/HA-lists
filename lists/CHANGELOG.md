## 0.8.2

- Boards: fix "+ Card / List / Note" buttons not adding anything (trailing-slash mismatch between frontend and FastAPI routes)
- Boards: drag nodes from the toolbar to place them exactly, or click to drop at viewport center
- Boards: drag lists and notes straight from the sidebar onto the board canvas
- Boards: clearer toolbar iconography (🗒️ card / 📋 list / 📄 note / ⇄ connect) with labels
- Boards: use `screenToFlowPosition` for accurate drop coordinates under pan/zoom

## 0.8.1

- Sidebar: consistent icons for new list (📋), note (📄) and board (🗂️) creation buttons — replaces ambiguous bare +

## 0.8.0

- Boards: infinite-canvas workspace (reactflow) with List, Note and Card nodes
- Boards: connect nodes with directional edges; bulk-move autosave
- Boards: right-click context menu for nodes/edges; keyboard delete with input guard
- Boards: tombstone rendering when a referenced list or note has been deleted
- Boards: pan/zoom viewport persisted per board
- Sidebar: boards listed per folder with full context menu (rename, duplicate, move, pin, archive, delete)
- API: new /api/boards endpoints (CRUD, duplicate, bulk positions, viewport, nodes, edges)

## 0.7.0

- Notes — new Obsidian-parity markdown note system (wikilinks, embeds, backlinks, callouts, KaTeX, Mermaid, code highlighting, GFM tables, clickable checklists)
- Split-view editor (CodeMirror source + live preview) with solo toggles
- Note-specific AI actions: summarize, continue, rewrite-in-tone, extract tasks to a list, generate outline
- Unified sidebar: folders now hold Lists and Notes together
- Right-side panel shows Outline + Backlinks for the active note
- Keyboard shortcuts: Ctrl+N (new note), Ctrl+Enter (toggle preview)

## 0.6.0

- PC-style right-click context menus on folders, lists, items, subtasks and tag chips
- Deep-copy duplicate for folders, lists and items via new `/duplicate` endpoints
- Move lists across folders (or to Unfiled) and items between lists straight from the menu
- Inline rename (F2) for folders, lists, items and subtasks; confirm dialog on delete
- Assign / Spiciness / Priority / Change-icon submenus; tag rename, recolor, detach, delete-globally
- Keyboard shortcuts: F2 rename, Delete (with confirm), Ctrl+D duplicate item
- Tag rename now returns 409 instead of 500 on unique-name collision

## 0.5.0

- AI provider is now configured directly in the add-on options (no Storage dependency)
- Add `ai_provider` (gemini/claude/ollama), `ai_gemini_api_key`, `ai_gemini_model`,
  `ai_claude_api_key`, `ai_claude_model`, `ai_ollama_url`, `ai_ollama_model` to add-on schema
- AI config is read from `/data/options.json` at runtime; changes take effect on next restart

## 0.4.0

- Design-system polish: apply GlitchyRee tokens (International Orange + Cobalt Blue) across the frontend
- Self-host Space Grotesk / Inter / JetBrains Mono via `public/fonts/` + `src/styles/design-tokens.css`
- Tailwind extended with `brand.*`, `surface.*`, `ink.*`, `semantic.*` colour tokens
- Spiciness slider gets a custom orange→gold gradient track with a glowing thumb
- AI job toast uses cobalt + shimmer animation; compile/detail dialogs use 2xl radii and brand glows
- Sidebar and list headers switch to the Space Grotesk display face

## 0.3.0

- Goblin-Tools-style AI features powered by the HA-storage provider config
- `POST /api/ai/breakdown` — spiciness-driven subtask breakdown (async, single-flight per-kind)
- `POST /api/ai/estimate` — AI time estimate, writes `estimate_min`/`estimate_max` onto the item
- `POST /api/ai/compile` — brain-dump → ordered items appended to a list (async)
- `POST /api/ai/formalize` — rewrite text in one of five tones (formal / casual / concise / kind / firm)
- `GET /api/ai/jobs/{task_id}` — poll async jobs for status, logs, and result
- Frontend: ✨ Compile dialog on list header, 🪄 Break down / ⏱️ Estimate / ✏️ Formalize buttons in item detail, AI job toast for async progress
- AI-generated subtasks are tagged in the DB (`ai_generated=1`) and re-running breakdown replaces only the AI-generated ones

## 0.2.0

- Paired Home Assistant custom integration `ha_lists` at submodule root
- Config flow with Supervisor add-on auto-discovery + `/api/health` connection test
- DataUpdateCoordinator polls the add-on every 60 s (health, persons, lists, open items)
- Todo entities: one per non-archived list, one per active person; toggling completion hits `POST /api/items/{id}/complete` or `/reopen`
- Sensors: household overdue count, household open count, per-person open count
- Calendar entity surfaces items with `due_at` in the HA calendar
- Sidebar iframe panel registered on config entry setup, pointing at the add-on ingress URL

## 0.1.0

- Initial scaffold: add-on manifest, Dockerfile (multi-stage), nginx reverse proxy with ingress-path injection, s6-overlay services
- FastAPI backend skeleton with SQLite schema at `/data/lists.db` (folders, lists, items, subtasks, tags)
- CRUD routers for folders, lists, items, subtasks, tags
- Persons sync from Home Assistant (6-hour refresh)
- Frontend shell: React 18 + Vite + Tailwind, folder sidebar / list view / item detail
- Backend test suite with tmp_db fixture
