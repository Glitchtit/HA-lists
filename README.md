<p align="center">
  <img src="https://raw.githubusercontent.com/Glitchtit/HA-lists/main/lists/logo.png" alt="Lists" height="72">
</p>

<p align="center">
  <b>Lists, notes and boards with AI task breakdown for your household</b><br>
  Part of Glitchtit's HA apps — runs on its own, no Storage add-on needed.
</p>

<p align="center">
  <a href="https://github.com/Glitchtit/HA-apps"><img alt="Home Assistant add-on" src="https://img.shields.io/badge/Home%20Assistant-add--on-0047AB?style=flat-square&logo=homeassistant&logoColor=white"></a>
  <img alt="Version" src="https://img.shields.io/badge/dynamic/json?style=flat-square&color=FF4F00&label=version&url=https%3A%2F%2Fraw.githubusercontent.com%2FGlitchtit%2FHA-lists%2Fmain%2Flists%2Fconfig.json&query=%24.version">
  <a href="https://hacs.xyz"><img alt="HACS custom" src="https://img.shields.io/badge/HACS-custom-1F2937?style=flat-square"></a>
</p>

<p align="center">
  <img src="https://raw.githubusercontent.com/Glitchtit/HA-lists/main/docs/screenshots/hero.png" alt="Lists screenshot" width="100%">
</p>

## ✨ Features

- **Folders → lists → items → subtasks** — organise tasks in folders, give each item notes, a due date, a priority, tags and a checklist of subtasks. Duplicate folders, lists and items, or move items between lists, from the right-click menu.
- **Spiciness-based AI breakdown** — rate an item 1–5 🌶️ and press **Break down**: the AI splits it into subtasks, with more and smaller steps the spicier it is. Re-running replaces the earlier AI subtasks.
- **More Goblin-Tools-style helpers** — an AI time estimate per item, a brain-dump compiler that turns pasted text into list items, and a tone rewriter (formal, casual, concise, kind, firm) for item notes.
- **Household assignment** — assign items to any Home Assistant person; people are synced from HA at startup and every 6 hours.
- **Markdown notes** — wikilinks with backlinks, embeds, aliases, tags, frontmatter properties, daily notes with a calendar, note templates, a graph view, callouts, KaTeX and Mermaid. AI can summarize, continue, rewrite or outline a note, or pull its tasks into a list.
- **Boards** — a canvas of cards, lists, notes, images, files, groups and links to other boards, joined with edges. Cards snap into alignment and come from a small template library.
- **Search and tabs** — Ctrl+K searches boards, notes and cards; open lists, notes and boards stay in a tab strip you can pin and save as workspaces.

## 🚀 Installation

### Add-on

1. In Home Assistant open **Settings → Add-ons → Add-on Store → ⋮ → Repositories** and add `https://github.com/Glitchtit/HA-apps`
2. Install **Lists** (it does not need any other add-on)
3. On the **Configuration** tab pick an `ai_provider` and fill in its API key (or the Ollama URL) — needed only for the AI features
4. Start it and open **Lists** from the sidebar

### Integration (HACS)

1. In HACS open **⋮ → Custom repositories**, add `https://github.com/Glitchtit/HA-lists` with category **Integration**
2. Download **Lists** and restart Home Assistant
3. **Settings → Devices & services → Add integration → Lists** (the add-on URL is filled in from the Supervisor when the add-on is running; the integration checks `/api/health` before saving)

## ⚙️ Configuration

| Option | Default | Description |
|--------|---------|-------------|
| `debug` | `false` | Verbose backend logging |
| `timezone` | `""` | Timezone for dates and daily notes; empty uses Home Assistant's timezone |
| `ai_provider` | `gemini` | AI backend for breakdown, estimates, compile and note helpers: `gemini`, `claude` or `ollama` |
| `ai_gemini_api_key` / `ai_gemini_model` | `""` / `gemini-2.0-flash` | Google Gemini API key and model |
| `ai_claude_api_key` / `ai_claude_model` | `""` / `claude-3-5-haiku-20241022` | Anthropic API key and model |
| `ai_ollama_url` / `ai_ollama_model` | `""` / `llama3` | Base URL and model of a local Ollama server |

## 🏠 In Home Assistant

The integration polls the add-on every minute and creates:

- **Sensors** — `Lists Open` and `Lists Overdue` item counts, plus an open-item count per person
- **To-do lists** — one per list and one per person, showing open items. Check items off, rename them, set notes and due dates, or delete them from Home Assistant; items added to a list's to-do land in that list
- **Calendar** — `Lists`, with every open item that has a due date

| Action | What it does |
|--------|--------------|
| `ha_lists.create_list` | Create a list, optionally with an icon, colour and folder |
| `ha_lists.add_item` | Add an item to a list by name, with optional notes, assignee, due date, priority and spiciness |
| `ha_lists.breakdown_item` | Break an item into subtasks with AI at a chosen spiciness |
| `ha_lists.compile_braindump` | Turn freeform text into items appended to a list |
| `ha_lists.find_lists` | Return every list with its id and name |

`breakdown_item`, `compile_braindump` and `find_lists` return data: the new subtasks or items as `{id, title}`, or the lists. The AI actions wait up to about 45 s and return a `timeout` status if the job is still running.

## 🧩 The family

<p align="center">
  <a href="https://github.com/Glitchtit/HA-storage"><img src="https://raw.githubusercontent.com/Glitchtit/HA-storage/main/storage/icon.png" width="56" alt="Storage"></a>&nbsp;
  <a href="https://github.com/Glitchtit/HA-scraper"><img src="https://raw.githubusercontent.com/Glitchtit/HA-scraper/main/addon/icon.png" width="56" alt="Scraper"></a>&nbsp;
  <a href="https://github.com/Glitchtit/HA-stock"><img src="https://raw.githubusercontent.com/Glitchtit/HA-stock/main/stock/icon.png" width="56" alt="Stock"></a>&nbsp;
  <a href="https://github.com/Glitchtit/HA-recipes"><img src="https://raw.githubusercontent.com/Glitchtit/HA-recipes/main/recipes/icon.png" width="56" alt="Recipes"></a>&nbsp;
  <a href="https://github.com/Glitchtit/HA-chores"><img src="https://raw.githubusercontent.com/Glitchtit/HA-chores/main/chores/icon.png" width="56" alt="Chores"></a>&nbsp;
  <a href="https://github.com/Glitchtit/HA-lists"><img src="https://raw.githubusercontent.com/Glitchtit/HA-lists/main/lists/icon.png" width="56" alt="Lists"></a>&nbsp;
  <a href="https://github.com/Glitchtit/HA-print"><img src="https://raw.githubusercontent.com/Glitchtit/HA-print/main/print/icon.png" width="56" alt="Print"></a>
</p>

<p align="center"><sub>Lists keeps its own data and holds one-off projects and notes; recurring household jobs belong in Chores, and groceries to buy belong in Storage's shopping list.</sub></p>

## 🛠️ Development

```bash
# Backend (FastAPI + SQLite)
cd lists/app && python -m pytest tests/ -v

# Frontend (React + Vite, proxies /api to localhost:8100)
cd lists/frontend && npm install && npm run dev
```
