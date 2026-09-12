"""
WP2 tests: guest trainer-list context, Unova badges, and explicit
create_run game_id.

Run against the real throwaway Postgres like the rest of the suite.
"""
from pathlib import Path

import pytest

import backend as backend_module

UNOVA_MIGRATION_SQL = (
    Path(backend_module.__file__).resolve().parent
    / "migrations"
    / "20260825_unova_badges.sql"
).read_text(encoding="utf-8")


def seed_location_trainer(db_conn, *, encounter_name, canonical_location_id=100,
                          version_group_id=11, game_id=None):
    row = db_conn.execute(
        "insert into trainer_pool (encounter_name, trainer_name, canonical_location_id, version_group_id, game_id) "
        "values (%s, %s, %s, %s, %s) returning trainer_id",
        (encounter_name, encounter_name, canonical_location_id, version_group_id, game_id),
    ).fetchone()
    db_conn.commit()
    return row["trainer_id"]


# ---------------------------------------------------------------------------
# guest trainer-list context (no run row to derive game context from)
# ---------------------------------------------------------------------------

def test_trainer_list_with_explicit_version_group(db_conn):
    seed_location_trainer(db_conn, encounter_name="TRAINER_A", version_group_id=11)
    seed_location_trainer(db_conn, encounter_name="TRAINER_B", version_group_id=14)

    trainers = backend_module.get_trainers_by_location(
        db_conn, 100, version_group_id=11
    )

    assert [t["encounter_name"] for t in trainers] == ["TRAINER_A"]


def test_trainer_list_derives_version_group_from_game_id(db_conn):
    db_conn.execute(
        "insert into games (game_id, name, game_tag, generation, version_group_id) "
        "values (17, 'Black', 'B', 5, 11)"
    )
    db_conn.commit()
    seed_location_trainer(db_conn, encounter_name="TRAINER_A", version_group_id=11)

    trainers = backend_module.get_trainers_by_location(db_conn, 100, game_id=17)

    assert [t["encounter_name"] for t in trainers] == ["TRAINER_A"]


def test_trainer_list_without_context_still_raises(db_conn):
    with pytest.raises(ValueError):
        backend_module.get_trainers_by_location(db_conn, 100)


def seed_flagged_trainer(db_conn, *, encounter_name, is_rematch=None, is_event=None):
    db_conn.execute(
        "insert into trainer_pool (encounter_name, trainer_name, canonical_location_id, version_group_id, is_rematch, is_event) "
        "values (%s, %s, 100, 11, %s, %s)",
        (encounter_name, encounter_name, is_rematch, is_event),
    )
    db_conn.commit()


def test_rematches_and_events_are_opt_in(db_conn):
    seed_flagged_trainer(db_conn, encounter_name="TRAINER_REGULAR")
    seed_flagged_trainer(db_conn, encounter_name="TRAINER_REMATCH", is_rematch="true")
    seed_flagged_trainer(db_conn, encounter_name="TRAINER_EVENT", is_event="1")

    default = backend_module.get_trainers_by_location(db_conn, 100, version_group_id=11)
    assert [t["encounter_name"] for t in default] == ["TRAINER_REGULAR"]

    everything = backend_module.get_trainers_by_location(
        db_conn, 100, version_group_id=11, include_rematches=True, include_events=True
    )
    rows = {t["encounter_name"]: dict(t) for t in everything}
    assert set(rows) == {"TRAINER_REGULAR", "TRAINER_REMATCH", "TRAINER_EVENT"}
    assert rows["TRAINER_REMATCH"]["is_rematch"] == 1
    assert rows["TRAINER_EVENT"]["is_event"] == 1
    assert rows["TRAINER_REGULAR"]["is_rematch"] == 0

    only_rematches = backend_module.get_trainers_by_location(
        db_conn, 100, version_group_id=11, include_rematches=True
    )
    assert {t["encounter_name"] for t in only_rematches} == {"TRAINER_REGULAR", "TRAINER_REMATCH"}


# ---------------------------------------------------------------------------
# Unova badges
# ---------------------------------------------------------------------------

def _reset_badge_schema_cache():
    backend_module._schema_ready["badge"] = False


def test_fresh_schema_seeds_unova_badges_and_mappings(db_conn):
    # Simulate a fresh database: event rows exist before the badge schema
    # ensure runs, so the constant-driven seeding maps them.
    trainer_id = seed_location_trainer(db_conn, encounter_name="TRAINER_LENORA")
    db_conn.execute(
        "insert into event_bosses (trainer_id, version_group_id, encounter_title) values (%s, 11, 'Nacrene City Gym')",
        (trainer_id,),
    )
    db_conn.commit()

    _reset_badge_schema_cache()
    backend_module._ensure_badge_schema(db_conn)

    badges = db_conn.execute(
        "select badge_id, badge_name, region from badges where badge_id between 33 and 42 order by badge_id"
    ).fetchall()
    assert [b["badge_id"] for b in badges] == list(range(33, 43))
    assert all(b["region"] == "Unova" for b in badges)
    assert badges[0]["badge_name"] == "Trio Badge"
    assert badges[-1]["badge_name"] == "Wave Badge"

    mapped = db_conn.execute(
        "select badge_id from event_bosses where trainer_id = %s", (trainer_id,)
    ).fetchone()
    assert mapped["badge_id"] == 34  # Basic Badge


def test_unova_migration_maps_existing_databases(db_conn):
    # Simulate an existing database: badge_architecture_v1 already recorded,
    # so _ensure_badge_schema will never re-seed; the migration must do it.
    _reset_badge_schema_cache()
    backend_module._ensure_badge_schema(db_conn)

    bw_gym = seed_location_trainer(db_conn, encounter_name="TRAINER_SKYLA")
    b2w2_gym = seed_location_trainer(db_conn, encounter_name="TRAINER_MARLON", version_group_id=14)
    non_gym = seed_location_trainer(db_conn, encounter_name="TRAINER_N")
    db_conn.execute(
        "insert into event_bosses (trainer_id, version_group_id, encounter_title) values "
        "(%s, 11, 'Mistralton City Gym'), (%s, 14, 'Humilau City Gym'), (%s, 11, 'N''s Castle')",
        (bw_gym, b2w2_gym, non_gym),
    )
    db_conn.commit()

    db_conn.execute(UNOVA_MIGRATION_SQL)
    db_conn.commit()

    rows = {
        r["trainer_id"]: r["badge_id"]
        for r in db_conn.execute("select trainer_id, badge_id from event_bosses").fetchall()
    }
    assert rows[bw_gym] == 38   # Jet Badge
    assert rows[b2w2_gym] == 42  # Wave Badge
    assert rows[non_gym] is None

    # Guarded: a rerun after adding another unmapped gym row is a no-op.
    late_gym = seed_location_trainer(db_conn, encounter_name="TRAINER_ELESA")
    db_conn.execute(
        "insert into event_bosses (trainer_id, version_group_id, encounter_title) values (%s, 11, 'Nimbasa City Gym')",
        (late_gym,),
    )
    db_conn.commit()
    db_conn.execute(UNOVA_MIGRATION_SQL)
    db_conn.commit()

    late_row = db_conn.execute(
        "select badge_id from event_bosses where trainer_id = %s", (late_gym,)
    ).fetchone()
    assert late_row["badge_id"] is None


# ---------------------------------------------------------------------------
# create_run takes game_id explicitly
# ---------------------------------------------------------------------------

def test_create_run_uses_explicit_game_id(db_conn):
    db_conn.execute(
        "insert into games (game_id, name, game_tag, generation, version_group_id) "
        "values (17, 'Black', 'B', 5, 11)"
    )
    db_conn.commit()

    run_id = backend_module.create_run(db_conn, "WP2 Run", 17, user_id=1)

    row = db_conn.execute("select game_id from runs where run_id = %s", (run_id,)).fetchone()
    assert row["game_id"] == 17


def test_create_run_without_game_id_raises(db_conn):
    with pytest.raises(ValueError):
        backend_module.create_run(db_conn, "WP2 Run", None, user_id=1)
