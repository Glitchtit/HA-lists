## 1.3.1

- **Slash commands** — type `/` at the start of a new line to open a quick-insert menu, just like Notion / Obsidian's Slash Commander. Choose from H1/H2/H3, bullet/numbered/checklist lists, quote, divider, code block, callout, table, wikilink, embed, today's date, current time. Filter as you type; ArrowUp/Down to navigate, Enter or Tab to insert, Esc to dismiss. Trigger only fires at column 0 so `/` mid-word doesn't disturb URLs or paths

## 1.3.0

- **Open wikilink in background tab** — Ctrl/Cmd-click any `[[wikilink]]` in the preview to open the target in a new tab *without* navigating away from your current note. Mirrors Obsidian's "Open in new tab" gesture. Toast confirms the new tab opens; existing pin/cap behaviour applies

## 1.2.9

- **Tag autocomplete** — typing `#` followed by a letter in the editor pops a floating tag picker, same UX as the wikilink one. Filtered by substring against every tag your notes already use (with counts); picking inserts `#tag ` at the cursor. Trigger only fires at line start or after whitespace, so existing hashes in words / URLs are left alone

## 1.2.8

- **Wikilink autocomplete** — typing `[[` in the editor pops a floating note-title picker beneath the cursor, just like Obsidian. Filter as you type; ArrowUp/Down to navigate, Enter or Tab to insert `[[Title]]` and close the brackets, Esc to dismiss. Notes are cached for 5 seconds to keep keystrokes snappy; cache invalidates when you switch notes or rename one. Trigger only fires inside a `[[…` that hasn't been closed, so existing wikilinks aren't disturbed

## 1.2.7

- **Custom CSS snippets** — Obsidian's appearance-snippets feature. Click 🎨 in the sidebar header to paste arbitrary CSS that gets injected into a single `<style id="lists-custom-css">` tag in `<head>`. Persists per-browser in `localStorage` (`lists_custom_css`); applied automatically on every load. Use the existing CSS variables and class hooks like `.note-preview`, `.wikilink`, `var(--brand-orange)` to restyle the app without touching code

## 1.2.6

- **Extract selection to new note** — Obsidian's note-refactoring command. Select any text in the editor (source or split mode), click ✂️ Extract in the toolbar, name the new note (the first non-heading line is suggested), and: a fresh note is created in the same folder, your selection becomes its body, and the selection in the original note is replaced with a `[[wikilink]]` to the new one. Toast confirms the extraction; sidebar refreshes so the new note shows up immediately

## 1.2.5

- **Workspaces** — Obsidian's saved-layout feature. Click 💼 in the sidebar header to open the workspaces modal: name your current tab strip + active tab and Save; click any saved entry to restore those tabs (including pin state) and re-activate the entity that was focused. Stored per-browser in `localStorage` (`lists_workspaces`); saving the same name overwrites. Useful for "work mode" vs "writing mode" presets

## 1.2.4

- **Pinned tabs** — right-click a tab to pin (or unpin) it. Pinned tabs render with a 📌 prefix in International Orange, sort to the front of the tab strip, and survive the 12-tab cap when older unpinned tabs would otherwise auto-drop. Mirrors Obsidian's pinned-tab behaviour for "keep this file open while I navigate around"

## 1.2.3

- **Editable Properties panel** — the YAML frontmatter Properties box above the rendered body is now an inline editor. Click any value to change it, ✕ to remove a key, `+` (or the empty-state button) to add a new property. Values are parsed lightly: `[a, b, c]` becomes a list, `true/false/null/123` get their typed forms, otherwise it's a string. Round-tripped into the note body via a small YAML serializer — your existing block-list `tags:` will normalise to flow form `[a, b]` on next edit

## 1.2.2

- **Find in note (Ctrl+F)** — wired up CodeMirror's official `@codemirror/search` extension, so the editor now exposes a full-featured search panel with case-sensitivity, whole-word, regex, replace, and prev/next navigation. Ctrl+F from preview mode auto-switches the editor to Split so the search panel is visible. Selection-match highlighting is on by default

## 1.2.1

- **Keyboard shortcuts cheat-sheet** — press `?` anywhere outside an input to open a modal listing every keybinding the app knows about, grouped by Navigation / Editing / Boards. Mirrors Obsidian's hotkeys help overlay. Press `Esc` (or click outside) to dismiss

## 1.2.0

- **Tabs** — multiple lists / notes / boards stay open across the top of the workspace, just like Obsidian's tabs. Opening any entity adds it to the tab strip (capped at 12, oldest dropped); the active tab is highlighted in cobalt and shows the entity icon + title. Click a tab to switch, click ✕ to close — closing the active tab falls back to the previous one. Tabs for archived/deleted entities render dimmed so you can still close them

## 1.1.9

- **Export note to `.md`** — new ⬇️ .md button in the note toolbar downloads the current note as a UTF-8 markdown file. Filename is the sanitised note title (no path separators or wildcards, capped at 120 chars). Body gets an H1 prepended if the title isn't already the first heading, so the export round-trips nicely to other markdown apps

## 1.1.8

- **Outgoing links pane** — symmetric counterpart to backlinks. The right pane now has an "Outgoing" tab listing every wikilink / embed in the current note, with each target resolved to its note (via title-or-alias lookup) and a clear "unresolved" badge for dangling links. Embeds are tinted orange to match the graph view's edge colours. Backed by new `GET /api/notes/{id}/outgoing`
- Fix Tags pane navigation — clicking a note inside a tag bucket now jumps to it (was previously broken due to a payload shape mismatch with the parent's onSelect handler)

## 1.1.7

- **Note templates** — Obsidian-style template library for new notes (separate from the board templates added in 0.9.4). Six seeded system templates: Daily journal, Meeting note, Book review, Project brief, Bug report, Cornell notes. Click 📋 in the sidebar header to open the picker; selecting a template creates a note in the same folder you're working in, with `{{date}}`, `{{time}}`, `{{title}}`, `{{datetime}}`, and parameterised `{{date:%Y-%m}}`-style variables substituted. CRUD endpoints under `/api/note-templates/` let you save your own templates; system templates are read-only

## 1.1.6

- **Pinned (Bookmarks) sidebar section** — Obsidian's Bookmarks pane equivalent. The sidebar now surfaces a top-level 📌 Pinned section above Recent, listing every pinned note and board (alphabetically) so you can jump back to important docs with one click. Pin/unpin via the existing right-click context menu — no schema changes; the section just elevates the existing `pinned` flag

## 1.1.5

- **Unlinked mentions** — Obsidian-style sister panel to backlinks. The Backlinks tab now shows two sections: actual wikilink/embed references *and* a new "Unlinked mentions" group of notes whose body contains this note's title (or any alias) literally but doesn't link to it. Word-boundary matching so `Project Atlas` doesn't match `XProject Atlas2`; mentions that already appear in brackets are filtered out so you only see text that *could* be linked. Served by new `GET /api/notes/{id}/unlinked_mentions`

## 1.1.4

- **Folder notes** — pin one note as a folder's "index" page, just like the Obsidian Folder Notes community plugin. Right-click a folder → **Set folder note** to pick any note inside it; the folder header then becomes a clickable dotted-underline link that opens that note. Right-click again to change or clear. Backend: `folders.folder_note_id` (nullable FK with `ON DELETE SET NULL`) + idempotent migration for existing DBs; PATCH validates the referenced note exists

## 1.1.3

- **Tags pane** — Obsidian-style tag aggregation. Right-pane now has a Tags tab that lists every `#tag` used across notes (count desc, then alphabetical). Picks up tags from inline body hashtags **and** frontmatter `tags:` (both flow `[a, b]` and block-list forms). Skips fenced code blocks so `# python` shebangs don't yield bogus tags. Click a tag to expand the notes that contain it; click a note to jump there. Served by new `GET /api/notes/tags`

## 1.1.2

- **Graph view** — Obsidian's signature feature. Click 🕸️ in the sidebar header to open a force-directed graph of every non-archived note, with edges drawn for resolved wikilinks (cobalt) and embeds (orange). Node radius scales with link degree, hover dims unrelated edges, click jumps into that note. Backend serves the graph via `GET /api/notes/graph`; aliases resolve as edges to the canonical note, dangling links and self-loops are dropped. Layout runs entirely in the browser — no extra dependencies, no service worker

## 1.1.1

- **Hover preview for wikilinks** — hovering a `[[wikilink]]` in the preview now opens a small popup with the linked note's icon, title, and the first ~700 chars of its body, just like Obsidian. 350 ms hover delay debounces accidental triggers; popup flips up if it would clip below the viewport; "not found" state shown when the target doesn't resolve

## 1.1.0

- **YAML frontmatter / Properties** — notes that start with a `---` fence block now render the parsed key/value pairs as a "Properties" panel above the body, just like Obsidian. Supports scalars (string, number, bool, null), flow lists (`tags: [a, b]`), and block lists (`tags:\n  - a\n  - b`). Common keys get a leading emoji (🏷️ tags, 🪪 aliases, 📅 date, 👤 author, 🚦 status, ⭐ priority). The frontmatter block is hidden from the rendered markdown and excluded from the editor's word count

## 1.0.9

- **Note aliases** — alternative names that wikilinks resolve to, mirroring Obsidian's frontmatter `aliases:`. New `note_aliases` table + `/api/notes/{id}/aliases` GET/POST/DELETE endpoints; `/api/notes/resolve` now falls back to alias lookup, so `[[Alt Name]]` jumps to the canonical note. Right-pane gains an Aliases tab to add/remove aliases inline; collisions with an existing note title return 409 so the canonical title always wins

## 1.0.8

- **Random note** — new 🎲 button in the sidebar header opens a uniformly-random non-archived note (skipping the currently-open one when possible). Mirrors Obsidian's Random Note core plugin; useful for surprise re-discovery of older notes

## 1.0.7

- **Recent files** — sidebar now shows a 🕘 Recent section listing the last five lists/notes/boards you opened, ordered most-recent-first. Clicking jumps back to that entity; archived and deleted entries auto-fall out. State persists per-browser in `localStorage` (`lists_recent`), mirroring Obsidian's Recent Files core plugin

## 1.0.6

- **Word & character count** — the note editor now shows a live `N words · N characters` status bar at the bottom of the workspace, just like Obsidian's footer. Counts strip code fences, inline code, callout markers, and wikilink brackets so the number reflects prose, not markdown plumbing

## 1.0.5

- **Daily notes** — Obsidian-style date-titled notes for journaling. Click 📅 Today in the sidebar header, or press `Ctrl+Alt+T` from anywhere, to open today's note (auto-created on first use with title `YYYY-MM-DD` and 📅 icon). New `POST /api/notes/daily?date=YYYY-MM-DD` endpoint creates-or-returns a daily note for any date, so future calendar / weekly views can hook into it

## 1.0.4
- Add **"What's new"** popup — when you open Lists after an update, a dismissable modal shows the changelog entries for every version released since your last visit. Markers persist per-browser via `localStorage` (`lists_whatsnew_lastSeen`); first visit silently marks the current version as seen so users don't get a wall of historical changelog on first install

## 1.0.3

- Fix sticky card body text: use prose-neutral on light-background cards so body text inherits dark colour

## 1.0.2

- Fix board card checkboxes: clicking a `- [ ]` checkbox now toggles it (native toggle was blocked by `preventDefault`)

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
