# HA-lists

Goblin-Tools-style to-do add-on for Home Assistant — ad-hoc lists, AI task breakdown, household assignment.

Complementary to [HA-chores](https://github.com/Glitchtit/HA-chores) (which owns recurring, gamified household obligations). HA-lists is the home for **projects** and **notes** — things you capture once and work through.

## Features (target v1)

- **Folders → lists → items → subtasks** four-level hierarchy
- **Spiciness-driven AI breakdown** (1–5 peppers: from a clean hand-off to step-by-step micro-tasks)
- **Estimator** — time range per item
- **Compiler** — paste a brain-dump, AI turns it into a structured list
- **Formalizer** — rewrite a note's tone
- **Household assignment** — any household member, synced from HA
- **HA entities** — todo-per-list, todo-per-person, calendar for due dates, open/overdue sensors

## Install

### Add-on

Part of the [Glitchtit HA-apps repository](https://github.com/Glitchtit/HA-apps). Add that repository to Home Assistant and install the **Lists** add-on from the add-on store.

### Custom integration (optional)

Installs HA entities: sensors for open/overdue counts per person, a todo entity per list, and a calendar for due dates.

**Via HACS (recommended)**

1. In HACS → Integrations → ⋮ → Custom repositories, add `https://github.com/Glitchtit/HA-lists` as category **Integration**.
2. Install **Lists** from HACS and restart Home Assistant.
3. Go to **Settings → Devices & Services → Add Integration** and search for **Lists**.
4. Enter the add-on URL (auto-discovered if the add-on is running, default `http://a0d7b954_ha_lists:8099`).

**Manual**

Copy `custom_components/ha_lists/` into your HA `config/custom_components/` folder and restart. Then follow step 3–4 above.

## Develop

```bash
# Backend
cd lists/app && pip install -r ../requirements.txt && python -m pytest tests/ -v

# Frontend
cd lists/frontend && npm install && npm run dev
```

## License

MIT — see the umbrella repo.
