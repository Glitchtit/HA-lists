"""HA-lists — API CRUD tests."""

from __future__ import annotations


class TestHealth:
    def test_health_returns_ok(self, client):
        resp = client.get("/api/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["db_tables"] > 0


class TestFolders:
    def test_create_and_list(self, client):
        r = client.post("/api/folders/", json={"name": "Home", "icon": "🏠"})
        assert r.status_code == 201
        assert r.json()["icon"] == "🏠"

        client.post("/api/folders/", json={"name": "Work"})
        r = client.get("/api/folders/")
        assert r.status_code == 200
        assert len(r.json()) == 2

    def test_patch_and_archive(self, client):
        folder_id = client.post("/api/folders/", json={"name": "Old"}).json()["id"]
        r = client.patch(f"/api/folders/{folder_id}", json={"name": "New", "archived": True})
        assert r.json()["name"] == "New"
        assert r.json()["archived"] is True
        # Archived folders are hidden by default
        assert len(client.get("/api/folders/").json()) == 0
        assert len(client.get("/api/folders/?include_archived=true").json()) == 1

    def test_delete(self, client):
        folder_id = client.post("/api/folders/", json={"name": "Tmp"}).json()["id"]
        assert client.delete(f"/api/folders/{folder_id}").status_code == 204
        assert client.get(f"/api/folders/{folder_id}").status_code == 404


class TestLists:
    def test_create_in_folder(self, client):
        folder_id = client.post("/api/folders/", json={"name": "Projects"}).json()["id"]
        r = client.post("/api/lists/", json={"folder_id": folder_id, "name": "Trip"})
        assert r.status_code == 201
        assert r.json()["folder_id"] == folder_id

    def test_create_rejects_bad_folder(self, client):
        r = client.post("/api/lists/", json={"folder_id": 9999, "name": "X"})
        assert r.status_code == 400

    def test_filter_by_folder(self, client):
        f1 = client.post("/api/folders/", json={"name": "A"}).json()["id"]
        f2 = client.post("/api/folders/", json={"name": "B"}).json()["id"]
        client.post("/api/lists/", json={"folder_id": f1, "name": "L1"})
        client.post("/api/lists/", json={"folder_id": f1, "name": "L2"})
        client.post("/api/lists/", json={"folder_id": f2, "name": "L3"})
        client.post("/api/lists/", json={"name": "Loose"})  # no folder
        assert len(client.get(f"/api/lists/?folder_id={f1}").json()) == 2
        assert len(client.get(f"/api/lists/?folder_id={f2}").json()) == 1

    def test_folder_deletion_detaches_lists(self, client):
        folder_id = client.post("/api/folders/", json={"name": "F"}).json()["id"]
        list_id = client.post(
            "/api/lists/", json={"folder_id": folder_id, "name": "L"}
        ).json()["id"]
        client.delete(f"/api/folders/{folder_id}")
        # List survives with folder_id = NULL (ON DELETE SET NULL)
        r = client.get(f"/api/lists/{list_id}")
        assert r.status_code == 200
        assert r.json()["folder_id"] is None


class TestItems:
    def _fresh_list(self, client) -> int:
        return client.post("/api/lists/", json={"name": "L"}).json()["id"]

    def test_create_with_defaults(self, client):
        list_id = self._fresh_list(client)
        r = client.post("/api/items/", json={"list_id": list_id, "title": "Do thing"})
        assert r.status_code == 201
        data = r.json()
        assert data["status"] == "open"
        assert data["spiciness"] == 3  # default
        assert data["tags"] == []

    def test_spiciness_bounds(self, client):
        list_id = self._fresh_list(client)
        assert client.post(
            "/api/items/", json={"list_id": list_id, "title": "X", "spiciness": 6}
        ).status_code == 422
        assert client.post(
            "/api/items/", json={"list_id": list_id, "title": "X", "spiciness": 0}
        ).status_code == 422

    def test_complete_and_reopen(self, client):
        list_id = self._fresh_list(client)
        item_id = client.post(
            "/api/items/", json={"list_id": list_id, "title": "T"}
        ).json()["id"]
        r = client.post(f"/api/items/{item_id}/complete", params={"completed_by": "person.alice"})
        assert r.json()["status"] == "completed"
        assert r.json()["completed_by"] == "person.alice"
        r = client.post(f"/api/items/{item_id}/reopen")
        assert r.json()["status"] == "open"
        assert r.json()["completed_at"] is None

    def test_filter_by_status_and_list(self, client):
        list_id = self._fresh_list(client)
        other_list = self._fresh_list(client)
        client.post("/api/items/", json={"list_id": list_id, "title": "A"})
        client.post("/api/items/", json={"list_id": list_id, "title": "B"})
        client.post("/api/items/", json={"list_id": other_list, "title": "C"})
        assert len(client.get(f"/api/items/?list_id={list_id}").json()) == 2
        assert len(client.get("/api/items/?status=open").json()) == 3

    def test_tags_attach_detach(self, client):
        list_id = self._fresh_list(client)
        item_id = client.post(
            "/api/items/", json={"list_id": list_id, "title": "X"}
        ).json()["id"]
        r = client.post(f"/api/items/{item_id}/tags/urgent")
        assert "urgent" in r.json()["tags"]
        r = client.post(f"/api/items/{item_id}/tags/today")
        assert set(r.json()["tags"]) == {"urgent", "today"}
        # Tag auto-created
        assert len(client.get("/api/tags/").json()) == 2
        # Filter by tag
        assert len(client.get("/api/items/?tag=urgent").json()) == 1
        # Detach
        r = client.delete(f"/api/items/{item_id}/tags/urgent")
        assert r.json()["tags"] == ["today"]

    def test_list_deletion_cascades_items(self, client):
        list_id = self._fresh_list(client)
        item_id = client.post(
            "/api/items/", json={"list_id": list_id, "title": "X"}
        ).json()["id"]
        client.delete(f"/api/lists/{list_id}")
        assert client.get(f"/api/items/{item_id}").status_code == 404


class TestSubtasks:
    def test_toggle(self, client):
        list_id = client.post("/api/lists/", json={"name": "L"}).json()["id"]
        item_id = client.post(
            "/api/items/", json={"list_id": list_id, "title": "Parent"}
        ).json()["id"]
        st_id = client.post(
            "/api/subtasks/",
            json={"item_id": item_id, "title": "Step 1", "ai_generated": True},
        ).json()["id"]
        r = client.post(f"/api/subtasks/{st_id}/toggle")
        assert r.json()["status"] == "completed"
        assert r.json()["completed_at"] is not None
        assert r.json()["ai_generated"] is True
        r = client.post(f"/api/subtasks/{st_id}/toggle")
        assert r.json()["status"] == "open"
        assert r.json()["completed_at"] is None

    def test_item_deletion_cascades(self, client):
        list_id = client.post("/api/lists/", json={"name": "L"}).json()["id"]
        item_id = client.post(
            "/api/items/", json={"list_id": list_id, "title": "P"}
        ).json()["id"]
        st_id = client.post(
            "/api/subtasks/", json={"item_id": item_id, "title": "s"}
        ).json()["id"]
        client.delete(f"/api/items/{item_id}")
        assert client.get(f"/api/subtasks/{st_id}").status_code == 404

    def test_list_by_item(self, client):
        list_id = client.post("/api/lists/", json={"name": "L"}).json()["id"]
        i1 = client.post("/api/items/", json={"list_id": list_id, "title": "P1"}).json()["id"]
        i2 = client.post("/api/items/", json={"list_id": list_id, "title": "P2"}).json()["id"]
        client.post("/api/subtasks/", json={"item_id": i1, "title": "a"})
        client.post("/api/subtasks/", json={"item_id": i1, "title": "b"})
        client.post("/api/subtasks/", json={"item_id": i2, "title": "c"})
        assert len(client.get(f"/api/subtasks/?item_id={i1}").json()) == 2
        assert len(client.get(f"/api/subtasks/?item_id={i2}").json()) == 1


class TestTags:
    def test_unique_name(self, client):
        r1 = client.post("/api/tags/", json={"name": "red", "color": "#f00"})
        assert r1.status_code == 201
        r2 = client.post("/api/tags/", json={"name": "red"})
        assert r2.status_code == 409

    def test_delete_cascades_item_tags(self, client):
        list_id = client.post("/api/lists/", json={"name": "L"}).json()["id"]
        item_id = client.post("/api/items/", json={"list_id": list_id, "title": "X"}).json()["id"]
        client.post(f"/api/items/{item_id}/tags/work")
        tag = client.get("/api/tags/").json()[0]
        client.delete(f"/api/tags/{tag['id']}")
        # Item survives; tag is gone from its list
        assert client.get(f"/api/items/{item_id}").json()["tags"] == []


class TestPersons:
    def test_sync_upserts(self, client, monkeypatch):
        async def _fake():
            return [
                {"entity_id": "person.alice", "name": "Alice", "avatar_url": "", "user_id": "u1"},
                {"entity_id": "person.bob", "name": "Bob", "avatar_url": "", "user_id": "u2"},
            ]
        monkeypatch.setattr("ha_client.get_persons", _fake)
        r = client.post("/api/persons/sync")
        assert r.status_code == 200
        assert len(r.json()) == 2
        names = sorted(p["name"] for p in r.json())
        assert names == ["Alice", "Bob"]

    def test_deactivates_missing_persons(self, client, monkeypatch):
        async def _two():
            return [
                {"entity_id": "person.alice", "name": "Alice", "avatar_url": "", "user_id": "u1"},
                {"entity_id": "person.bob", "name": "Bob", "avatar_url": "", "user_id": "u2"},
            ]
        async def _one():
            return [
                {"entity_id": "person.alice", "name": "Alice", "avatar_url": "", "user_id": "u1"},
            ]
        monkeypatch.setattr("ha_client.get_persons", _two)
        client.post("/api/persons/sync")
        monkeypatch.setattr("ha_client.get_persons", _one)
        client.post("/api/persons/sync")
        active = client.get("/api/persons/").json()
        all_p = client.get("/api/persons/?include_inactive=true").json()
        assert len(active) == 1
        assert len(all_p) == 2
        inactive = [p for p in all_p if not p["active"]]
        assert len(inactive) == 1 and inactive[0]["entity_id"] == "person.bob"

    def test_whoami_without_header(self, client):
        r = client.get("/api/persons/me")
        assert r.status_code == 200
        assert r.json() is None

    def test_whoami_matches_ha_user_id(self, client, monkeypatch):
        async def _fake():
            return [
                {"entity_id": "person.alice", "name": "Alice", "avatar_url": "", "user_id": "u1"},
            ]
        monkeypatch.setattr("ha_client.get_persons", _fake)
        client.post("/api/persons/sync")
        r = client.get("/api/persons/me", headers={"X-Remote-User-Id": "u1"})
        assert r.status_code == 200
        assert r.json()["entity_id"] == "person.alice"

    def test_item_assignment_requires_known_person(self, client):
        list_id = client.post("/api/lists/", json={"name": "L"}).json()["id"]
        r = client.post(
            "/api/items/",
            json={"list_id": list_id, "title": "X", "assigned_to": "person.ghost"},
        )
        assert r.status_code == 400


class TestIngressStrip:
    """The middleware should strip X-Ingress-Path so routes match whether or
    not requests come through the Supervisor ingress."""

    def test_stripped_path_still_routes(self, client):
        r = client.get(
            "/api/hassio_ingress/token/api/health",
            headers={"X-Ingress-Path": "/api/hassio_ingress/token"},
        )
        assert r.status_code == 200
        assert r.json()["status"] == "ok"


class TestDuplicate:
    def _seed_list_with_content(self, client):
        folder_id = client.post("/api/folders/", json={"name": "F"}).json()["id"]
        list_id = client.post(
            "/api/lists/", json={"name": "L", "folder_id": folder_id}
        ).json()["id"]
        item_id = client.post(
            "/api/items/",
            json={"list_id": list_id, "title": "It", "spiciness": 3, "priority": 2},
        ).json()["id"]
        client.post("/api/subtasks/", json={"item_id": item_id, "title": "s1"})
        client.post("/api/subtasks/", json={"item_id": item_id, "title": "s2"})
        client.post(f"/api/items/{item_id}/tags/urgent")
        return folder_id, list_id, item_id

    def test_duplicate_item_same_list(self, client):
        _, list_id, item_id = self._seed_list_with_content(client)
        r = client.post(f"/api/items/{item_id}/duplicate")
        assert r.status_code == 201
        dup = r.json()
        assert dup["id"] != item_id
        assert dup["list_id"] == list_id
        assert dup["title"].endswith("(copy)")
        assert dup["status"] == "open"
        assert dup["spiciness"] == 3
        assert dup["priority"] == 2
        assert "urgent" in dup["tags"]
        subs = client.get(f"/api/subtasks/?item_id={dup['id']}").json()
        assert [s["title"] for s in subs] == ["s1", "s2"]
        assert all(s["status"] == "open" for s in subs)

    def test_duplicate_item_target_list(self, client):
        _, list_id, item_id = self._seed_list_with_content(client)
        other = client.post("/api/lists/", json={"name": "L2"}).json()["id"]
        r = client.post(
            f"/api/items/{item_id}/duplicate", json={"target_list_id": other}
        )
        assert r.status_code == 201
        assert r.json()["list_id"] == other

    def test_duplicate_item_bad_target_list(self, client):
        _, _, item_id = self._seed_list_with_content(client)
        r = client.post(
            f"/api/items/{item_id}/duplicate", json={"target_list_id": 99999}
        )
        assert r.status_code == 400

    def test_duplicate_list_same_folder(self, client):
        folder_id, list_id, item_id = self._seed_list_with_content(client)
        r = client.post(f"/api/lists/{list_id}/duplicate")
        assert r.status_code == 201
        new_list = r.json()
        assert new_list["id"] != list_id
        assert new_list["folder_id"] == folder_id
        assert new_list["name"].endswith("(copy)")
        items = client.get(f"/api/items/?list_id={new_list['id']}").json()
        assert len(items) == 1
        assert items[0]["id"] != item_id
        assert "urgent" in items[0]["tags"]
        assert len(client.get(f"/api/subtasks/?item_id={items[0]['id']}").json()) == 2

    def test_duplicate_list_to_folder(self, client):
        folder_id, list_id, _ = self._seed_list_with_content(client)
        other = client.post("/api/folders/", json={"name": "F2"}).json()["id"]
        r = client.post(
            f"/api/lists/{list_id}/duplicate",
            json={"keep_folder": False, "target_folder_id": other},
        )
        assert r.status_code == 201
        assert r.json()["folder_id"] == other

    def test_duplicate_list_to_unfiled(self, client):
        _, list_id, _ = self._seed_list_with_content(client)
        r = client.post(
            f"/api/lists/{list_id}/duplicate",
            json={"keep_folder": False, "target_folder_id": None},
        )
        assert r.status_code == 201
        assert r.json()["folder_id"] is None

    def test_duplicate_folder_deep(self, client):
        folder_id, list_id, _ = self._seed_list_with_content(client)
        # Add a second list in the folder.
        client.post("/api/lists/", json={"name": "L2", "folder_id": folder_id})
        r = client.post(f"/api/folders/{folder_id}/duplicate")
        assert r.status_code == 201
        new_folder = r.json()
        assert new_folder["id"] != folder_id
        assert new_folder["name"].endswith("(copy)")
        new_lists = [
            l for l in client.get("/api/lists/").json() if l["folder_id"] == new_folder["id"]
        ]
        assert len(new_lists) == 2


class TestTagRenameCollision:
    def test_rename_to_existing_name_returns_409(self, client):
        a = client.post("/api/tags/", json={"name": "alpha"}).json()["id"]
        client.post("/api/tags/", json={"name": "beta"})
        r = client.patch(f"/api/tags/{a}", json={"name": "beta"})
        assert r.status_code == 409


class TestMoveValidation:
    def test_move_item_to_nonexistent_list(self, client):
        list_id = client.post("/api/lists/", json={"name": "L"}).json()["id"]
        item_id = client.post(
            "/api/items/", json={"list_id": list_id, "title": "X"}
        ).json()["id"]
        r = client.patch(f"/api/items/{item_id}", json={"list_id": 9999})
        assert r.status_code == 400

    def test_move_list_to_nonexistent_folder(self, client):
        list_id = client.post("/api/lists/", json={"name": "L"}).json()["id"]
        r = client.patch(f"/api/lists/{list_id}", json={"folder_id": 9999})
        assert r.status_code == 400

    def test_folder_note_assignment(self, client):
        fid = client.post("/api/folders/", json={"name": "F"}).json()["id"]
        nid = client.post("/api/notes/", json={"title": "Index"}).json()["id"]
        r = client.patch(f"/api/folders/{fid}", json={"folder_note_id": nid})
        assert r.status_code == 200
        assert r.json()["folder_note_id"] == nid
        # clear it
        r2 = client.patch(f"/api/folders/{fid}", json={"folder_note_id": None})
        assert r2.json()["folder_note_id"] is None

    def test_folder_note_rejects_missing_note(self, client):
        fid = client.post("/api/folders/", json={"name": "F"}).json()["id"]
        r = client.patch(f"/api/folders/{fid}", json={"folder_note_id": 99999})
        assert r.status_code == 400

    def test_folder_note_clears_on_note_delete(self, client):
        fid = client.post("/api/folders/", json={"name": "F"}).json()["id"]
        nid = client.post("/api/notes/", json={"title": "Index"}).json()["id"]
        client.patch(f"/api/folders/{fid}", json={"folder_note_id": nid})
        client.delete(f"/api/notes/{nid}")
        r = client.get(f"/api/folders/{fid}")
        assert r.json()["folder_note_id"] is None


class TestNotes:
    def test_create_with_defaults(self, client):
        r = client.post("/api/notes/", json={"title": "Hello"})
        assert r.status_code == 201
        data = r.json()
        assert data["title"] == "Hello"
        assert data["body"] == ""
        assert data["icon"] == "📝"
        assert data["pinned"] is False
        assert data["archived"] is False
        assert data["ai_generated"] is False

    def test_create_in_folder_and_validates(self, client):
        fid = client.post("/api/folders/", json={"name": "F"}).json()["id"]
        r = client.post("/api/notes/", json={"title": "N", "folder_id": fid})
        assert r.status_code == 201
        assert r.json()["folder_id"] == fid
        bad = client.post("/api/notes/", json={"title": "X", "folder_id": 99999})
        assert bad.status_code == 400

    def test_patch_archive_pinned(self, client):
        nid = client.post("/api/notes/", json={"title": "N"}).json()["id"]
        r = client.patch(f"/api/notes/{nid}", json={"pinned": True, "archived": True})
        assert r.status_code == 200
        data = r.json()
        assert data["pinned"] is True
        assert data["archived"] is True
        # Archived hidden by default
        assert len(client.get("/api/notes/").json()) == 0
        assert len(client.get("/api/notes/?archived=true").json()) == 1

    def test_folder_deletion_detaches_notes(self, client):
        fid = client.post("/api/folders/", json={"name": "F"}).json()["id"]
        nid = client.post("/api/notes/", json={"title": "N", "folder_id": fid}).json()["id"]
        client.delete(f"/api/folders/{fid}")
        r = client.get(f"/api/notes/{nid}")
        assert r.status_code == 200
        assert r.json()["folder_id"] is None

    def test_delete_cascades_note_links(self, client, tmp_db):
        nid = client.post(
            "/api/notes/", json={"title": "Src", "body": "See [[Target]] and ![[Other]]"}
        ).json()["id"]
        rows = tmp_db.execute(
            "SELECT COUNT(*) AS c FROM note_links WHERE source_note_id = ?", (nid,)
        ).fetchone()
        assert rows["c"] == 2
        client.delete(f"/api/notes/{nid}")
        rows = tmp_db.execute(
            "SELECT COUNT(*) AS c FROM note_links WHERE source_note_id = ?", (nid,)
        ).fetchone()
        assert rows["c"] == 0

    def test_search_filter(self, client):
        client.post("/api/notes/", json={"title": "Apple pie", "body": "sweet"})
        client.post("/api/notes/", json={"title": "Salad", "body": "with apples"})
        client.post("/api/notes/", json={"title": "Bread", "body": "yeasty"})
        r = client.get("/api/notes/?search=apple").json()
        titles = sorted(n["title"] for n in r)
        assert titles == ["Apple pie", "Salad"]

    def test_duplicate_copies_body_and_links(self, client, tmp_db):
        nid = client.post(
            "/api/notes/", json={"title": "Orig", "body": "has [[Ref]]"}
        ).json()["id"]
        r = client.post(f"/api/notes/{nid}/duplicate")
        assert r.status_code == 201
        new_id = r.json()["id"]
        assert new_id != nid
        assert r.json()["title"].endswith("(copy)")
        assert r.json()["body"] == "has [[Ref]]"
        rows = tmp_db.execute(
            "SELECT target_title FROM note_links WHERE source_note_id = ?", (new_id,)
        ).fetchall()
        assert [r["target_title"] for r in rows] == ["Ref"]

    def test_list_order(self, client):
        a = client.post("/api/notes/", json={"title": "A", "sort_order": 3}).json()["id"]
        b = client.post("/api/notes/", json={"title": "B", "sort_order": 1}).json()["id"]
        c = client.post(
            "/api/notes/", json={"title": "C", "sort_order": 5, "pinned": True}
        ).json()["id"]
        ids = [n["id"] for n in client.get("/api/notes/").json()]
        # Pinned first, then by sort_order ascending
        assert ids[0] == c
        assert ids.index(b) < ids.index(a)

    def test_daily_note_creates_and_reuses(self, client):
        r = client.post("/api/notes/daily", params={"date": "2026-05-15"})
        assert r.status_code == 200
        first = r.json()
        assert first["title"] == "2026-05-15"
        assert first["icon"] == "📅"
        assert first["body"] == ""
        r2 = client.post("/api/notes/daily", params={"date": "2026-05-15"})
        assert r2.status_code == 200
        assert r2.json()["id"] == first["id"]

    def test_daily_note_default_is_today(self, client):
        from datetime import datetime
        r = client.post("/api/notes/daily")
        assert r.status_code == 200
        assert r.json()["title"] == datetime.now().strftime("%Y-%m-%d")

    def test_daily_note_rejects_bad_date(self, client):
        r = client.post("/api/notes/daily", params={"date": "not-a-date"})
        assert r.status_code == 400

    def test_aliases_crud_and_resolve(self, client):
        nid = client.post("/api/notes/", json={"title": "Canonical"}).json()["id"]
        # empty list to start
        assert client.get(f"/api/notes/{nid}/aliases").json() == []
        # add a couple
        client.post(f"/api/notes/{nid}/aliases", json={"alias": "alt name"})
        client.post(f"/api/notes/{nid}/aliases", json={"alias": "Canon"})
        assert sorted(client.get(f"/api/notes/{nid}/aliases").json()) == ["Canon", "alt name"]
        # resolve hits aliases (case-insensitive)
        r = client.get("/api/notes/resolve", params={"title": "ALT NAME"})
        assert r.status_code == 200
        assert r.json()["note_id"] == nid
        # title still wins over alias
        r2 = client.get("/api/notes/resolve", params={"title": "canonical"})
        assert r2.json()["note_id"] == nid
        # delete an alias
        client.delete(f"/api/notes/{nid}/aliases/alt%20name")
        assert client.get(f"/api/notes/{nid}/aliases").json() == ["Canon"]

    def test_alias_rejects_collision_with_existing_title(self, client):
        a = client.post("/api/notes/", json={"title": "Apple"}).json()["id"]
        client.post("/api/notes/", json={"title": "Banana"})
        r = client.post(f"/api/notes/{a}/aliases", json={"alias": "Banana"})
        assert r.status_code == 409

    def test_alias_empty_rejected(self, client):
        nid = client.post("/api/notes/", json={"title": "X"}).json()["id"]
        r = client.post(f"/api/notes/{nid}/aliases", json={"alias": "  "})
        assert r.status_code == 400

    def test_alias_cascade_on_note_delete(self, client, tmp_db):
        nid = client.post("/api/notes/", json={"title": "Doomed"}).json()["id"]
        client.post(f"/api/notes/{nid}/aliases", json={"alias": "Goner"})
        assert tmp_db.execute("SELECT COUNT(*) AS c FROM note_aliases").fetchone()["c"] == 1
        client.delete(f"/api/notes/{nid}")
        assert tmp_db.execute("SELECT COUNT(*) AS c FROM note_aliases").fetchone()["c"] == 0

    def test_graph_returns_resolved_edges(self, client):
        a = client.post("/api/notes/", json={"title": "A", "body": "see [[B]] and [[Ghost]]"}).json()["id"]
        b = client.post("/api/notes/", json={"title": "B", "body": "embeds ![[C]]"}).json()["id"]
        c = client.post("/api/notes/", json={"title": "C", "body": "plain"}).json()["id"]
        r = client.get("/api/notes/graph")
        assert r.status_code == 200
        data = r.json()
        node_ids = {n["id"] for n in data["nodes"]}
        assert node_ids == {a, b, c}
        # Edges only for resolvable targets, no self-loops, dedup'd
        edges = sorted((e["source"], e["target"]) for e in data["edges"])
        assert edges == sorted([(a, b), (b, c)])

    def test_graph_resolves_alias_edges(self, client):
        a = client.post("/api/notes/", json={"title": "A", "body": "see [[Beeline]]"}).json()["id"]
        b = client.post("/api/notes/", json={"title": "Bee"}).json()["id"]
        client.post(f"/api/notes/{b}/aliases", json={"alias": "Beeline"})
        edges = client.get("/api/notes/graph").json()["edges"]
        assert any(e["source"] == a and e["target"] == b for e in edges)

    def test_rename_rewrites_wikilinks_in_other_notes(self, client):
        a = client.post("/api/notes/", json={"title": "Origin"}).json()["id"]
        client.post("/api/notes/", json={"title": "X", "body": "See [[Origin]] and [[Origin|alt]] and ![[Origin]] and [[Origin#Sec]]"})
        client.post("/api/notes/", json={"title": "Y", "body": "plain text"})
        client.patch(f"/api/notes/{a}", json={"title": "Renamed"})
        notes = client.get("/api/notes/").json()
        x = next(n for n in notes if n["title"] == "X")
        assert "[[Renamed]]" in x["body"]
        assert "[[Renamed|alt]]" in x["body"]
        assert "![[Renamed]]" in x["body"]
        assert "[[Renamed#Sec]]" in x["body"]
        # The renamed note's own body must be untouched
        a_after = client.get(f"/api/notes/{a}").json()
        assert a_after["title"] == "Renamed"

    def test_rename_is_case_insensitive_on_lookup(self, client):
        a = client.post("/api/notes/", json={"title": "Origin"}).json()["id"]
        client.post("/api/notes/", json={"title": "X", "body": "see [[ORIGIN]] and [[origin|x]]"})
        client.patch(f"/api/notes/{a}", json={"title": "NewName"})
        x = next(n for n in client.get("/api/notes/").json() if n["title"] == "X")
        assert "[[NewName]]" in x["body"]
        assert "[[NewName|x]]" in x["body"]

    def test_query_by_tag_and_folder(self, client):
        fid = client.post("/api/folders/", json={"name": "F"}).json()["id"]
        a = client.post("/api/notes/", json={"title": "A", "body": "has #foo", "folder_id": fid}).json()["id"]
        b = client.post("/api/notes/", json={"title": "B", "body": "has #foo"}).json()["id"]
        client.post("/api/notes/", json={"title": "C", "body": "has #bar", "folder_id": fid})
        # Tag filter
        r = client.post("/api/notes/query", json={"tag": "foo"}).json()
        ids = sorted(x["id"] for x in r)
        assert ids == sorted([a, b])
        # Tag + folder filter
        r2 = client.post("/api/notes/query", json={"tag": "foo", "folder_id": fid}).json()
        assert [x["id"] for x in r2] == [a]
        # Unfiled
        r3 = client.post("/api/notes/query", json={"tag": "foo", "folder_id": None}).json()
        assert [x["id"] for x in r3] == [b]

    def test_query_limit_and_sort(self, client):
        for i in range(5):
            client.post("/api/notes/", json={"title": f"N{i}", "body": "#tag"})
        r = client.post("/api/notes/query", json={"tag": "tag", "limit": 3}).json()
        assert len(r) == 3
        # Default sort is title ascending
        titles = [x["title"] for x in r]
        assert titles == sorted(titles)

    def test_vault_stats(self, client):
        client.post("/api/notes/", json={"title": "A", "body": "Hello world #tag1 [[B]]"})
        b = client.post("/api/notes/", json={"title": "B", "body": "B content #tag2"}).json()["id"]
        client.post(f"/api/notes/{b}/aliases", json={"alias": "Beta"})
        archived = client.post("/api/notes/", json={"title": "Old"}).json()["id"]
        client.patch(f"/api/notes/{archived}", json={"archived": True})
        client.post("/api/folders/", json={"name": "F"})
        client.post("/api/lists/", json={"name": "L"})

        r = client.get("/api/notes/vault_stats")
        assert r.status_code == 200
        data = r.json()
        assert data["notes_total"] == 3
        assert data["notes_archived"] == 1
        assert data["notes_active"] == 2
        assert data["folders"] >= 1
        assert data["lists"] >= 1
        assert data["tags"] >= 2
        assert data["aliases"] == 1
        assert data["wikilinks"] == 1
        assert data["words"] > 0
        assert data["characters"] > 0

    def test_outgoing_links_resolve_and_unresolved(self, client):
        a = client.post("/api/notes/", json={"title": "A", "body": "[[B]] then ![[Ghost]]"}).json()["id"]
        b = client.post("/api/notes/", json={"title": "B"}).json()["id"]
        c = client.post("/api/notes/", json={"title": "Bee"}).json()["id"]
        client.post(f"/api/notes/{c}/aliases", json={"alias": "Bumble"})
        # Add an alias-resolving link too
        client.patch(f"/api/notes/{a}", json={"body": "[[B]] then ![[Ghost]] and ![[Bumble]]"})

        r = client.get(f"/api/notes/{a}/outgoing")
        assert r.status_code == 200
        by_target = {row["target_title"]: row for row in r.json()}
        assert by_target["B"]["note_id"] == b
        assert by_target["B"]["link_type"] == "wikilink"
        assert by_target["Ghost"]["note_id"] is None
        assert by_target["Ghost"]["link_type"] == "embed"
        assert by_target["Bumble"]["note_id"] == c

    def test_unlinked_mentions(self, client):
        target = client.post("/api/notes/", json={"title": "Project Atlas"}).json()["id"]
        # Linked: mentions and wikilinks → should NOT appear in unlinked
        client.post("/api/notes/", json={
            "title": "Notes A",
            "body": "Working on [[Project Atlas]] this week",
        })
        # Unlinked: mentions literally but no wikilink
        b = client.post("/api/notes/", json={
            "title": "Notes B",
            "body": "We talked about Project Atlas at standup",
        }).json()["id"]
        # Substring-only: should not match (word boundary)
        client.post("/api/notes/", json={
            "title": "Notes C",
            "body": "The XProject Atlas2 was different",
        })
        # Case insensitive
        d = client.post("/api/notes/", json={
            "title": "Notes D",
            "body": "Long history of project atlas across teams.",
        }).json()["id"]
        # Alias resolution
        client.post(f"/api/notes/{target}/aliases", json={"alias": "PA-2026"})
        e = client.post("/api/notes/", json={
            "title": "Notes E",
            "body": "Ref PA-2026 here",
        }).json()["id"]

        r = client.get(f"/api/notes/{target}/unlinked_mentions")
        assert r.status_code == 200
        ids = {entry["note_id"] for entry in r.json()}
        assert b in ids and d in ids and e in ids
        # Linked note must not appear
        link_ids = {entry["note_id"] for entry in r.json()}
        linked_titles = [entry["title"] for entry in r.json()]
        assert "Notes A" not in linked_titles
        assert "Notes C" not in linked_titles  # word-boundary excluded

    def test_tag_rename(self, client):
        client.post("/api/notes/", json={
            "title": "A",
            "body": "Has #old and #other tags",
        })
        client.post("/api/notes/", json={
            "title": "B",
            "body": "---\ntags: [old, foo]\n---\n#old #unrelated",
        })
        client.post("/api/notes/", json={
            "title": "C",
            "body": "Inside `#old` should still get hit since it's inline-code, but a fence:\n```\n#old in code stays\n```\nand plain #old in prose",
        })
        r = client.post("/api/notes/tags/rename", json={"old": "old", "new": "new-name"})
        assert r.status_code == 200
        assert r.json()["updated"] == 3
        # Verify changes
        notes = {n["title"]: n["body"] for n in client.get("/api/notes/").json()}
        assert "#new-name" in notes["A"] and "#old" not in notes["A"]
        assert "[new-name, foo]" in notes["B"] or "new-name" in notes["B"]
        # Fenced code block leaves the literal "#old in code stays" intact
        assert "#old in code stays" in notes["C"]
        # Out-of-fence prose got rewritten
        assert "#new-name in prose" in notes["C"]

    def test_tag_rename_validates_new(self, client):
        r = client.post("/api/notes/tags/rename", json={"old": "a", "new": "bad tag!"})
        assert r.status_code == 400

    def test_tag_aggregation_inline_and_frontmatter(self, client):
        client.post("/api/notes/", json={
            "title": "T1",
            "body": "Use #python and #data-science here",
        })
        client.post("/api/notes/", json={
            "title": "T2",
            "body": "---\ntags: [python, art]\n---\nbody",
        })
        client.post("/api/notes/", json={
            "title": "T3",
            "body": "---\ntags:\n  - python\n  - cooking\n---\nbody",
        })
        # Inline hashtags inside fenced code should NOT count
        client.post("/api/notes/", json={
            "title": "T4",
            "body": "```\n# not a tag\n```\nbut #real is",
        })
        data = client.get("/api/notes/tags").json()
        tags = {entry["tag"]: entry["count"] for entry in data}
        assert tags.get("python") == 3
        assert tags.get("data-science") == 1
        assert tags.get("art") == 1
        assert tags.get("cooking") == 1
        assert tags.get("real") == 1
        assert "not" not in tags  # fenced code stripped
        # Sort: count desc, then tag asc
        counts = [entry["count"] for entry in data]
        assert counts == sorted(counts, reverse=True)


class TestWikilinkParser:
    def test_plain(self):
        from routers._wikilinks import extract_wikilinks
        assert extract_wikilinks("see [[Foo]] here") == [("Foo", "wikilink")]

    def test_heading_anchor_stripped(self):
        from routers._wikilinks import extract_wikilinks
        assert extract_wikilinks("see [[Foo#Section]] here") == [("Foo", "wikilink")]
        assert extract_wikilinks("![[Foo#Bar]]") == [("Foo", "embed")]

    def test_embed(self):
        from routers._wikilinks import extract_wikilinks
        assert extract_wikilinks("![[Bar]]") == [("Bar", "embed")]

    def test_alias_keeps_title(self):
        from routers._wikilinks import extract_wikilinks
        assert extract_wikilinks("[[Foo|alias text]]") == [("Foo", "wikilink")]

    def test_both_kinds_preserve_order_and_dedup(self):
        from routers._wikilinks import extract_wikilinks
        body = "![[Bar]] and [[Foo]] then [[Foo]] again and ![[Bar]] too"
        assert extract_wikilinks(body) == [("Bar", "embed"), ("Foo", "wikilink")]

    def test_ignores_fenced_code(self):
        from routers._wikilinks import extract_wikilinks
        body = "```\n[[Fenced]]\n```\n[[Outside]]"
        assert extract_wikilinks(body) == [("Outside", "wikilink")]

    def test_ignores_inline_backticks(self):
        from routers._wikilinks import extract_wikilinks
        assert extract_wikilinks("prose `[[Ignored]]` text [[Real]]") == [
            ("Real", "wikilink")
        ]

    def test_empty(self):
        from routers._wikilinks import extract_wikilinks
        assert extract_wikilinks("") == []
        assert extract_wikilinks(None or "") == []

    def test_unmatched_no_crash(self):
        from routers._wikilinks import extract_wikilinks
        # Unmatched brackets / nested should not raise
        out = extract_wikilinks("[[broken and [[nested]] oops")
        assert ("nested", "wikilink") in out


class TestBacklinks:
    def test_source_rename_preserves_link(self, client):
        a = client.post("/api/notes/", json={"title": "A", "body": "ref [[B]]"}).json()["id"]
        b = client.post("/api/notes/", json={"title": "B"}).json()["id"]
        # rename source
        client.patch(f"/api/notes/{a}", json={"title": "A-renamed"})
        bls = client.get(f"/api/notes/{b}/backlinks").json()
        assert len(bls) == 1
        assert bls[0]["note_id"] == a
        assert bls[0]["title"] == "A-renamed"

    def test_target_rename_follows_links(self, client):
        """As of v1.3.4: renaming a note rewrites wikilinks in other notes,
        so the backlink follows the new title instead of breaking."""
        a = client.post("/api/notes/", json={"title": "A", "body": "ref [[B]]"}).json()["id"]
        b = client.post("/api/notes/", json={"title": "B"}).json()["id"]
        client.patch(f"/api/notes/{b}", json={"title": "B2"})
        backlinks = client.get(f"/api/notes/{b}/backlinks").json()
        assert len(backlinks) == 1
        assert backlinks[0]["note_id"] == a
        # Source body got rewritten too
        a_body = client.get(f"/api/notes/{a}").json()["body"]
        assert "[[B2]]" in a_body
        assert "[[B]]" not in a_body

    def test_resolve_case_insensitive(self, client):
        nid = client.post("/api/notes/", json={"title": "Hello World"}).json()["id"]
        r = client.get("/api/notes/resolve", params={"title": "HELLO WORLD"})
        assert r.status_code == 200
        assert r.json()["note_id"] == nid

    def test_embed_vs_wikilink(self, client):
        a = client.post(
            "/api/notes/", json={"title": "A", "body": "![[B]] and [[B]]"}
        ).json()["id"]
        b = client.post("/api/notes/", json={"title": "B"}).json()["id"]
        bls = client.get(f"/api/notes/{b}/backlinks").json()
        kinds = sorted(bl["link_type"] for bl in bls)
        assert kinds == ["embed", "wikilink"]

    def test_resolve_ambiguity_lowest_id(self, client):
        first = client.post("/api/notes/", json={"title": "Dup"}).json()["id"]
        second = client.post("/api/notes/", json={"title": "Dup"}).json()["id"]
        assert second > first
        r = client.get("/api/notes/resolve", params={"title": "Dup"})
        assert r.json()["note_id"] == first

    def test_resolve_unknown(self, client):
        r = client.get("/api/notes/resolve", params={"title": "Nope"})
        assert r.status_code == 404

    def test_snippet_length_and_position(self, client):
        prefix = "x" * 200
        body = f"{prefix} see [[B]] here {prefix}"
        a = client.post("/api/notes/", json={"title": "A", "body": body}).json()["id"]
        b = client.post("/api/notes/", json={"title": "B"}).json()["id"]
        bls = client.get(f"/api/notes/{b}/backlinks").json()
        assert len(bls) == 1
        snip = bls[0]["snippet"]
        assert len(snip) <= 120
        assert "[[B]]" in snip or "B" in snip


class TestBoards:
    def test_create_with_defaults(self, client):
        r = client.post("/api/boards/", json={"name": "Plan"})
        assert r.status_code == 201
        data = r.json()
        assert data["name"] == "Plan"
        assert data["icon"] == "🧩"
        assert data["pinned"] is False
        assert data["archived"] is False
        assert data["viewport"] == {"x": 0, "y": 0, "zoom": 1}

    def test_create_rejects_bad_folder(self, client):
        r = client.post("/api/boards/", json={"name": "X", "folder_id": 9999})
        assert r.status_code == 400

    def test_filter_by_folder_and_search(self, client):
        f1 = client.post("/api/folders/", json={"name": "F1"}).json()["id"]
        f2 = client.post("/api/folders/", json={"name": "F2"}).json()["id"]
        client.post("/api/boards/", json={"folder_id": f1, "name": "Alpha"})
        client.post("/api/boards/", json={"folder_id": f1, "name": "Beta"})
        client.post("/api/boards/", json={"folder_id": f2, "name": "Gamma"})
        assert len(client.get(f"/api/boards/?folder_id={f1}").json()) == 2
        assert len(client.get(f"/api/boards/?folder_id={f2}").json()) == 1
        hits = client.get("/api/boards/?search=alp").json()
        assert [b["name"] for b in hits] == ["Alpha"]

    def test_patch_archive_pinned(self, client):
        bid = client.post("/api/boards/", json={"name": "B"}).json()["id"]
        r = client.patch(f"/api/boards/{bid}", json={"pinned": True, "archived": True})
        assert r.status_code == 200
        data = r.json()
        assert data["pinned"] is True
        assert data["archived"] is True
        # Archived hidden by default
        assert len(client.get("/api/boards/").json()) == 0
        assert len(client.get("/api/boards/?archived=true").json()) == 1

    def test_patch_rejects_bad_folder(self, client):
        bid = client.post("/api/boards/", json={"name": "B"}).json()["id"]
        r = client.patch(f"/api/boards/{bid}", json={"folder_id": 9999})
        assert r.status_code == 400

    def test_list_order_pinned_first(self, client):
        a = client.post("/api/boards/", json={"name": "A", "sort_order": 3}).json()["id"]
        b = client.post("/api/boards/", json={"name": "B", "sort_order": 1}).json()["id"]
        c = client.post(
            "/api/boards/", json={"name": "C", "sort_order": 5, "pinned": True}
        ).json()["id"]
        ids = [x["id"] for x in client.get("/api/boards/").json()]
        assert ids[0] == c
        assert ids.index(b) < ids.index(a)

    def test_delete_cascades_nodes_and_edges(self, client, tmp_db):
        bid = client.post("/api/boards/", json={"name": "B"}).json()["id"]
        n1 = client.post(
            f"/api/boards/{bid}/nodes", json={"kind": "card", "title": "A"}
        ).json()["id"]
        n2 = client.post(
            f"/api/boards/{bid}/nodes", json={"kind": "card", "title": "B"}
        ).json()["id"]
        client.post(
            f"/api/boards/{bid}/edges",
            json={"source_node_id": n1, "target_node_id": n2},
        )
        assert client.delete(f"/api/boards/{bid}").status_code == 204
        nc = tmp_db.execute(
            "SELECT COUNT(*) AS c FROM board_nodes WHERE board_id = ?", (bid,)
        ).fetchone()["c"]
        ec = tmp_db.execute(
            "SELECT COUNT(*) AS c FROM board_edges WHERE board_id = ?", (bid,)
        ).fetchone()["c"]
        assert nc == 0 and ec == 0

    def test_folder_delete_detaches_boards(self, client):
        fid = client.post("/api/folders/", json={"name": "F"}).json()["id"]
        bid = client.post(
            "/api/boards/", json={"name": "B", "folder_id": fid}
        ).json()["id"]
        client.delete(f"/api/folders/{fid}")
        r = client.get(f"/api/boards/{bid}")
        assert r.status_code == 200
        assert r.json()["board"]["folder_id"] is None

    def test_duplicate_copies_nodes_and_edges(self, client):
        bid = client.post("/api/boards/", json={"name": "Orig"}).json()["id"]
        n_ids = [
            client.post(
                f"/api/boards/{bid}/nodes",
                json={"kind": "card", "title": f"N{i}", "x": float(i), "y": 0.0},
            ).json()["id"]
            for i in range(3)
        ]
        client.post(
            f"/api/boards/{bid}/edges",
            json={"source_node_id": n_ids[0], "target_node_id": n_ids[1]},
        )
        client.post(
            f"/api/boards/{bid}/edges",
            json={"source_node_id": n_ids[1], "target_node_id": n_ids[2]},
        )
        r = client.post(f"/api/boards/{bid}/duplicate")
        assert r.status_code == 201
        new = r.json()
        assert new["name"].endswith("(copy)")
        new_id = new["id"]
        detail = client.get(f"/api/boards/{new_id}").json()
        assert len(detail["nodes"]) == 3
        assert len(detail["edges"]) == 2
        new_node_ids = {n["id"] for n in detail["nodes"]}
        # Edges reference the NEW ids, not the old ones.
        for e in detail["edges"]:
            assert e["source_node_id"] in new_node_ids
            assert e["target_node_id"] in new_node_ids
            assert e["source_node_id"] not in n_ids
            assert e["target_node_id"] not in n_ids

    def test_viewport_roundtrip(self, client):
        bid = client.post("/api/boards/", json={"name": "B"}).json()["id"]
        r = client.patch(
            f"/api/boards/{bid}/viewport", json={"x": 42.5, "y": -10.0, "zoom": 1.5}
        )
        assert r.status_code == 200
        assert r.json()["viewport"] == {"x": 42.5, "y": -10.0, "zoom": 1.5}
        detail = client.get(f"/api/boards/{bid}").json()
        assert detail["board"]["viewport"] == {"x": 42.5, "y": -10.0, "zoom": 1.5}

    def test_get_unknown_board_404(self, client):
        assert client.get("/api/boards/9999").status_code == 404


class TestBoardNodes:
    def _board(self, client) -> int:
        return client.post("/api/boards/", json={"name": "B"}).json()["id"]

    def test_create_card(self, client):
        bid = self._board(client)
        r = client.post(
            f"/api/boards/{bid}/nodes",
            json={"kind": "card", "title": "hi", "body": "world"},
        )
        assert r.status_code == 201
        data = r.json()
        assert data["kind"] == "card"
        assert data["ref_id"] is None
        assert data["title"] == "hi"
        assert data["width"] == 240
        assert data["height"] == 160

    def test_create_list_node(self, client):
        bid = self._board(client)
        lid = client.post("/api/lists/", json={"name": "My List"}).json()["id"]
        r = client.post(
            f"/api/boards/{bid}/nodes", json={"kind": "list", "ref_id": lid}
        )
        assert r.status_code == 201
        assert r.json()["ref_id"] == lid

    def test_create_note_node(self, client):
        bid = self._board(client)
        nid = client.post("/api/notes/", json={"title": "N"}).json()["id"]
        r = client.post(
            f"/api/boards/{bid}/nodes", json={"kind": "note", "ref_id": nid}
        )
        assert r.status_code == 201
        assert r.json()["ref_id"] == nid

    def test_reject_missing_ref_id_for_list(self, client):
        bid = self._board(client)
        r = client.post(f"/api/boards/{bid}/nodes", json={"kind": "list"})
        assert r.status_code == 400

    def test_reject_missing_ref_id_for_note(self, client):
        bid = self._board(client)
        r = client.post(f"/api/boards/{bid}/nodes", json={"kind": "note"})
        assert r.status_code == 400

    def test_reject_unknown_ref_id_for_list(self, client):
        bid = self._board(client)
        r = client.post(
            f"/api/boards/{bid}/nodes", json={"kind": "list", "ref_id": 9999}
        )
        assert r.status_code == 400

    def test_reject_unknown_ref_id_for_note(self, client):
        bid = self._board(client)
        r = client.post(
            f"/api/boards/{bid}/nodes", json={"kind": "note", "ref_id": 9999}
        )
        assert r.status_code == 400

    def test_patch_partial(self, client):
        bid = self._board(client)
        nid = client.post(
            f"/api/boards/{bid}/nodes", json={"kind": "card", "title": "t"}
        ).json()["id"]
        r = client.patch(
            f"/api/boards/{bid}/nodes/{nid}", json={"title": "t2", "x": 99.0}
        )
        assert r.status_code == 200
        data = r.json()
        assert data["title"] == "t2"
        assert data["x"] == 99.0

    def test_bulk_positions(self, client):
        bid = self._board(client)
        ids = [
            client.post(
                f"/api/boards/{bid}/nodes", json={"kind": "card", "title": str(i)}
            ).json()["id"]
            for i in range(3)
        ]
        payload = {
            "positions": [
                {"id": ids[0], "x": 10.0, "y": 20.0},
                {"id": ids[1], "x": 30.0, "y": 40.0},
                {"id": ids[2], "x": 50.0, "y": 60.0},
            ]
        }
        r = client.post(f"/api/boards/{bid}/nodes/bulk-positions", json=payload)
        assert r.status_code == 204
        detail = client.get(f"/api/boards/{bid}").json()
        coords = {n["id"]: (n["x"], n["y"]) for n in detail["nodes"]}
        assert coords[ids[0]] == (10.0, 20.0)
        assert coords[ids[1]] == (30.0, 40.0)
        assert coords[ids[2]] == (50.0, 60.0)

    def test_bulk_positions_skips_foreign_ids(self, client):
        b1 = self._board(client)
        b2 = self._board(client)
        n1 = client.post(
            f"/api/boards/{b1}/nodes", json={"kind": "card", "title": "a"}
        ).json()["id"]
        n2 = client.post(
            f"/api/boards/{b2}/nodes", json={"kind": "card", "title": "b"}
        ).json()["id"]
        r = client.post(
            f"/api/boards/{b1}/nodes/bulk-positions",
            json={
                "positions": [
                    {"id": n1, "x": 5.0, "y": 5.0},
                    {"id": n2, "x": 999.0, "y": 999.0},  # belongs to b2, skipped
                ]
            },
        )
        assert r.status_code == 204
        d2 = client.get(f"/api/boards/{b2}").json()
        assert d2["nodes"][0]["x"] != 999.0

    def test_delete_single_node(self, client):
        bid = self._board(client)
        nid = client.post(
            f"/api/boards/{bid}/nodes", json={"kind": "card", "title": "x"}
        ).json()["id"]
        assert client.delete(f"/api/boards/{bid}/nodes/{nid}").status_code == 204
        assert len(client.get(f"/api/boards/{bid}").json()["nodes"]) == 0

    def test_tombstone_when_ref_deleted(self, client):
        bid = self._board(client)
        lid = client.post("/api/lists/", json={"name": "Doomed"}).json()["id"]
        nid = client.post(
            f"/api/boards/{bid}/nodes", json={"kind": "list", "ref_id": lid}
        ).json()["id"]
        client.delete(f"/api/lists/{lid}")
        detail = client.get(f"/api/boards/{bid}").json()
        node = next(n for n in detail["nodes"] if n["id"] == nid)
        assert node["ref_summary"] is None
        assert node["ref_id"] == lid  # tombstoned ref kept

    def test_ref_summary_for_list(self, client):
        bid = self._board(client)
        lid = client.post("/api/lists/", json={"name": "Groceries"}).json()["id"]
        client.post("/api/items/", json={"list_id": lid, "title": "a"})
        iid = client.post(
            "/api/items/", json={"list_id": lid, "title": "b"}
        ).json()["id"]
        client.patch(f"/api/items/{iid}", json={"status": "completed"})
        client.post(
            f"/api/boards/{bid}/nodes", json={"kind": "list", "ref_id": lid}
        )
        detail = client.get(f"/api/boards/{bid}").json()
        s = detail["nodes"][0]["ref_summary"]
        assert s["id"] == lid
        assert s["name"] == "Groceries"
        assert s["item_count"] == 2
        assert s["completed_count"] == 1

    def test_ref_summary_for_note(self, client):
        bid = self._board(client)
        body = "x" * 1000
        nid = client.post(
            "/api/notes/", json={"title": "Big", "body": body}
        ).json()["id"]
        client.post(
            f"/api/boards/{bid}/nodes", json={"kind": "note", "ref_id": nid}
        )
        detail = client.get(f"/api/boards/{bid}").json()
        s = detail["nodes"][0]["ref_summary"]
        assert s["id"] == nid
        assert s["title"] == "Big"
        assert "body_preview" in s
        assert len(s["body_preview"]) == 400

    def test_card_has_null_ref_summary(self, client):
        bid = self._board(client)
        client.post(
            f"/api/boards/{bid}/nodes", json={"kind": "card", "title": "c"}
        )
        detail = client.get(f"/api/boards/{bid}").json()
        assert detail["nodes"][0]["ref_summary"] is None


class TestBoardEdges:
    def _board_with_two_nodes(self, client) -> tuple[int, int, int]:
        bid = client.post("/api/boards/", json={"name": "B"}).json()["id"]
        n1 = client.post(
            f"/api/boards/{bid}/nodes", json={"kind": "card", "title": "a"}
        ).json()["id"]
        n2 = client.post(
            f"/api/boards/{bid}/nodes", json={"kind": "card", "title": "b"}
        ).json()["id"]
        return bid, n1, n2

    def test_create_edge(self, client):
        bid, n1, n2 = self._board_with_two_nodes(client)
        r = client.post(
            f"/api/boards/{bid}/edges",
            json={"source_node_id": n1, "target_node_id": n2, "label": "hi"},
        )
        assert r.status_code == 201
        data = r.json()
        assert data["source_node_id"] == n1
        assert data["target_node_id"] == n2
        assert data["label"] == "hi"
        assert data["style"] == "default"

    def test_reject_self_loop(self, client):
        bid, n1, _ = self._board_with_two_nodes(client)
        r = client.post(
            f"/api/boards/{bid}/edges",
            json={"source_node_id": n1, "target_node_id": n1},
        )
        assert r.status_code == 400

    def test_reject_cross_board_edge(self, client):
        b1, n1, _ = self._board_with_two_nodes(client)
        _, other, _ = self._board_with_two_nodes(client)
        r = client.post(
            f"/api/boards/{b1}/edges",
            json={"source_node_id": n1, "target_node_id": other},
        )
        assert r.status_code == 400

    def test_patch_edge(self, client):
        bid, n1, n2 = self._board_with_two_nodes(client)
        eid = client.post(
            f"/api/boards/{bid}/edges",
            json={"source_node_id": n1, "target_node_id": n2},
        ).json()["id"]
        r = client.patch(
            f"/api/boards/{bid}/edges/{eid}", json={"label": "LBL", "style": "bold"}
        )
        assert r.status_code == 200
        assert r.json()["label"] == "LBL"
        assert r.json()["style"] == "bold"

    def test_delete_edge(self, client):
        bid, n1, n2 = self._board_with_two_nodes(client)
        eid = client.post(
            f"/api/boards/{bid}/edges",
            json={"source_node_id": n1, "target_node_id": n2},
        ).json()["id"]
        assert client.delete(f"/api/boards/{bid}/edges/{eid}").status_code == 204
        assert len(client.get(f"/api/boards/{bid}").json()["edges"]) == 0

    def test_delete_source_node_cascades_edge(self, client):
        bid, n1, n2 = self._board_with_two_nodes(client)
        client.post(
            f"/api/boards/{bid}/edges",
            json={"source_node_id": n1, "target_node_id": n2},
        )
        client.delete(f"/api/boards/{bid}/nodes/{n1}")
        assert len(client.get(f"/api/boards/{bid}").json()["edges"]) == 0


class TestBoardAttachments:
    def _board(self, client) -> int:
        return client.post("/api/boards/", json={"name": "B"}).json()["id"]

    def _upload(self, client, bid: int, content: bytes = b"hello",
                name: str = "pic.png", mime: str = "image/png") -> dict:
        r = client.post(
            f"/api/boards/{bid}/attachments",
            files={"file": (name, content, mime)},
        )
        assert r.status_code == 201, r.text
        return r.json()

    def test_upload_returns_metadata(self, client):
        bid = self._board(client)
        meta = self._upload(client, bid)
        assert meta["filename"]
        assert meta["filename"].endswith(".png")
        assert meta["original_name"] == "pic.png"
        assert meta["mime"] == "image/png"
        assert meta["size"] == len(b"hello")

    def test_create_image_node_from_upload(self, client):
        bid = self._board(client)
        meta = self._upload(client, bid)
        r = client.post(
            f"/api/boards/{bid}/nodes",
            json={
                "kind": "image",
                "media_filename": meta["filename"],
                "media_mime": meta["mime"],
                "media_size": meta["size"],
                "media_alt": "cat photo",
                "x": 10,
                "y": 20,
            },
        )
        assert r.status_code == 201, r.text
        node = r.json()
        assert node["kind"] == "image"
        assert node["media_filename"] == meta["filename"]
        assert node["media_alt"] == "cat photo"

    def test_serve_attachment_requires_referencing_node(self, client):
        bid = self._board(client)
        meta = self._upload(client, bid)
        # No node references the file yet → 404.
        r = client.get(f"/api/boards/{bid}/attachments/{meta['filename']}")
        assert r.status_code == 404

        client.post(
            f"/api/boards/{bid}/nodes",
            json={"kind": "image", "media_filename": meta["filename"]},
        )
        r = client.get(f"/api/boards/{bid}/attachments/{meta['filename']}")
        assert r.status_code == 200
        assert r.content == b"hello"

    def test_delete_node_purges_orphan_media(self, client, tmp_path):
        bid = self._board(client)
        meta = self._upload(client, bid)
        nid = client.post(
            f"/api/boards/{bid}/nodes",
            json={"kind": "image", "media_filename": meta["filename"]},
        ).json()["id"]
        # File exists on disk.
        path = tmp_path / "board_media" / str(bid) / meta["filename"]
        assert path.exists()

        assert client.delete(f"/api/boards/{bid}/nodes/{nid}").status_code == 204
        assert not path.exists()

    def test_shared_media_survives_single_node_delete(self, client, tmp_path):
        bid = self._board(client)
        meta = self._upload(client, bid)
        n1 = client.post(
            f"/api/boards/{bid}/nodes",
            json={"kind": "image", "media_filename": meta["filename"]},
        ).json()["id"]
        client.post(
            f"/api/boards/{bid}/nodes",
            json={"kind": "image", "media_filename": meta["filename"]},
        )
        path = tmp_path / "board_media" / str(bid) / meta["filename"]
        assert path.exists()

        client.delete(f"/api/boards/{bid}/nodes/{n1}")
        # Second node still references it; file must survive.
        assert path.exists()

    def test_create_rejects_missing_media_filename(self, client):
        bid = self._board(client)
        r = client.post(
            f"/api/boards/{bid}/nodes", json={"kind": "image"}
        )
        assert r.status_code == 400

    def test_create_rejects_unknown_media_filename(self, client):
        bid = self._board(client)
        r = client.post(
            f"/api/boards/{bid}/nodes",
            json={"kind": "file", "media_filename": "nope.bin"},
        )
        assert r.status_code == 400

    def test_serve_rejects_path_traversal(self, client):
        bid = self._board(client)
        r = client.get(f"/api/boards/{bid}/attachments/..%2Fetc%2Fpasswd")
        # Either 400 (invalid) or 404 — never a file outside the media dir.
        assert r.status_code in (400, 404)

    def test_board_detail_includes_media_fields(self, client):
        bid = self._board(client)
        meta = self._upload(client, bid, name="doc.pdf", mime="application/pdf")
        client.post(
            f"/api/boards/{bid}/nodes",
            json={
                "kind": "file",
                "media_filename": meta["filename"],
                "media_mime": meta["mime"],
                "media_size": meta["size"],
            },
        )
        detail = client.get(f"/api/boards/{bid}").json()
        node = detail["nodes"][0]
        assert node["kind"] == "file"
        assert node["media_filename"] == meta["filename"]
        assert node["media_mime"] == "application/pdf"


class TestBoardGroups:
    def _board(self, client) -> int:
        return client.post("/api/boards/", json={"name": "B"}).json()["id"]

    def _card(self, client, bid, **kw) -> int:
        payload = {"kind": "card", "title": "c", "x": 0, "y": 0, **kw}
        return client.post(f"/api/boards/{bid}/nodes", json=payload).json()["id"]

    def _group(self, client, bid, **kw) -> int:
        payload = {
            "kind": "group",
            "title": "G",
            "x": 0,
            "y": 0,
            "width": 400,
            "height": 260,
            **kw,
        }
        return client.post(f"/api/boards/{bid}/nodes", json=payload).json()["id"]

    def test_create_group(self, client):
        bid = self._board(client)
        r = client.post(
            f"/api/boards/{bid}/nodes",
            json={"kind": "group", "title": "G1", "width": 320, "height": 200},
        )
        assert r.status_code == 201, r.text
        data = r.json()
        assert data["kind"] == "group"
        assert data["title"] == "G1"
        assert data["parent_group_id"] is None

    def test_set_parent_on_create(self, client):
        bid = self._board(client)
        gid = self._group(client, bid)
        r = client.post(
            f"/api/boards/{bid}/nodes",
            json={"kind": "card", "title": "child", "parent_group_id": gid},
        )
        assert r.status_code == 201, r.text
        assert r.json()["parent_group_id"] == gid

    def test_set_parent_via_patch(self, client):
        bid = self._board(client)
        gid = self._group(client, bid)
        cid = self._card(client, bid)
        r = client.patch(
            f"/api/boards/{bid}/nodes/{cid}", json={"parent_group_id": gid}
        )
        assert r.status_code == 200
        assert r.json()["parent_group_id"] == gid

    def test_ungroup_via_patch(self, client):
        bid = self._board(client)
        gid = self._group(client, bid)
        cid = self._card(client, bid, parent_group_id=gid)
        r = client.patch(
            f"/api/boards/{bid}/nodes/{cid}", json={"parent_group_id": None}
        )
        assert r.status_code == 200
        assert r.json()["parent_group_id"] is None

    def test_reject_parent_not_group(self, client):
        bid = self._board(client)
        target = self._card(client, bid)
        r = client.post(
            f"/api/boards/{bid}/nodes",
            json={"kind": "card", "parent_group_id": target},
        )
        assert r.status_code == 400

    def test_reject_parent_on_other_board(self, client):
        b1 = self._board(client)
        b2 = self._board(client)
        g2 = self._group(client, b2)
        r = client.post(
            f"/api/boards/{b1}/nodes",
            json={"kind": "card", "parent_group_id": g2},
        )
        assert r.status_code == 400

    def test_reject_self_parent(self, client):
        bid = self._board(client)
        gid = self._group(client, bid)
        r = client.patch(
            f"/api/boards/{bid}/nodes/{gid}", json={"parent_group_id": gid}
        )
        assert r.status_code == 400

    def test_reject_cycle(self, client):
        bid = self._board(client)
        g1 = self._group(client, bid)
        g2 = self._group(client, bid, parent_group_id=g1)
        # g1 cannot become a child of g2 (cycle g1→g2→g1)
        r = client.patch(
            f"/api/boards/{bid}/nodes/{g1}", json={"parent_group_id": g2}
        )
        assert r.status_code == 400

    def test_translate_moves_group_and_children(self, client):
        bid = self._board(client)
        gid = self._group(client, bid, x=100, y=200)
        c1 = self._card(client, bid, x=120, y=220, parent_group_id=gid)
        c2 = self._card(client, bid, x=140, y=240, parent_group_id=gid)
        other = self._card(client, bid, x=500, y=500)
        r = client.post(
            f"/api/boards/{bid}/nodes/{gid}/translate",
            json={"dx": 10, "dy": -5},
        )
        assert r.status_code == 204, r.text
        detail = client.get(f"/api/boards/{bid}").json()
        coords = {n["id"]: (n["x"], n["y"]) for n in detail["nodes"]}
        assert coords[gid] == (110.0, 195.0)
        assert coords[c1] == (130.0, 215.0)
        assert coords[c2] == (150.0, 235.0)
        assert coords[other] == (500.0, 500.0)  # unaffected

    def test_translate_cascades_nested(self, client):
        bid = self._board(client)
        outer = self._group(client, bid, x=0, y=0)
        inner = self._group(client, bid, x=10, y=10, parent_group_id=outer)
        grandchild = self._card(client, bid, x=20, y=20, parent_group_id=inner)
        r = client.post(
            f"/api/boards/{bid}/nodes/{outer}/translate",
            json={"dx": 100, "dy": 0},
        )
        assert r.status_code == 204
        detail = client.get(f"/api/boards/{bid}").json()
        coords = {n["id"]: (n["x"], n["y"]) for n in detail["nodes"]}
        assert coords[outer] == (100.0, 0.0)
        assert coords[inner] == (110.0, 10.0)
        assert coords[grandchild] == (120.0, 20.0)

    def test_translate_rejects_non_group(self, client):
        bid = self._board(client)
        cid = self._card(client, bid)
        r = client.post(
            f"/api/boards/{bid}/nodes/{cid}/translate", json={"dx": 1, "dy": 1}
        )
        assert r.status_code == 400

    def test_delete_group_nulls_children_parent(self, client):
        bid = self._board(client)
        gid = self._group(client, bid)
        cid = self._card(client, bid, parent_group_id=gid)
        assert client.delete(f"/api/boards/{bid}/nodes/{gid}").status_code == 204
        detail = client.get(f"/api/boards/{bid}").json()
        child = next(n for n in detail["nodes"] if n["id"] == cid)
        assert child["parent_group_id"] is None

    def test_duplicate_preserves_group_structure(self, client):
        bid = self._board(client)
        gid = self._group(client, bid, title="Grp")
        c1 = self._card(client, bid, title="child1", parent_group_id=gid)
        c2 = self._card(client, bid, title="child2", parent_group_id=gid)  # noqa: F841
        new_id = client.post(f"/api/boards/{bid}/duplicate").json()["id"]
        detail = client.get(f"/api/boards/{new_id}").json()
        groups = [n for n in detail["nodes"] if n["kind"] == "group"]
        cards = [n for n in detail["nodes"] if n["kind"] == "card"]
        assert len(groups) == 1
        assert len(cards) == 2
        new_gid = groups[0]["id"]
        assert all(c["parent_group_id"] == new_gid for c in cards)
        # Ids must be remapped (not the source's).
        assert new_gid != gid
        assert all(c["id"] not in (c1,) for c in cards)

    def test_board_detail_includes_parent_group_id(self, client):
        bid = self._board(client)
        gid = self._group(client, bid)
        cid = self._card(client, bid, parent_group_id=gid)
        detail = client.get(f"/api/boards/{bid}").json()
        child = next(n for n in detail["nodes"] if n["id"] == cid)
        assert child["parent_group_id"] == gid


class TestBoardPortals:
    def _board(self, client, name="B") -> int:
        return client.post("/api/boards/", json={"name": name}).json()["id"]

    def test_create_board_portal(self, client):
        src = self._board(client, "Src")
        dst = self._board(client, "Dst")
        r = client.post(
            f"/api/boards/{src}/nodes",
            json={"kind": "board", "ref_id": dst, "x": 0, "y": 0},
        )
        assert r.status_code == 201, r.text
        data = r.json()
        assert data["kind"] == "board"
        assert data["ref_id"] == dst

    def test_portal_requires_ref_id(self, client):
        src = self._board(client)
        r = client.post(
            f"/api/boards/{src}/nodes", json={"kind": "board"}
        )
        assert r.status_code == 400

    def test_portal_rejects_self_reference(self, client):
        bid = self._board(client)
        r = client.post(
            f"/api/boards/{bid}/nodes",
            json={"kind": "board", "ref_id": bid},
        )
        assert r.status_code == 400

    def test_portal_rejects_missing_ref(self, client):
        bid = self._board(client)
        r = client.post(
            f"/api/boards/{bid}/nodes",
            json={"kind": "board", "ref_id": 999_999},
        )
        assert r.status_code == 400

    def test_portal_ref_summary(self, client):
        src = self._board(client, "Src")
        dst = self._board(client, "Dst")
        # populate dst with a couple of nodes + one edge
        a = client.post(
            f"/api/boards/{dst}/nodes", json={"kind": "card", "title": "a"}
        ).json()["id"]
        b = client.post(
            f"/api/boards/{dst}/nodes", json={"kind": "card", "title": "b"}
        ).json()["id"]
        client.post(
            f"/api/boards/{dst}/edges",
            json={"source_node_id": a, "target_node_id": b},
        )
        client.post(
            f"/api/boards/{src}/nodes",
            json={"kind": "board", "ref_id": dst},
        )
        detail = client.get(f"/api/boards/{src}").json()
        portal = next(n for n in detail["nodes"] if n["kind"] == "board")
        summary = portal["ref_summary"]
        assert summary is not None
        assert summary["id"] == dst
        assert summary["name"] == "Dst"
        assert summary["node_count"] == 2
        assert summary["edge_count"] == 1
        assert summary["last_modified"]

    def test_portal_tombstone_when_target_deleted(self, client):
        src = self._board(client, "Src")
        dst = self._board(client, "Dst")
        client.post(
            f"/api/boards/{src}/nodes",
            json={"kind": "board", "ref_id": dst},
        )
        client.delete(f"/api/boards/{dst}")
        detail = client.get(f"/api/boards/{src}").json()
        portal = next(n for n in detail["nodes"] if n["kind"] == "board")
        assert portal["ref_summary"] is None


class TestSearchAndBacklinks:
    def _board(self, client, name):
        return client.post("/api/boards/", json={"name": name}).json()["id"]

    def _note(self, client, title, body=""):
        return client.post("/api/notes/", json={"title": title, "body": body}).json()["id"]

    def test_search_empty_query_returns_empty(self, client):
        r = client.get("/api/search", params={"q": ""})
        assert r.status_code == 200
        assert r.json() == {"results": []}

    def test_search_finds_board_by_name(self, client):
        self._board(client, "Project Nebula")
        self._board(client, "Zebra Plans")
        res = client.get("/api/search", params={"q": "nebula"}).json()["results"]
        assert any(r["type"] == "board" and r["title"] == "Project Nebula" for r in res)

    def test_search_finds_note_by_body(self, client):
        self._note(client, "Meeting", "Discussed the quarterly roadmap today")
        res = client.get("/api/search", params={"q": "quarterly"}).json()["results"]
        assert any(r["type"] == "note" and "quarterly" in r["snippet"].lower() for r in res)

    def test_search_finds_card_body(self, client):
        bid = self._board(client, "Canvas")
        client.post(
            f"/api/boards/{bid}/nodes",
            json={"kind": "card", "title": "Idea", "body": "nebulous thoughts about pricing"},
        )
        res = client.get("/api/search", params={"q": "pricing"}).json()["results"]
        assert any(r["type"] == "card" and r["board_id"] == bid for r in res)

    def test_search_ignores_deleted_note(self, client):
        nid = self._note(client, "EphemeralTopic", "about clouds")
        client.delete(f"/api/notes/{nid}")
        res = client.get("/api/search", params={"q": "EphemeralTopic"}).json()["results"]
        assert not any(r["type"] == "note" and r["id"] == nid for r in res)

    def test_board_backlinks_portals(self, client):
        src = self._board(client, "Src")
        dst = self._board(client, "Dst")
        client.post(f"/api/boards/{src}/nodes", json={"kind": "board", "ref_id": dst})
        bl = client.get(f"/api/boards/{dst}/backlinks").json()
        assert len(bl["portals"]) == 1
        assert bl["portals"][0]["board_id"] == src

    def test_board_backlinks_wikilinks_in_cards(self, client):
        target = self._board(client, "Docs")
        other = self._board(client, "Scratch")
        client.post(
            f"/api/boards/{other}/nodes",
            json={"kind": "card", "title": "ref", "body": "see [[Docs]] for details"},
        )
        bl = client.get(f"/api/boards/{target}/backlinks").json()
        assert len(bl["cards"]) == 1
        assert bl["cards"][0]["board_id"] == other

    def test_board_backlinks_missing(self, client):
        assert client.get("/api/boards/9999/backlinks").status_code == 404

    def test_note_board_backlinks_via_ref_and_wikilink(self, client):
        nid = self._note(client, "ProjectNote")
        bid = self._board(client, "Canvas")
        client.post(f"/api/boards/{bid}/nodes", json={"kind": "note", "ref_id": nid})
        client.post(
            f"/api/boards/{bid}/nodes",
            json={"kind": "card", "body": "see [[ProjectNote]] please"},
        )
        bl = client.get(f"/api/notes/{nid}/board_backlinks").json()
        assert len(bl["refs"]) == 1
        assert len(bl["cards"]) == 1


class TestBoardTemplates:
    def test_list_includes_system_templates(self, client):
        r = client.get("/api/board-templates/")
        assert r.status_code == 200
        names = [t["name"] for t in r.json()]
        # System seed includes at least these.
        for expected in ["Sticky", "Checklist", "Meeting note"]:
            assert expected in names

    def test_system_templates_are_read_only(self, client):
        sys_tpl = next(t for t in client.get("/api/board-templates/").json() if t["is_system"])
        assert client.patch(f"/api/board-templates/{sys_tpl['id']}", json={"name": "X"}).status_code == 403
        assert client.delete(f"/api/board-templates/{sys_tpl['id']}").status_code == 403

    def test_create_and_update_user_template(self, client):
        created = client.post(
            "/api/board-templates/",
            json={"name": "My template", "body_md": "# Hello", "icon": "⭐"},
        )
        assert created.status_code == 201
        tid = created.json()["id"]
        patched = client.patch(f"/api/board-templates/{tid}", json={"body_md": "# Updated"})
        assert patched.status_code == 200
        assert patched.json()["body_md"] == "# Updated"

    def test_delete_user_template(self, client):
        tid = client.post(
            "/api/board-templates/",
            json={"name": "Ephemeral", "body_md": "x"},
        ).json()["id"]
        assert client.delete(f"/api/board-templates/{tid}").status_code == 204
        assert client.get(f"/api/board-templates/{tid}").status_code == 404

    def test_filter_by_category(self, client):
        r = client.get("/api/board-templates/", params={"category": "basic"})
        assert r.status_code == 200
        for t in r.json():
            assert t["category"] == "basic"


class TestNoteTemplates:
    def test_seeded_system_templates_present(self, client):
        names = [t["name"] for t in client.get("/api/note-templates/").json()]
        for expected in ["Daily journal", "Meeting note", "Bug report", "Project brief"]:
            assert expected in names

    def test_system_templates_are_read_only(self, client):
        sys_tpl = next(t for t in client.get("/api/note-templates/").json() if t["is_system"])
        assert client.patch(f"/api/note-templates/{sys_tpl['id']}", json={"name": "X"}).status_code == 403
        assert client.delete(f"/api/note-templates/{sys_tpl['id']}").status_code == 403

    def test_user_template_crud(self, client):
        t = client.post("/api/note-templates/", json={
            "name": "My note tpl",
            "body_md": "# {{title}}\n\nbody",
            "title_tpl": "{{date}} reflections",
        }).json()
        assert t["id"]
        u = client.patch(f"/api/note-templates/{t['id']}", json={"body_md": "# updated"}).json()
        assert u["body_md"] == "# updated"
        assert client.delete(f"/api/note-templates/{t['id']}").status_code == 204

    def test_apply_substitutes_variables(self, client):
        from datetime import datetime
        sys_tpl = next(
            t for t in client.get("/api/note-templates/").json()
            if t["name"] == "Daily journal"
        )
        r = client.post(f"/api/note-templates/{sys_tpl['id']}/apply")
        assert r.status_code == 201
        note = r.json()
        today = datetime.now().strftime("%Y-%m-%d")
        assert note["title"] == today
        assert today in note["body"]
        assert note["icon"] == "📅"

    def test_apply_with_override_title_and_folder(self, client):
        fid = client.post("/api/folders/", json={"name": "F"}).json()["id"]
        sys_tpl = next(
            t for t in client.get("/api/note-templates/").json()
            if t["name"] == "Meeting note"
        )
        r = client.post(
            f"/api/note-templates/{sys_tpl['id']}/apply",
            json={"folder_id": fid, "title": "Standup"},
        )
        note = r.json()
        assert note["title"] == "Standup"
        assert note["folder_id"] == fid
        # Body still gets {{title}} substituted with the resolved title
        assert "Standup" in note["body"]

    def test_apply_rejects_bad_folder(self, client):
        sys_tpl = next(t for t in client.get("/api/note-templates/").json())
        r = client.post(
            f"/api/note-templates/{sys_tpl['id']}/apply",
            json={"folder_id": 99999},
        )
        assert r.status_code == 400
