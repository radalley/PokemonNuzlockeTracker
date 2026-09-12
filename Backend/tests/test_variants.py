"""
WP7 tests: the variant model.

A ROM hack is its own games row + its own version group (reserved range
1000+), linked to its base via base_game_id and seeded by cloning. These
cover the games metadata, the clone pipeline end-to-end on real Postgres,
and the is_level_cap flag on script rows.
"""
import pytest

import backend as backend_module
from etl.pipelines import clone_version_group


# ---------------------------------------------------------------------------
# fixtures: a miniature vanilla game
# ---------------------------------------------------------------------------

def seed_base_game(db_conn):
    # Badge rows must exist before a boss row can reference badge 33: the
    # badge-schema ensure adds the foreign key.
    backend_module._schema_ready["badge"] = False
    backend_module._ensure_badge_schema(db_conn)
    db_conn.execute(
        "insert into games (game_id, name, game_tag, generation, version_group_id, valid_game) "
        "values (17, 'Black', 'B', 5, 11, 'valid')"
    )
    db_conn.execute(
        "insert into canon_locations (canonical_location_id, canonical_location_name) "
        "values (1, 'Route 1'), (7, 'Striaton City')"
    )
    db_conn.execute(
        "insert into event_locations (canonical_location_id, version_group_id, sort_order, secondary_sort_order, event_type) "
        "values (1, 11, 1, 0, 'Location'), (7, 11, 2, 0, 'Location')"
    )
    db_conn.execute(
        "insert into location_areas (canonical_location_id, version_group_id, area_name, area_kind, sort_order) "
        "values (7, 11, 'Striaton Gym', 'gym', 1)"
    )
    area_id = db_conn.execute("select area_id from location_areas").fetchone()["area_id"]
    trainer = db_conn.execute(
        "insert into trainer_pool (encounter_name, trainer_name, canonical_location_id, area_id, version_group_id, load_build) "
        "values ('TRAINER_CILAN', 'CILAN', 7, %s, 11, 6) returning trainer_id",
        (area_id,),
    ).fetchone()
    db_conn.execute(
        "insert into trainer_pokemon (encounter_name, species_name, lvl, version_group_id, load_build, slot, trainer_id) "
        "values ('TRAINER_CILAN', 'pansage', 14, 11, 6, 1, %s)",
        (trainer["trainer_id"],),
    )
    db_conn.execute(
        "insert into event_bosses (trainer_id, version_group_id, encounter_title, sort_order, event_type, badge_id, is_level_cap, battle_type) "
        "values (%s, 11, 'Striaton City Gym', '2.1', '', 33, true, 'rotation')",
        (trainer["trainer_id"],),
    )
    db_conn.execute(
        "insert into encounter_pool (game_id, location_id, canonical_location_id, species_id, min_level, max_level, method, enounter_rate) "
        "values ('17', 1, 1, 504, 2, 4, 'walk', 40)"
    )
    db_conn.commit()
    return trainer["trainer_id"]


def run_clone(db_conn, full=True):
    sql = clone_version_group.build_sql(
        11, 1001, [(1001, 17, "Test Hack Black")], full=full,
        valid_game="hidden", rollback=False,
    )
    db_conn.execute(sql)
    db_conn.commit()


# ---------------------------------------------------------------------------
# clone pipeline
# ---------------------------------------------------------------------------

def test_full_clone_produces_playable_copy(db_conn):
    base_trainer = seed_base_game(db_conn)
    run_clone(db_conn)

    game = db_conn.execute("select * from games where game_id = 1001").fetchone()
    assert game["name"] == "Test Hack Black"
    assert game["version_group_id"] == 1001
    assert game["base_game_id"] == 17
    assert game["is_rom_hack"] is True
    assert game["valid_game"] == "hidden"
    assert game["generation"] == 5  # inherited from the base

    assert db_conn.execute(
        "select count(*) as n from event_locations where version_group_id = 1001"
    ).fetchone()["n"] == 2

    clone_trainer = db_conn.execute(
        "select * from trainer_pool where version_group_id = 1001"
    ).fetchone()
    assert clone_trainer["encounter_name"] == "TRAINER_CILAN"
    assert clone_trainer["trainer_id"] != base_trainer
    # The cloned trainer points at the cloned area, not the base's.
    area = db_conn.execute(
        "select version_group_id from location_areas where area_id = %s",
        (clone_trainer["area_id"],),
    ).fetchone()
    assert area["version_group_id"] == 1001

    party = db_conn.execute(
        "select trainer_id, species_name from trainer_pokemon where version_group_id = 1001"
    ).fetchone()
    assert party["trainer_id"] == clone_trainer["trainer_id"]

    boss = db_conn.execute(
        "select * from event_bosses where version_group_id = 1001"
    ).fetchone()
    assert boss["trainer_id"] == clone_trainer["trainer_id"]
    assert boss["badge_id"] == 33
    assert boss["is_level_cap"] is True
    assert boss["battle_type"] == "rotation"

    pool = db_conn.execute(
        "select species_id from encounter_pool where nullif(game_id::text,'')::integer = 1001"
    ).fetchall()
    assert [p["species_id"] for p in pool] == [504]


def test_clone_drops_unmapped_game_exclusives(db_conn):
    """Cloning only Black from the Black/White pair must DROP White-exclusive
    rows, not turn them into shared rows -- turning them shared put White's
    Opelucid Gym into a Black clone's script."""
    seed_base_game(db_conn)
    white_trainer = db_conn.execute(
        "insert into trainer_pool (encounter_name, trainer_name, canonical_location_id, version_group_id, load_build) "
        "values ('TRAINER_WHITE_ONLY', 'IRIS', 7, 11, 6) returning trainer_id"
    ).fetchone()
    db_conn.execute(
        "insert into event_bosses (trainer_id, version_group_id, encounter_title, sort_order, game_id) "
        "values (%s, 11, 'Opelucid City Gym (White)', '3.1', 18)",
        (white_trainer["trainer_id"],),
    )
    db_conn.commit()

    run_clone(db_conn)

    clone_bosses = db_conn.execute(
        "select encounter_title, game_id from event_bosses where version_group_id = 1001"
    ).fetchall()
    assert [b["encounter_title"] for b in clone_bosses] == ["Striaton City Gym"]


def test_clone_refuses_reserved_range_violation(db_conn):
    seed_base_game(db_conn)
    sql = clone_version_group.build_sql(11, 12, [(1001, 17, "Bad")], rollback=False)
    with pytest.raises(Exception, match="reserved range"):
        db_conn.execute(sql)
    db_conn.rollback()


def test_clone_refuses_occupied_version_group(db_conn):
    seed_base_game(db_conn)
    run_clone(db_conn)
    with pytest.raises(Exception, match="already in use"):
        db_conn.execute(clone_version_group.build_sql(
            11, 1001, [(1001, 17, "Again")], rollback=False,
        ))
    db_conn.rollback()


# ---------------------------------------------------------------------------
# read paths
# ---------------------------------------------------------------------------

def test_get_games_exposes_variant_metadata(db_conn):
    seed_base_game(db_conn)
    run_clone(db_conn)
    db_conn.execute("update games set valid_game = 'valid' where game_id = 1001")
    db_conn.commit()

    games = {g["game_id"]: dict(g) for g in backend_module.get_games(db_conn)}
    assert games[17]["is_rom_hack"] is False
    assert games[17]["base_game_name"] is None
    assert games[1001]["is_rom_hack"] is True
    assert games[1001]["base_game_id"] == 17
    assert games[1001]["base_game_name"] == "Black"


def test_hidden_games_stay_out_of_the_list(db_conn):
    seed_base_game(db_conn)
    run_clone(db_conn)

    games = [g["game_id"] for g in backend_module.get_games(db_conn)]
    assert 17 in games
    assert 1001 not in games


def test_script_rows_carry_level_cap_flag_and_isolate_version_groups(db_conn):
    seed_base_game(db_conn)
    run_clone(db_conn)

    base_script = [dict(r) for r in backend_module.get_script(db_conn, "Fire", version_group_id=11, game_id=17)]
    clone_script = [dict(r) for r in backend_module.get_script(db_conn, "Fire", version_group_id=1001, game_id=1001)]

    assert [r["display_name"] for r in base_script] == [r["display_name"] for r in clone_script]

    base_boss = next(r for r in base_script if r["boss_event_id"] is not None)
    clone_boss = next(r for r in clone_script if r["boss_event_id"] is not None)
    assert base_boss["is_level_cap"] is True
    assert clone_boss["is_level_cap"] is True
    assert clone_boss["battle_type"] == "rotation"
    assert clone_boss["badge_id"] == 33
    # Isolation: the clone's boss row resolves to the clone's trainer.
    assert clone_boss["event_id"] != base_boss["event_id"]
