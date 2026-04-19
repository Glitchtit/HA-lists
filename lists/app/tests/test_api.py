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
