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

Part of the [Glitchtit HA-apps repository](https://github.com/Glitchtit/HA-apps). Add that repository to Home Assistant and install from the add-on store.

## Develop

```bash
# Backend
cd lists/app && pip install -r ../requirements.txt && python -m pytest tests/ -v

# Frontend
cd lists/frontend && npm install && npm run dev
```

## License

MIT — see the umbrella repo.
