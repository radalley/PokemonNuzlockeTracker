"""
Encounter tables read path: the flat rows the encounter panel groups, the
species pool derived from the same rows, and the registry that rides along.
"""
from pathlib import Path

import backend as backend_module
import encounter_methods

MIGRATION_SQL = (
    Path(backend_module.__file__).resolve().parent / "migrations" / "20260916_encounter_tables.sql"
).read_text(encoding="utf-8")
TABLE_COLUMNS = ("area", "area_sort", "condition", "slot_kind", "tag", "note")


def test_encounter_tables_migration_adds_the_columns_once(db_conn):
    # Start from a pool without the columns, as production had them.
    for column in TABLE_COLUMNS:
        db_conn.execute(f"alter table encounter_pool drop column if exists {column}")
    db_conn.execute("create table if not exists schema_migrations (migration_name text primary key, applied_at timestamp with time zone not null default current_timestamp)")
    db_conn.execute("delete from schema_migrations where migration_name = 'encounter_tables_v1'")
    db_conn.commit()

    db_conn.execute(MIGRATION_SQL)
    db_conn.commit()
    db_conn.execute(MIGRATION_SQL)   # a second run must be a no-op
    db_conn.commit()

    columns = {r["column_name"]: r for r in db_conn.execute(
        "select column_name, is_nullable, column_default from information_schema.columns "
        "where table_name = 'encounter_pool'").fetchall()}
    assert set(TABLE_COLUMNS) <= set(columns)
    assert columns["slot_kind"]["is_nullable"] == "NO"
    assert "'slot'" in columns["slot_kind"]["column_default"]
    assert db_conn.execute(
        "select count(*) as n from schema_migrations where migration_name = 'encounter_tables_v1'").fetchone()["n"] == 1


def seed_species(db_conn):
    db_conn.execute(
        "insert into species (species_id, name) values "
        "(551, 'SANDILE'), (27, 'SANDSHREW'), (552, 'KROKOROK'), (377, 'REGIROCK'), "
        "(637, 'VOLCARONA'), (495, 'SNIVY'), (129, 'MAGIKARP'), (130, 'GYARADOS')"
    )


def seed_row(db_conn, *, game_id="1001", location_id=240, species_id, method, rate,
             area=None, area_sort=0, condition=None, slot_kind="slot", tag=None,
             min_level=None, note=None):
    db_conn.execute(
        "insert into encounter_pool (game_id, canonical_location_id, species_id, method, enounter_rate, "
        "area, area_sort, condition, slot_kind, tag, min_level, max_level, note) "
        "values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
        (game_id, location_id, species_id, method, rate, area, area_sort, condition, slot_kind, tag,
         min_level, min_level, note),
    )


def seed_relic_castle(db_conn):
    seed_species(db_conn)
    # inserted out of display order on purpose
    seed_row(db_conn, species_id=637, method="static", rate=None, area="Volcarona Room", area_sort=3,
             slot_kind="static", tag="special", min_level=75)
    seed_row(db_conn, species_id=377, method="sand", rate=1, area="B2F, B3F, B4F, B5F", area_sort=2,
             slot_kind="overlay", tag="legendary", min_level=50, note="deep down")
    seed_row(db_conn, species_id=27, method="sand", rate=40, area="1F", area_sort=1)
    seed_row(db_conn, species_id=551, method="sand", rate=60, area="1F", area_sort=1)
    seed_row(db_conn, species_id=552, method="sand", rate=100, area="B2F, B3F, B4F, B5F", area_sort=2)
    # a rippling-water table on the whole location, and the Volt White copy
    seed_row(db_conn, species_id=130, method="surf-spots", rate=100)
    seed_row(db_conn, species_id=129, method="surf", rate=100)
    seed_row(db_conn, game_id="1002", species_id=551, method="sand", rate=100, area="1F", area_sort=1)
    # an inherited Starter-style row: no method, pool only
    seed_row(db_conn, location_id=999, species_id=495, method=None, rate=None)
    db_conn.commit()


def test_rows_come_back_in_display_order(db_conn):
    seed_relic_castle(db_conn)

    rows = backend_module.load_encounter_rows(db_conn, [240, 999], 1001)

    relic = rows[240]
    assert [(r["area"], r["method"], r["slot_kind"], r["name"]) for r in relic] == [
        (None, "surf", "slot", "MAGIKARP"),
        (None, "surf-spots", "slot", "GYARADOS"),
        ("1F", "sand", "slot", "SANDILE"),
        ("1F", "sand", "slot", "SANDSHREW"),
        ("B2F, B3F, B4F, B5F", "sand", "slot", "KROKOROK"),
        ("B2F, B3F, B4F, B5F", "sand", "overlay", "REGIROCK"),
        ("Volcarona Room", "static", "static", "VOLCARONA"),
    ]
    regirock = next(r for r in relic if r["name"] == "REGIROCK")
    assert regirock == {
        "species_id": 377, "name": "REGIROCK", "method": "sand", "area": "B2F, B3F, B4F, B5F",
        "area_sort": 2, "condition": None, "slot_kind": "overlay", "tag": "legendary",
        "rate": 1, "min_level": 50, "max_level": 50, "note": "deep down",
    }
    # the Volt White row never leaks into the Blaze Black read
    assert all(r["name"] != "SANDILE" or r["rate"] == 60 for r in relic)
    # the starter row rides along for the pool, without a method
    assert [(r["name"], r["method"]) for r in rows[999]] == [("SNIVY", None)]


def test_pools_and_tables_derive_from_the_same_rows(db_conn):
    seed_relic_castle(db_conn)
    rows = backend_module.load_encounter_rows(db_conn, [240, 999], 1001)

    pools = backend_module.pools_from_rows(rows)
    tables = backend_module.tables_from_rows(rows)

    # one entry per species, first seen wins, including the method-less row
    assert [p["name"] for p in pools[240]] == ["MAGIKARP", "GYARADOS", "SANDILE", "SANDSHREW", "KROKOROK", "REGIROCK", "VOLCARONA"]
    assert pools[999] == [{"species_id": 495, "name": "SNIVY"}]
    # tables drop rows without a method
    assert tables[999] == []
    assert len(tables[240]) == 7


def test_missing_locations_and_games_are_harmless(db_conn):
    seed_relic_castle(db_conn)
    assert backend_module.load_encounter_rows(db_conn, [], 1001) == {}
    assert backend_module.load_encounter_rows(db_conn, [240], None) == {}
    assert backend_module.load_encounter_rows(db_conn, [12345], 1001) == {}


def test_registry_rides_with_the_page():
    methods = backend_module.get_encounter_methods()
    assert [m["key"] for m in methods] == encounter_methods.METHOD_KEYS
    assert all({"key", "label", "group", "is_rare", "sort_order", "description"} <= set(m) for m in methods)
    # a copy: mutating it cannot touch the registry
    methods[0]["label"] = "changed"
    assert encounter_methods.METHODS[0]["label"] != "changed"


def test_attempt_page_carries_tables_and_methods(db_conn):
    db_conn.execute(
        "insert into games (game_id, name, game_tag, generation, version_group_id) values (1001, 'Blaze Black', 'BB', 5, 1001)")
    run_id = db_conn.execute(
        "insert into runs (game_id, name, user_id) values (1001, 'Run', 1) returning run_id").fetchone()["run_id"]
    db_conn.execute("insert into attempts (run_id, attempt_number, starter) values (%s, 1, 'Fire')", (run_id,))
    db_conn.execute(
        "insert into canon_locations (canonical_location_id, canonical_location_name) values (240, 'Relic Castle')")
    db_conn.execute(
        "insert into event_locations (canonical_location_id, version_group_id, sort_order, secondary_sort_order, event_type) "
        "values (240, 1001, 1, 0, 'Location')")
    seed_relic_castle(db_conn)

    page = backend_module.get_attempt_page_data(db_conn, run_id, 1)

    assert [p["name"] for p in page["pools"][240]][:3] == ["MAGIKARP", "GYARADOS", "SANDILE"]
    assert [r["name"] for r in page["pool_tables"][240]][-1] == "VOLCARONA"
    assert page["encounter_methods"][0]["key"] == "grass"


def test_tables_keep_only_registry_methods_and_omit_empty_fields(db_conn):
    seed_relic_castle(db_conn)
    # A pool loaded before the reparse still carries the old method keys:
    # it must stay a plain pool, not merge every floor into one table.
    seed_row(db_conn, location_id=241, species_id=551, method="sand-normal", rate=60)
    seed_row(db_conn, location_id=241, species_id=27, method="sand-normal", rate=60)
    db_conn.commit()
    rows = backend_module.load_encounter_rows(db_conn, [240, 241], 1001)

    tables = backend_module.tables_from_rows(rows)

    assert tables[241] == []
    assert [p["name"] for p in backend_module.pools_from_rows(rows)[241]] == ["SANDILE", "SANDSHREW"]
    by_name = {r["name"]: r for r in tables[240]}
    # empty fields are left out of the payload; the ones a row has stay
    assert by_name["SANDILE"] == {"species_id": 551, "name": "SANDILE", "method": "sand", "area": "1F",
                                  "area_sort": 1, "slot_kind": "slot", "rate": 60}
    assert by_name["MAGIKARP"] == {"species_id": 129, "name": "MAGIKARP", "method": "surf", "area_sort": 0,
                                   "slot_kind": "slot", "rate": 100}
    assert by_name["VOLCARONA"]["slot_kind"] == "static" and "rate" not in by_name["VOLCARONA"]
    assert by_name["REGIROCK"]["note"] == "deep down"


def test_column_probe_only_sees_the_current_schema(db_conn):
    db_conn.execute("create schema if not exists probe_elsewhere")
    db_conn.execute("create table if not exists probe_elsewhere.encounter_pool_probe (area text)")
    db_conn.commit()
    try:
        assert backend_module._has_column(db_conn, "encounter_pool", "area") is True
        assert backend_module._has_column(db_conn, "encounter_pool_probe", "area") is False
    finally:
        db_conn.execute("drop schema probe_elsewhere cascade")
        db_conn.commit()


def test_guest_script_route_carries_pools_tables_and_methods(client, db_conn, monkeypatch):
    import api as api_module
    monkeypatch.setattr(api_module, "get_db", lambda: db_conn)
    db_conn.execute(
        "insert into games (game_id, name, game_tag, generation, version_group_id) values (1001, 'Blaze Black', 'BB', 5, 1001)")
    db_conn.execute(
        "insert into canon_locations (canonical_location_id, canonical_location_name) values (240, 'Relic Castle')")
    db_conn.execute(
        "insert into event_locations (canonical_location_id, version_group_id, sort_order, secondary_sort_order, event_type) "
        "values (240, 1001, 1, 0, 'Location')")
    seed_relic_castle(db_conn)

    response = client.get("/api/guest-script?game_id=1001&version_group_id=1001")

    assert response.status_code == 200
    payload = response.get_json()
    assert [p["name"] for p in payload["pools"]["240"]][:3] == ["MAGIKARP", "GYARADOS", "SANDILE"]
    tables = payload["pool_tables"]["240"]
    assert [r["name"] for r in tables] == ["MAGIKARP", "GYARADOS", "SANDILE", "SANDSHREW", "KROKOROK", "REGIROCK", "VOLCARONA"]
    # empty fields stay out of the JSON too
    assert "condition" not in tables[0] and tables[-1]["slot_kind"] == "static"
    assert [m["key"] for m in payload["encounter_methods"]] == encounter_methods.METHOD_KEYS


def test_all_seasons_rows_come_before_seasonal_ones_and_slots_before_overlays(db_conn):
    seed_species(db_conn)
    seed_row(db_conn, species_id=551, method="grass", rate=100, condition="season:winter")
    seed_row(db_conn, species_id=27, method="grass", rate=100, condition="season:spring,summer,autumn")
    seed_row(db_conn, species_id=552, method="grass", rate=100)
    # an overlay at the same rate as a slot still follows it
    seed_row(db_conn, species_id=377, method="grass", rate=100, slot_kind="overlay", tag="legendary")
    db_conn.commit()

    rows = backend_module.load_encounter_rows(db_conn, [240], 1001)[240]

    assert [(r["condition"], r["slot_kind"], r["name"]) for r in rows] == [
        (None, "slot", "KROKOROK"),
        (None, "overlay", "REGIROCK"),
        ("season:spring,summer,autumn", "slot", "SANDSHREW"),
        ("season:winter", "slot", "SANDILE"),
    ]


def test_pool_lists_a_species_once_when_several_tables_carry_it(db_conn):
    seed_species(db_conn)
    seed_row(db_conn, species_id=551, method="sand", rate=60, area="1F", area_sort=1)
    seed_row(db_conn, species_id=27, method="sand", rate=40, area="1F", area_sort=1)
    seed_row(db_conn, species_id=551, method="sand", rate=30, area="B2F", area_sort=2)
    db_conn.commit()

    rows = backend_module.load_encounter_rows(db_conn, [240], 1001)

    assert backend_module.pools_from_rows(rows)[240] == [
        {"species_id": 551, "name": "SANDILE"}, {"species_id": 27, "name": "SANDSHREW"},
    ]
    # the tables keep both Sandile slots
    assert [r["name"] for r in backend_module.tables_from_rows(rows)[240]] == ["SANDILE", "SANDSHREW", "SANDILE"]
