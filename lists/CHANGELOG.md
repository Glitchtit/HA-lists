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
