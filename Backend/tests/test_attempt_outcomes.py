"""
Attempt outcomes: declaring a run dead, the post-mortem summary,
and reopening an accidental declaration.
"""
import pytest

import backend as backend_module


def seed_run(db_conn):
    db_conn.execute(
        "insert into games (game_id, name, version_group_id, generation) "
        "values (17, 'Black', 11, 5)"
    )
    run_id = db_conn.execute(
        "insert into runs (game_id, name) values (17, 'Test Run') returning run_id"
    ).fetchone()["run_id"]
    attempt_id = db_conn.execute(
        "insert into attempts (run_id, attempt_number, starter) "
        "values (%s, 1, 'Fire') returning attempt_id",
        (run_id,),
    ).fetchone()["attempt_id"]
    db_conn.commit()
    return run_id, attempt_id


def seed_killer(db_conn):
    db_conn.execute(
        "insert into canon_locations (canonical_location_id, canonical_location_name) "
        "values (233, 'Striaton City')"
    )
    trainer_id = db_conn.execute(
        "insert into trainer_pool (encounter_name, trainer_name, trainer_class, version_group_id, canonical_location_id) "
        "values ('TRAINER_LEADER_CHILI', 'CHILI', 'TRAINER_CLASS_LEADER', 11, 233) returning trainer_id"
    ).fetchone()["trainer_id"]
    db_conn.commit()
    return trainer_id


def test_end_attempt_records_killer_and_note(db_conn):
    run_id, _ = seed_run(db_conn)
    killer_id = seed_killer(db_conn)

    result = backend_module.end_attempt(
        db_conn, run_id, 1, trainer_id=killer_id, note="swept by Pansear")
    assert result["success"] is True

    row = db_conn.execute(
        "select outcome, ended_at, ended_by_trainer_id, death_note "
        "from attempts where run_id = %s and attempt_number = 1", (run_id,)).fetchone()
    assert row["outcome"] == "dead"
    assert row["ended_at"] is not None
    assert row["ended_by_trainer_id"] == killer_id
    assert row["death_note"] == "swept by Pansear"


def test_end_attempt_rejects_double_end_and_bad_trainer(db_conn):
    run_id, _ = seed_run(db_conn)
    backend_module.end_attempt(db_conn, run_id, 1)
    with pytest.raises(ValueError):
        backend_module.end_attempt(db_conn, run_id, 1)
    with pytest.raises(ValueError):
        backend_module.end_attempt(db_conn, run_id, 99)

    run_id2 = db_conn.execute(
        "insert into runs (game_id, name) values (17, 'Second') returning run_id").fetchone()["run_id"]
    db_conn.execute(
        "insert into attempts (run_id, attempt_number, starter) values (%s, 1, 'Fire')", (run_id2,))
    db_conn.commit()
    with pytest.raises(ValueError):
        backend_module.end_attempt(db_conn, run_id2, 1, trainer_id=999999)


def test_end_attempt_rejects_killer_from_another_game(db_conn):
    run_id, _ = seed_run(db_conn)
    foreign = db_conn.execute(
        "insert into trainer_pool (encounter_name, trainer_name, version_group_id) "
        "values ('TRAINER_KANTO_GUY', 'BROCK', 1) returning trainer_id").fetchone()["trainer_id"]
    db_conn.commit()

    with pytest.raises(ValueError):
        backend_module.end_attempt(db_conn, run_id, 1, trainer_id=foreign)


def test_reopen_missing_attempt_raises(db_conn):
    run_id, _ = seed_run(db_conn)
    with pytest.raises(ValueError):
        backend_module.reopen_attempt(db_conn, run_id, 99)


def test_reopen_attempt(db_conn):
    run_id, _ = seed_run(db_conn)
    backend_module.end_attempt(db_conn, run_id, 1, note="oops")

    assert backend_module.reopen_attempt(db_conn, run_id, 1) is True
    row = db_conn.execute(
        "select outcome, ended_at, death_note from attempts where run_id = %s", (run_id,)).fetchone()
    assert row["outcome"] is None
    assert row["ended_at"] is None
    assert row["death_note"] is None
    # Reopening a live attempt is a no-op.
    assert backend_module.reopen_attempt(db_conn, run_id, 1) is False


def test_attempt_summary_shape(db_conn):
    run_id, attempt_id = seed_run(db_conn)
    killer_id = seed_killer(db_conn)
    db_conn.execute("insert into species (species_id, name) values (495, 'SNIVY'), (504, 'PATRAT')")
    db_conn.execute(
        "insert into pokebank (run_id, attempt_id, species_id, canonical_location_id, nickname, status, level_met) "
        "values (%s, %s, 495, 233, 'Smug', 'Captured', 5), "
        "       (%s, %s, 504, 233, null, 'Dead', 3)",
        (run_id, attempt_id, run_id, attempt_id))
    db_conn.execute(
        "insert into trainers_defeated (run_id, attempt_id, trainer_id) values (%s, %s, %s)",
        (run_id, attempt_id, killer_id))
    db_conn.commit()
    backend_module.end_attempt(db_conn, run_id, 1, trainer_id=killer_id)

    summary = backend_module.get_attempt_summary(db_conn, run_id, 1)

    assert summary["attempt"]["outcome"] == "dead"
    assert summary["killer"]["trainer_name"] == "CHILI"
    assert summary["killer"]["location_name"] == "Striaton City"
    assert [d["species_name"] for d in summary["deaths"]] == ["PATRAT"]
    assert [s["nickname"] for s in summary["survivors"]] == ["Smug"]
    assert summary["counts"]["captured"] == 1
    assert summary["counts"]["dead"] == 1
    assert summary["counts"]["trainers_defeated"] == 1


def test_attempts_listing_includes_outcome(db_conn):
    run_id, _ = seed_run(db_conn)
    db_conn.execute(
        "insert into attempts (run_id, attempt_number, starter) values (%s, 2, 'Fire')", (run_id,))
    db_conn.commit()
    backend_module.end_attempt(db_conn, run_id, 1)

    rows = [dict(r) for r in backend_module.get_attempts_for_run(db_conn, run_id)]
    assert rows[0]["attempt_number"] == 1 and rows[0]["outcome"] == "dead"
    assert rows[1]["attempt_number"] == 2 and rows[1]["outcome"] is None
