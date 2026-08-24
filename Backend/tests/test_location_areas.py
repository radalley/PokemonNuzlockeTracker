"""
WP4 tests: location areas.

Areas sit below canonical locations so a city's trainer panel can separate
its gym, its buildings, and its dungeon floors instead of listing everything
flat. Trainers standing in the location itself keep a null area.
"""
import pytest

import backend as backend_module
from etl import normalize
from etl.pipelines import derive_location_areas


def seed_location(db_conn, location_id, name):
    db_conn.execute(
        "insert into canon_locations (canonical_location_id, canonical_location_name) values (%s, %s)",
        (location_id, name),
    )
    db_conn.commit()


def seed_area(db_conn, location_id, name, *, kind="interior", vg=1, sort_order=1):
    row = db_conn.execute(
        "insert into location_areas (canonical_location_id, version_group_id, area_name, area_kind, sort_order) "
        "values (%s, %s, %s, %s, %s) returning area_id",
        (location_id, vg, name, kind, sort_order),
    ).fetchone()
    db_conn.commit()
    return row["area_id"]


def seed_trainer(db_conn, *, name, location_id, vg=1, area_id=None, details=None):
    row = db_conn.execute(
        "insert into trainer_pool (encounter_name, trainer_name, canonical_location_id, version_group_id, area_id, details) "
        "values (%s, %s, %s, %s, %s, %s) returning trainer_id",
        (f"TRAINER_{name}", name, location_id, vg, area_id, details),
    ).fetchone()
    db_conn.commit()
    return row["trainer_id"]


# ---------------------------------------------------------------------------
# name derivation
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("raw,expected", [
    ("CeladonGym", "Celadon Gym"),
    ("VermilionGym", "Vermilion Gym"),
    ("canalave_city_gym", "Canalave City Gym"),
    # Floor designators must survive the CamelCase split intact.
    ("PokemonTower3F", "Pokemon Tower 3F"),
    ("RocketHideoutB1F", "Rocket Hideout B1F"),
    ("MtMoon1F", "Mt Moon 1F"),
    ("SilphCo11F", "Silph Co 11F"),
    ("", ""),
])
def test_area_display_name(raw, expected):
    assert normalize.area_display_name(raw) == expected


def test_area_kind_flags_gyms():
    assert normalize.area_kind("Celadon Gym") == "gym"
    assert normalize.area_kind("Game Corner") == "interior"


@pytest.mark.parametrize("details,expected", [
    ("redblue_map=CeladonGym; source=object_event", "CeladonGym"),
    ("crystal_map=VioletGym; source=loadtrainer", "VioletGym"),
    ("matched_map=canalave_city_gym; x=1", "canalave_city_gym"),
    ("blackwhite_trainer_index=281; battle_type=0", None),
    ("", None),
])
def test_extract_map_name_handles_every_generation_key(details, expected):
    assert derive_location_areas.extract_map_name(details) == expected


# ---------------------------------------------------------------------------
# trainer list grouping
# ---------------------------------------------------------------------------

def test_trainer_list_returns_area_details(db_conn):
    seed_location(db_conn, 26, "Celadon City")
    gym = seed_area(db_conn, 26, "Celadon Gym", kind="gym", sort_order=1)
    seed_trainer(db_conn, name="ERIKA_GRUNT", location_id=26, area_id=gym)

    rows = [dict(r) for r in backend_module.get_trainers_by_location(db_conn, 26, version_group_id=1)]

    assert len(rows) == 1
    assert rows[0]["area_id"] == gym
    assert rows[0]["area_name"] == "Celadon Gym"
    assert rows[0]["area_kind"] == "gym"


def test_area_less_trainers_sort_before_areas(db_conn):
    seed_location(db_conn, 26, "Celadon City")
    gym = seed_area(db_conn, 26, "Celadon Gym", kind="gym", sort_order=1)
    hideout = seed_area(db_conn, 26, "Rocket Hideout B1F", sort_order=2)
    # Deliberately inserted out of display order.
    seed_trainer(db_conn, name="HIDEOUT_GRUNT", location_id=26, area_id=hideout)
    seed_trainer(db_conn, name="GYM_TRAINER", location_id=26, area_id=gym)
    seed_trainer(db_conn, name="OUTSIDE", location_id=26, area_id=None)

    rows = [dict(r) for r in backend_module.get_trainers_by_location(db_conn, 26, version_group_id=1)]

    assert [r["trainer_name"] for r in rows] == ["OUTSIDE", "GYM_TRAINER", "HIDEOUT_GRUNT"]
    assert [r["area_name"] for r in rows] == [None, "Celadon Gym", "Rocket Hideout B1F"]


def test_trainers_without_areas_are_unaffected(db_conn):
    seed_location(db_conn, 3, "Route 1")
    seed_trainer(db_conn, name="YOUNGSTER", location_id=3)

    rows = [dict(r) for r in backend_module.get_trainers_by_location(db_conn, 3, version_group_id=1)]

    assert len(rows) == 1
    assert rows[0]["area_id"] is None
    assert rows[0]["area_name"] is None


def test_areas_are_scoped_to_their_version_group(db_conn):
    seed_location(db_conn, 26, "Celadon City")
    gym_vg1 = seed_area(db_conn, 26, "Celadon Gym", kind="gym", vg=1)
    seed_trainer(db_conn, name="RB_GYM", location_id=26, vg=1, area_id=gym_vg1)
    seed_trainer(db_conn, name="YELLOW_GYM", location_id=26, vg=2, area_id=None)

    vg1 = [dict(r) for r in backend_module.get_trainers_by_location(db_conn, 26, version_group_id=1)]
    vg2 = [dict(r) for r in backend_module.get_trainers_by_location(db_conn, 26, version_group_id=2)]

    assert [r["trainer_name"] for r in vg1] == ["RB_GYM"]
    assert [r["trainer_name"] for r in vg2] == ["YELLOW_GYM"]


# ---------------------------------------------------------------------------
# derivation pipeline logic
# ---------------------------------------------------------------------------

def test_route_trainers_are_not_given_an_area():
    """A route trainer's source map IS the location, which is not a sub-area."""
    assert normalize.location_match_key("Route 1") == normalize.location_match_key("Route1")
    assert normalize.location_match_key("Mt. Moon") == normalize.location_match_key("MtMoon")
    assert normalize.location_match_key("CeladonGym") != normalize.location_match_key("Celadon City")


def test_derivation_load_guards_and_statements():
    candidates = [{
        "trainer_id": 1, "canonical_location_id": 26, "version_group_id": 1,
        "area_name": "Celadon Gym", "area_kind": "gym", "source_key": "CeladonGym",
    }]
    sql = derive_location_areas.build_load(candidates).build_sql(
        {"location_area_stage": "/tmp/s.csv"}, rollback=True
    )
    assert "INSERT INTO location_areas" in sql
    assert "SET area_id = la.area_id" in sql
    # Default run must not clobber curated assignments.
    assert "AND tp.area_id IS NULL" in sql
    assert "does not exist" in sql

    reassign = derive_location_areas.build_load(candidates, reassign=True).build_sql(
        {"location_area_stage": "/tmp/s.csv"}, rollback=True
    )
    assert "AND tp.area_id IS NULL" not in reassign
