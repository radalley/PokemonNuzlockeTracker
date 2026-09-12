"""Renaming a run from the Load Run screen."""
import pytest

import backend as backend_module


def seed_run(db_conn, name="Test Run"):
    db_conn.execute(
        "insert into games (game_id, name, version_group_id, generation) "
        "values (17, 'Black', 11, 5) on conflict do nothing"
    )
    run_id = db_conn.execute(
        "insert into runs (game_id, name) values (17, %s) returning run_id", (name,)
    ).fetchone()["run_id"]
    db_conn.commit()
    return run_id


def test_rename_run_updates_name_and_trims(db_conn):
    run_id = seed_run(db_conn)
    assert backend_module.rename_run(db_conn, run_id, "  Monotype Water  ") == "Monotype Water"
    row = db_conn.execute("select name from runs where run_id = %s", (run_id,)).fetchone()
    assert row["name"] == "Monotype Water"


def test_rename_run_rejects_blank_and_missing(db_conn):
    run_id = seed_run(db_conn)
    with pytest.raises(ValueError):
        backend_module.rename_run(db_conn, run_id, "   ")
    assert backend_module.rename_run(db_conn, 999999, "Ghost") is None
    row = db_conn.execute("select name from runs where run_id = %s", (run_id,)).fetchone()
    assert row["name"] == "Test Run"


# ---------------------------------------------------------------------------
# PATCH /api/runs/<run_id> (route wiring; ownership + validation)
# ---------------------------------------------------------------------------

import api as api_module


def _patch_auth(monkeypatch, owns=True):
    monkeypatch.setattr(api_module, "get_current_user", lambda: {"user_id": 1})
    monkeypatch.setattr(api_module, "run_belongs_to_user", lambda conn, run_id, user_id: owns)
    monkeypatch.setattr(api_module, "get_db", lambda: "fake-conn")


def test_rename_route_updates_owned_run(client, monkeypatch):
    _patch_auth(monkeypatch)
    calls = []

    def fake_rename(conn, run_id, name):
        calls.append((run_id, name))
        return name.strip()

    monkeypatch.setattr(api_module, "rename_run", fake_rename)
    res = client.patch("/api/runs/42", json={"run_name": "  Wonderlocke "})
    assert res.status_code == 200
    assert res.get_json() == {"success": True, "run_name": "Wonderlocke"}
    assert calls == [(42, "  Wonderlocke ")]


def test_rename_route_rejects_blank_and_non_owner(client, monkeypatch):
    _patch_auth(monkeypatch)
    monkeypatch.setattr(api_module, "rename_run", backend_module.rename_run)
    res = client.patch("/api/runs/42", json={"run_name": "   "})
    assert res.status_code == 400

    _patch_auth(monkeypatch, owns=False)
    res = client.patch("/api/runs/42", json={"run_name": "Stolen"})
    assert res.status_code == 404
