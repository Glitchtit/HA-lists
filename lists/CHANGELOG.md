## 0.1.0

- Initial scaffold: add-on manifest, Dockerfile (multi-stage), nginx reverse proxy with ingress-path injection, s6-overlay services
- FastAPI backend skeleton with SQLite schema at `/data/lists.db` (folders, lists, items, subtasks, tags)
- CRUD routers for folders, lists, items, subtasks, tags
- Persons sync from Home Assistant (6-hour refresh)
- Frontend shell: React 18 + Vite + Tailwind, folder sidebar / list view / item detail
- Backend test suite with tmp_db fixture
