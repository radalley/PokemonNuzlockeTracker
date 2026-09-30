"""
WP5 tests: placement curation.

Covers the suggestion matcher, the admin placement functions, and the
guarantee the whole feature exists for: curated decisions survive
re-extraction because loaders re-apply curated_trainer_placements.
"""
import pytest

import backend as backend_module
from etl import curation
from etl.pipelines.build_placement_suggestions import location_stem, suggest_locations


# ---------------------------------------------------------------------------
# suggestion matching
# ---------------------------------------------------------------------------

LOCATIONS = [
    (1, "Route 1"),
    (10, "Route 10"),
    (54, "Pewter City"),
    (26, "Celadon City"),
    (99, "Mt. Moon"),
]


def test_exact_match_wins():
    assert suggest_locations("Route 10", LOCATIONS) == [(10, "Route 10")]


def test_route1_does_not_match_inside_route10():
    matches = suggest_locations("Route10Gate", LOCATIONS)
    assert matches == [(10, "Route 10")]


def test_gym_map_matches_city_by_stem():
    assert suggest_locations("PewterGym", LOCATIONS) == [(54, "Pewter City")]


def test_unrelated_map_matches_nothing():
    assert suggest_locations("SilphCo7F", LOCATIONS) == []


def test_punctuated_location_matches():
    assert suggest_locations("MtMoonB2F", LOCATIONS) == [(99, "Mt. Moon")]


def test_location_stem_strips_settlement_suffixes():
    assert location_stem("pewtercity") == "pewter"
    assert location_stem("route10") == "route10"


# ---------------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------------

def seed_world(db_conn):
    db_conn.execute(
        "insert into canon_locations (canonical_location_id, canonical_location_name) "
        "values (54, 'Pewter City'), (26, 'Celadon City'), (3, 'Route 3')"
    )
    # Pewter City and Route 3 are in the vg-1 script; Celadon City is not.
    db_conn.execute(
        "insert into event_locations (canonical_location_id, version_group_id, sort_order, event_type) "
        "values (54, 1, 1, 'Location'), (3, 1, 2, 'Location')"
    )
    db_conn.commit()


def seed_unplaced(db_conn, *, key, vg=1, name="Tester", details=None):
    row = db_conn.execute(
        "insert into trainer_pool (encounter_name, trainer_name, version_group_id, details) "
        "values (%s, %s, %s, %s) returning trainer_id",
        (key, name, vg, details),
    ).fetchone()
    db_conn.commit()
    return row["trainer_id"]


def seed_suggestion(db_conn, *, key, location_id, vg=1, area_name=None, source="map_reference", detail=None):
    db_conn.execute(
        "insert into trainer_placement_suggestions "
        "(version_group_id, trainer_key, canonical_location_id, area_name, source, detail) "
        "values (%s, %s, %s, %s, %s, %s)",
        (vg, key, location_id, area_name, source, detail),
    )
    db_conn.commit()


# ---------------------------------------------------------------------------
# admin read paths
# ---------------------------------------------------------------------------

def test_summary_counts_placement_state(db_conn):
    seed_world(db_conn)
    seed_unplaced(db_conn, key="TRAINER_A")
    seed_unplaced(db_conn, key="TRAINER_B")
    db_conn.execute(
        "insert into trainer_pool (encounter_name, trainer_name, version_group_id, canonical_location_id) "
        "values ('TRAINER_PLACED', 'Placed', 1, 54)"
    )
    db_conn.commit()
    seed_suggestion(db_conn, key="TRAINER_A", location_id=54)

    summary = [dict(r) for r in backend_module.get_placement_summary(db_conn)]

    row = next(r for r in summary if r["version_group_id"] == 1)
    assert row["total_trainers"] == 3
    assert row["placed"] == 1
    assert row["unplaced"] == 2
    assert row["unplaced_with_suggestions"] == 1


def test_unplaced_listing_includes_suggestions_and_script_flag(db_conn):
    seed_world(db_conn)
    seed_unplaced(db_conn, key="TRAINER_GYM_GUY")
    seed_suggestion(db_conn, key="TRAINER_GYM_GUY", location_id=54,
                    area_name="Pewter Gym", detail="PewterGym")
    seed_suggestion(db_conn, key="TRAINER_GYM_GUY", location_id=26, source="serebii")

    trainers = backend_module.get_unplaced_trainers(db_conn, 1)

    assert len(trainers) == 1
    suggestions = trainers[0]["suggestions"]
    assert len(suggestions) == 2
    by_location = {s["canonical_location_id"]: s for s in suggestions}
    assert by_location[54]["in_script"] is True
    assert by_location[54]["area_name"] == "Pewter Gym"
    assert by_location[26]["in_script"] is False  # Celadon not in vg-1 script


def test_only_suggested_filter(db_conn):
    seed_world(db_conn)
    seed_unplaced(db_conn, key="TRAINER_WITH")
    seed_unplaced(db_conn, key="TRAINER_WITHOUT")
    seed_suggestion(db_conn, key="TRAINER_WITH", location_id=54)

    everything = backend_module.get_unplaced_trainers(db_conn, 1)
    suggested = backend_module.get_unplaced_trainers(db_conn, 1, only_suggested=True)

    assert {t["encounter_name"] for t in everything} == {"TRAINER_WITH", "TRAINER_WITHOUT"}
    assert [t["encounter_name"] for t in suggested] == ["TRAINER_WITH"]


# ---------------------------------------------------------------------------
# applying placements
# ---------------------------------------------------------------------------

def test_apply_placement_updates_pool_and_curated_and_creates_area(db_conn):
    seed_world(db_conn)
    trainer_id = seed_unplaced(db_conn, key="TRAINER_GYM_GUY")

    results = backend_module.apply_trainer_placements(db_conn, 1, [{
        "trainer_key": "TRAINER_GYM_GUY",
        "canonical_location_id": 54,
        "area_name": "Pewter Gym",
    }])

    assert results[0]["trainers_updated"] == 1
    pool = db_conn.execute(
        "select canonical_location_id, area_id from trainer_pool where trainer_id = %s",
        (trainer_id,),
    ).fetchone()
    assert pool["canonical_location_id"] == 54
    area = db_conn.execute(
        "select area_name, area_kind, version_group_id from location_areas where area_id = %s",
        (pool["area_id"],),
    ).fetchone()
    assert area["area_name"] == "Pewter Gym"
    assert area["area_kind"] == "gym"
    assert area["version_group_id"] == 1
    curated = db_conn.execute(
        "select canonical_location_id, area_id from curated_trainer_placements "
        "where version_group_id = 1 and trainer_key = 'TRAINER_GYM_GUY'"
    ).fetchone()
    assert curated["canonical_location_id"] == 54
    assert curated["area_id"] == pool["area_id"]


def test_apply_placement_reuses_existing_area(db_conn):
    seed_world(db_conn)
    seed_unplaced(db_conn, key="TRAINER_ONE")
    seed_unplaced(db_conn, key="TRAINER_TWO")

    backend_module.apply_trainer_placements(db_conn, 1, [
        {"trainer_key": "TRAINER_ONE", "canonical_location_id": 54, "area_name": "Pewter Gym"},
        {"trainer_key": "TRAINER_TWO", "canonical_location_id": 54, "area_name": "Pewter Gym"},
    ])

    areas = db_conn.execute("select count(*) as n from location_areas").fetchone()
    assert areas["n"] == 1


def test_apply_placement_rejects_unknown_targets(db_conn):
    seed_world(db_conn)
    seed_unplaced(db_conn, key="TRAINER_A")

    with pytest.raises(ValueError):
        backend_module.apply_trainer_placements(db_conn, 1, [
            {"trainer_key": "TRAINER_A", "canonical_location_id": 999},
        ])
    with pytest.raises(ValueError):
        backend_module.apply_trainer_placements(db_conn, 1, [
            {"trainer_key": "TRAINER_NOBODY", "canonical_location_id": 54},
        ])


def test_recuration_overwrites_previous_decision(db_conn):
    seed_world(db_conn)
    seed_unplaced(db_conn, key="TRAINER_A")

    backend_module.apply_trainer_placements(db_conn, 1, [
        {"trainer_key": "TRAINER_A", "canonical_location_id": 54},
    ])
    backend_module.apply_trainer_placements(db_conn, 1, [
        {"trainer_key": "TRAINER_A", "canonical_location_id": 3},
    ])

    curated = db_conn.execute(
        "select canonical_location_id from curated_trainer_placements "
        "where version_group_id = 1 and trainer_key = 'TRAINER_A'"
    ).fetchone()
    assert curated["canonical_location_id"] == 3


# ---------------------------------------------------------------------------
# curation survives re-extraction
# ---------------------------------------------------------------------------

def test_curated_placements_reapply_after_reload(db_conn):
    """Simulates a loader re-run: rows recreated unplaced, then the curated
    UPDATE (which loaders embed in their transaction) restores the decision."""
    seed_world(db_conn)
    seed_unplaced(db_conn, key="TRAINER_A")
    backend_module.apply_trainer_placements(db_conn, 1, [
        {"trainer_key": "TRAINER_A", "canonical_location_id": 54, "area_name": "Pewter Gym"},
    ])

    # Re-extraction: the trainer row is dropped and recreated with no location.
    db_conn.execute("delete from trainer_pool where encounter_name = 'TRAINER_A'")
    new_id = seed_unplaced(db_conn, key="TRAINER_A")

    db_conn.execute(curation.apply_curated_placements_sql(1))
    db_conn.commit()

    row = db_conn.execute(
        "select canonical_location_id, area_id from trainer_pool where trainer_id = %s",
        (new_id,),
    ).fetchone()
    assert row["canonical_location_id"] == 54
    assert row["area_id"] is not None


def test_curated_flags_and_game_apply_to_pool(db_conn):
    """Curated is_rematch/is_event/game_id land on trainer_pool as '1'/'0'
    text and integer; NULL curated flags leave extractor values alone."""
    seed_world(db_conn)
    flagged = seed_unplaced(db_conn, key="TRAINER_STADIUM")
    untouched = seed_unplaced(db_conn, key="TRAINER_ROUTE")
    db_conn.execute(
        "update trainer_pool set is_rematch = 'extractor', is_event = 'extractor' "
        "where trainer_id = %s", (untouched,))
    db_conn.execute(
        "insert into curated_trainer_placements "
        "(version_group_id, trainer_key, canonical_location_id, status, is_rematch, is_event, game_id) "
        "values (1, 'TRAINER_STADIUM', 54, 'placed', true, false, 17), "
        "       (1, 'TRAINER_ROUTE', 3, 'placed', null, null, null)")
    db_conn.commit()

    db_conn.execute(curation.apply_curated_placements_sql(1))
    db_conn.commit()

    row = db_conn.execute(
        "select canonical_location_id, is_rematch, is_event, game_id "
        "from trainer_pool where trainer_id = %s", (flagged,)).fetchone()
    assert row["canonical_location_id"] == 54
    assert row["is_rematch"] == "1"
    assert row["is_event"] == "0"
    assert row["game_id"] == 17
    row = db_conn.execute(
        "select canonical_location_id, is_rematch, is_event, game_id "
        "from trainer_pool where trainer_id = %s", (untouched,)).fetchone()
    assert row["canonical_location_id"] == 3
    assert row["is_rematch"] == "extractor"
    assert row["is_event"] == "extractor"
    assert row["game_id"] is None


def test_summary_separates_excluded_and_boss_linked(db_conn):
    """Unplaced trainers resolve out of the gap count when curated
    'excluded' or attached to a scripted boss event."""
    seed_world(db_conn)
    seed_unplaced(db_conn, key="TRAINER_REAL_GAP")
    seed_unplaced(db_conn, key="TRAINER_PLACEHOLDER")
    boss_id = seed_unplaced(db_conn, key="TRAINER_BOSS")
    db_conn.execute(
        "insert into curated_trainer_placements (version_group_id, trainer_key, status, note) "
        "values (1, 'TRAINER_PLACEHOLDER', 'excluded', 'unused ROM placeholder')")
    db_conn.execute(
        "insert into event_bosses (event_id, trainer_id, version_group_id) values (900, %s, 1)",
        (boss_id,))
    db_conn.commit()

    summary = [dict(r) for r in backend_module.get_placement_summary(db_conn)]

    row = next(r for r in summary if r["version_group_id"] == 1)
    assert row["unplaced"] == 3
    assert row["excluded"] == 1
    assert row["boss_linked"] == 1
    assert row["actionable_gaps"] == 1


def test_gen5_loader_embeds_curated_reapply():
    from etl.pipelines import gen5_trainers

    class Args:
        manifest = "blackwhite"
        preview_dir = None

    sql = gen5_trainers.build_load(Args()).build_sql(
        {"trainer_pool_stage": "/tmp/a.csv", "trainer_pokemon_stage": "/tmp/b.csv"},
        rollback=True,
    )
    assert "curated_trainer_placements" in sql
    assert "c.trainer_key = tp.encounter_name" in sql
