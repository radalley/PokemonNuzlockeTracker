"""
Curated trainer order within a location area.

An admin ranks the trainers of one route/area in the order the player
meets them. The rank is a placement-style curation: it lands on
trainer_pool for reads and on curated_trainer_placements so re-extraction
re-applies it. Reordering never moves a trainer between locations.
"""
import pytest

import backend as backend_module
from etl import curation


def seed_location(db_conn, location_id, name):
    db_conn.execute(
        "insert into canon_locations (canonical_location_id, canonical_location_name) values (%s, %s)",
        (location_id, name),
    )


def seed_trainer(db_conn, *, key, location_id, vg=1, area_id=None, game_id=None):
    row = db_conn.execute(
        "insert into trainer_pool (encounter_name, trainer_name, canonical_location_id, version_group_id, area_id, game_id) "
        "values (%s, %s, %s, %s, %s, %s) returning trainer_id",
        (key, key.replace("TRAINER_", "").title(), location_id, vg, area_id, game_id),
    ).fetchone()
    return row["trainer_id"]


def seed_route(db_conn):
    """Route 3 with three area-less trainers (ids ascending A, B, C)."""
    seed_location(db_conn, 3, "Route 3")
    seed_location(db_conn, 4, "Route 4")
    a = seed_trainer(db_conn, key="TRAINER_A", location_id=3)
    b = seed_trainer(db_conn, key="TRAINER_B", location_id=3)
    c = seed_trainer(db_conn, key="TRAINER_C", location_id=3)
    db_conn.commit()
    return a, b, c


def listed_keys(db_conn, location_id, vg=1):
    return [r["encounter_name"] for r in backend_module.get_trainers_by_location(db_conn, location_id, version_group_id=vg)]


def test_unordered_trainers_list_by_id(db_conn):
    seed_route(db_conn)
    assert listed_keys(db_conn, 3) == ["TRAINER_A", "TRAINER_B", "TRAINER_C"]


def test_set_order_ranks_the_group_and_curates_it(db_conn):
    a, b, c = seed_route(db_conn)

    result = backend_module.set_trainer_order(db_conn, [c, a, b])

    assert result["canonical_location_id"] == 3
    assert result["area_id"] is None
    assert result["order"] == [
        {"trainer_id": c, "sort_order": 1},
        {"trainer_id": a, "sort_order": 2},
        {"trainer_id": b, "sort_order": 3},
    ]
    assert listed_keys(db_conn, 3) == ["TRAINER_C", "TRAINER_A", "TRAINER_B"]
    curated = {r["trainer_key"]: dict(r) for r in db_conn.execute(
        "select trainer_key, canonical_location_id, area_id, sort_order from curated_trainer_placements "
        "where version_group_id = 1").fetchall()}
    assert curated["TRAINER_C"] == {"trainer_key": "TRAINER_C", "canonical_location_id": 3, "area_id": None, "sort_order": 1}
    assert curated["TRAINER_B"]["sort_order"] == 3

    # A second pass re-ranks in place (no duplicate curated rows).
    backend_module.set_trainer_order(db_conn, [b, c, a])
    assert listed_keys(db_conn, 3) == ["TRAINER_B", "TRAINER_C", "TRAINER_A"]
    assert db_conn.execute(
        "select count(*) as n from curated_trainer_placements where version_group_id = 1").fetchone()["n"] == 3


def test_ordering_keeps_an_existing_placement_decision(db_conn):
    """Ranking a trainer whose curated row already holds a location/area
    must not overwrite that decision."""
    a, b, c = seed_route(db_conn)
    db_conn.execute(
        "insert into curated_trainer_placements (version_group_id, trainer_key, canonical_location_id, area_id, note) "
        "values (1, 'TRAINER_A', 3, null, 'stands by the gate')")
    db_conn.commit()

    backend_module.set_trainer_order(db_conn, [b, a, c])

    row = db_conn.execute(
        "select canonical_location_id, note, sort_order from curated_trainer_placements "
        "where version_group_id = 1 and trainer_key = 'TRAINER_A'").fetchone()
    assert row["canonical_location_id"] == 3
    assert row["note"] == "stands by the gate"
    assert row["sort_order"] == 2


def test_order_survives_reextraction(db_conn):
    a, b, c = seed_route(db_conn)
    backend_module.set_trainer_order(db_conn, [c, b, a])

    # Re-extraction recreates the pool rows without any order...
    db_conn.execute("delete from trainer_pool where version_group_id = 1")
    seed_trainer(db_conn, key="TRAINER_A", location_id=3)
    seed_trainer(db_conn, key="TRAINER_B", location_id=3)
    seed_trainer(db_conn, key="TRAINER_C", location_id=3)
    db_conn.commit()
    assert listed_keys(db_conn, 3) == ["TRAINER_A", "TRAINER_B", "TRAINER_C"]

    # ...and the loaders' re-apply step restores it.
    db_conn.execute(curation.apply_curated_placements_sql(1))
    db_conn.commit()
    assert listed_keys(db_conn, 3) == ["TRAINER_C", "TRAINER_B", "TRAINER_A"]


def test_unordered_rows_follow_ordered_ones(db_conn):
    a, b, c = seed_route(db_conn)
    d = seed_trainer(db_conn, key="TRAINER_D", location_id=3)
    db_conn.commit()

    backend_module.set_trainer_order(db_conn, [d, b])

    # D and B are ranked; A and C keep their id order after them.
    assert listed_keys(db_conn, 3) == ["TRAINER_D", "TRAINER_B", "TRAINER_A", "TRAINER_C"]


def test_order_is_scoped_to_an_area(db_conn):
    seed_location(db_conn, 54, "Pewter City")
    gym = db_conn.execute(
        "insert into location_areas (canonical_location_id, version_group_id, area_name, area_kind, sort_order) "
        "values (54, 1, 'Pewter Gym', 'gym', 1) returning area_id").fetchone()["area_id"]
    street = seed_trainer(db_conn, key="TRAINER_STREET", location_id=54)
    g1 = seed_trainer(db_conn, key="TRAINER_GYM_1", location_id=54, area_id=gym)
    g2 = seed_trainer(db_conn, key="TRAINER_GYM_2", location_id=54, area_id=gym)
    db_conn.commit()

    backend_module.set_trainer_order(db_conn, [g2, g1])
    assert listed_keys(db_conn, 54) == ["TRAINER_STREET", "TRAINER_GYM_2", "TRAINER_GYM_1"]

    # The street trainer and the gym trainers are different groups.
    with pytest.raises(ValueError, match="one location area"):
        backend_module.set_trainer_order(db_conn, [street, g1])


def test_order_rejects_trainers_from_another_location(db_conn):
    a, b, c = seed_route(db_conn)
    elsewhere = seed_trainer(db_conn, key="TRAINER_ELSEWHERE", location_id=4)
    db_conn.commit()

    with pytest.raises(ValueError, match="one location area"):
        backend_module.set_trainer_order(db_conn, [a, elsewhere, b])
    # nothing was ranked
    assert db_conn.execute(
        "select count(*) as n from trainer_pool where sort_order is not null").fetchone()["n"] == 0


def test_replacing_a_ranked_trainer_drops_its_rank(db_conn):
    """A rank belongs to the group it was given in."""
    a, b, c = seed_route(db_conn)
    d = seed_trainer(db_conn, key="TRAINER_D", location_id=4)
    e = seed_trainer(db_conn, key="TRAINER_E", location_id=4)
    db_conn.execute(
        "insert into event_locations (canonical_location_id, version_group_id, sort_order, event_type) "
        "values (3, 1, 1, 'Location'), (4, 1, 2, 'Location')")
    db_conn.commit()
    backend_module.set_trainer_order(db_conn, [c, b, a])
    backend_module.set_trainer_order(db_conn, [e, d])

    backend_module.apply_trainer_placements(db_conn, 1, [{"trainer_key": "TRAINER_C", "canonical_location_id": 4}])

    assert listed_keys(db_conn, 3) == ["TRAINER_B", "TRAINER_A"]
    # C arrives unranked: after Route 4's own order, not ahead of it
    assert listed_keys(db_conn, 4) == ["TRAINER_E", "TRAINER_D", "TRAINER_C"]
    row = db_conn.execute(
        "select sort_order from curated_trainer_placements where version_group_id = 1 and trainer_key = 'TRAINER_C'").fetchone()
    assert row["sort_order"] is None

    # Re-placing at the same spot keeps the rank.
    backend_module.apply_trainer_placements(db_conn, 1, [{"trainer_key": "TRAINER_E", "canonical_location_id": 4}])
    assert listed_keys(db_conn, 4) == ["TRAINER_E", "TRAINER_D", "TRAINER_C"]


def test_ranking_one_game_view_keeps_the_other_game_coherent(db_conn):
    """Version-exclusive trainers share the group but not the view; the
    ones left out of a request trail the new ranking in their old order."""
    seed_location(db_conn, 3, "Route 3")
    s1 = seed_trainer(db_conn, key="TRAINER_S1", location_id=3)
    s2 = seed_trainer(db_conn, key="TRAINER_S2", location_id=3)
    a1 = seed_trainer(db_conn, key="TRAINER_A1", location_id=3, game_id=10)
    b1 = seed_trainer(db_conn, key="TRAINER_B1", location_id=3, game_id=11)
    db_conn.commit()
    view = lambda game: [r["encounter_name"] for r in backend_module.get_trainers_by_location(db_conn, 3, version_group_id=1, game_id=game)]

    backend_module.set_trainer_order(db_conn, [a1, s1, s2])          # from game 10's view
    assert view(10) == ["TRAINER_A1", "TRAINER_S1", "TRAINER_S2"]
    assert view(11) == ["TRAINER_S1", "TRAINER_S2", "TRAINER_B1"]     # B1 unranked, trails

    backend_module.set_trainer_order(db_conn, [s1, s2, b1])          # from game 11's view
    assert view(11) == ["TRAINER_S1", "TRAINER_S2", "TRAINER_B1"]
    # A1 was ranked before: it keeps a rank, behind the fresh 1..3, no tie
    assert view(10) == ["TRAINER_S1", "TRAINER_S2", "TRAINER_A1"]
    ranks = {r["encounter_name"]: r["sort_order"] for r in db_conn.execute(
        "select encounter_name, sort_order from trainer_pool where version_group_id = 1").fetchall()}
    assert ranks == {"TRAINER_S1": 1, "TRAINER_S2": 2, "TRAINER_B1": 3, "TRAINER_A1": 4}
    assert db_conn.execute(
        "select sort_order from curated_trainer_placements where trainer_key = 'TRAINER_A1'").fetchone()["sort_order"] == 4


def test_order_rejects_bad_input(db_conn):
    a, b, c = seed_route(db_conn)
    unplaced = seed_trainer(db_conn, key="TRAINER_LOST", location_id=None)
    db_conn.commit()

    with pytest.raises(ValueError):
        backend_module.set_trainer_order(db_conn, [])
    with pytest.raises(ValueError, match="repeats"):
        backend_module.set_trainer_order(db_conn, [a, a])
    with pytest.raises(ValueError, match="Unknown"):
        backend_module.set_trainer_order(db_conn, [a, 999999])
    with pytest.raises(ValueError, match="integers"):
        backend_module.set_trainer_order(db_conn, [a, "x"])
    with pytest.raises(ValueError, match="integers"):
        backend_module.set_trainer_order(db_conn, [a, True])
    with pytest.raises(ValueError, match="integers"):
        backend_module.set_trainer_order(db_conn, [a, 1.5])
    # digit strings (JSON clients sometimes send them) are fine
    backend_module.set_trainer_order(db_conn, [str(b), a])
    assert listed_keys(db_conn, 3)[:2] == ["TRAINER_B", "TRAINER_A"]
    with pytest.raises(ValueError, match="placed"):
        backend_module.set_trainer_order(db_conn, [unplaced])
