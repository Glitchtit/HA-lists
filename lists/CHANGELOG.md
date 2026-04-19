## 1.0.1

- Board cards now auto-expand vertically to fit all content (height is no longer locked; ReactFlow measures natural DOM height)
- Sticky/light-background cards get black text in preview mode and a square minimum height (minHeight = card width); textarea stays white-text on its own dark background for visibility

## 1.0.0

- Fix board card checkboxes: clicking a `- [ ] task` checkbox now toggles it and saves immediately (onToggleChecklist was never wired to CardNode's NotePreview)

## 0.9.9

- Drag & drop lists, notes, and boards between folders in the sidebar; drop on a folder to move into it, drop on the Unfiled section to remove from all folders; drop targets highlight with a blue ring on hover

## 0.9.8

- Fix: dragging a card out of a group frame now clears its group membership (parent_group_id was never set to null when dropped outside all groups)

## 0.9.7

- Fix board image attachments returning 404 when the URL ends in a file extension (nginx `^~` prefix match for `/api/` prevents static-asset regex from intercepting API routes)
- Fix board template picker: inserting a template now actually creates the card (null color/width/height values caused Pydantic 422 validation failure, silently swallowed)

## 0.9.6

- Fix context menus: Change icon and Move to folder submenus are now reachable and their items can be clicked (fixed hover race + mousedown-before-click race with portaled submenus)

## 0.9.5

- Fix startup crash on upgrade (`sqlite3.OperationalError: no such column: parent_group_id`): run board_nodes column migration before executing the base SCHEMA so that indexes referencing newer columns succeed on older databases

## 0.9.4

- Card templates: pick from a starter library (Sticky, Checklist, Meeting note, Link bookmark, Code snippet, Quote) via the new 🧩 Templates toolbar button or press `t` on the canvas to open the picker at the cursor
- Quick capture: press `c` on the canvas to drop a blank card at the cursor
- User templates: create, rename, and delete your own templates through the `/api/board-templates` CRUD endpoints (system templates remain read-only)

## 0.9.3

- Global search: press ⌘K / Ctrl+K anywhere to open a palette that searches boards, notes, and card bodies with FTS5 ranking and prefix matching
- Boards: new 🔗 Backlinks drawer shows every board that portals into this board and every card that wikilinks to it; one click jumps to the source
- Notes: new `/api/notes/{id}/board_backlinks` endpoint exposes board refs + card mentions for future note-side panels
- Backend: FTS5 `search_index` auto-populates and stays in sync via triggers on boards / notes / card-kind board_nodes; falls back to LIKE scans on SQLite builds without FTS5

## 0.9.2

- Boards: new `board` portal node — embed any board on the canvas and double-click to navigate into it
- Boards: portals show live node/edge counts and a last-modified timestamp; stale portals become tombstones if the target board is deleted
- Boards: drag a board from the sidebar onto the canvas, or use the 🗂️ Add board toolbar picker
- Boards: backend rejects self-referential portals and keeps `ref_summary` in sync with the target board

## 0.9.1

- Boards: new `group` node — a dashed coloured frame with a title bar that corrals related cards
- Boards: drag a node onto a group to attach it; dragging the group moves all members together
- Boards: right-click any node with neighbours selected to **Group selection**; right-click a group to **Ungroup**; right-click a member to **Remove from group**
- Boards: 📦 New group toolbar button — click to drop at viewport center, or drag to place
- Boards: groups are resizable; child positions persist atomically when the parent moves

## 0.9.0

- Boards: drop, paste, or upload images and files directly onto the canvas
- Boards: new `image` node renders a thumbnail with click-to-zoom lightbox and editable alt text
- Boards: new `file` node shows MIME, size, and a download link for attachments like PDFs, zips, audio, or video
- Boards: 📎 Upload toolbar button; `Ctrl/Cmd+V` paste on the canvas creates image cards; OS file drag-drop also supported
- Boards: duplicating a board now copies its attachment files too; deleting the last node that references an attachment purges the file from disk

## 0.8.7

- Boards: removed confusing Strict/Loose connect toggle; strict mode is now always on (hover a node to see handle dots, drag from them to connect)

## 0.8.6

- Fix: board note cards no longer crash with "Syntax error" from mermaid — mermaid blocks render as a `📊 Diagram` placeholder in card previews; truncated code fences are auto-closed

## 0.8.5

- Fix: notes now correctly open in Preview mode (editorMode state was in App.jsx, not NoteEditor)

## 0.8.4

- Notes: default mode is now Preview (was Split) — click Source or Split in the toolbar to edit
- Notes: Outline/Backlinks sidebar is hidden by default; shows a slim ☰ Outline toggle button; ✕ to hide

## 0.8.3

- Boards: fix newly-added list/note nodes showing "deleted" immediately — POST response has no ref_summary so the optimistic node now carries the known item data as ref_summary
- Boards: tighten tombstone detection to only fire when ref_id is set but ref_summary is absent (genuine deletion), not simply missing on fresh nodes

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
