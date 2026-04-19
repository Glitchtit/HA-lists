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


class TestWikilinkParser:
    def test_plain(self):
        from routers._wikilinks import extract_wikilinks
        assert extract_wikilinks("see [[Foo]] here") == [("Foo", "wikilink")]

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

    def test_target_rename_breaks_link(self, client):
        a = client.post("/api/notes/", json={"title": "A", "body": "ref [[B]]"}).json()["id"]
        b = client.post("/api/notes/", json={"title": "B"}).json()["id"]
        client.patch(f"/api/notes/{b}", json={"title": "B2"})
        assert client.get(f"/api/notes/{b}/backlinks").json() == []

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
