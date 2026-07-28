"""
Priority 2 tests: core Nuzlocke gameplay state, against a real (throwaway,
local) Postgres instance rather than mocks -- these functions are almost
entirely raw SQL, so the only test worth trusting is one that runs the SQL.

Covers: party management (including the 6-pokemon cap), encounter
upsert/delete, and bonus locations (create/delete/rename).
"""
import backend as backend_module


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def seed_run_and_attempt(db_conn, *, game_id=1, run_id=None, attempt_number=1, version_group_id=10):
    db_conn.execute(
        "insert into games (game_id, name, game_tag, generation, version_group_id) "
        "values (%s, %s, %s, %s, %s)",
        (game_id, "Test Game", "TG", 3, version_group_id),
    )
    row = db_conn.execute(
        "insert into runs (game_id, name, user_id) values (%s, %s, %s) returning run_id",
        (game_id, "Test Run", 1),
    ).fetchone()
    run_id = row["run_id"]
    attempt_row = db_conn.execute(
        "insert into attempts (run_id, attempt_number, starter) values (%s, %s, %s) returning attempt_id",
        (run_id, attempt_number, "Fire"),
    ).fetchone()
    db_conn.commit()
    return run_id, attempt_row["attempt_id"]


def seed_pokemon(db_conn, run_id, attempt_id, *, species_id=1, location_id=1, status="Captured"):
    row = db_conn.execute(
        "insert into pokebank (run_id, attempt_id, species_id, canonical_location_id, status) "
        "values (%s, %s, %s, %s, %s) returning pokemon_id",
        (run_id, attempt_id, species_id, location_id, status),
    ).fetchone()
    db_conn.commit()
    return row["pokemon_id"]


# ---------------------------------------------------------------------------
# party management -- the 6-pokemon cap is a core Nuzlocke rule
# ---------------------------------------------------------------------------

def test_add_to_party_assigns_first_open_slot(db_conn):
    run_id, attempt_id = seed_run_and_attempt(db_conn)
    pokemon_id = seed_pokemon(db_conn, run_id, attempt_id)

    slot = backend_module.add_to_party_for_attempt(db_conn, run_id, 1, pokemon_id)

    assert slot == 1


def test_add_to_party_is_idempotent_for_same_pokemon(db_conn):
    run_id, attempt_id = seed_run_and_attempt(db_conn)
    pokemon_id = seed_pokemon(db_conn, run_id, attempt_id)

    first_slot = backend_module.add_to_party_for_attempt(db_conn, run_id, 1, pokemon_id)
    second_slot = backend_module.add_to_party_for_attempt(db_conn, run_id, 1, pokemon_id)

    assert first_slot == second_slot == 1
    rows = db_conn.execute(
        "select count(*) as n from party where attempt_id = %s", (attempt_id,)
    ).fetchone()
    assert rows["n"] == 1, "adding the same pokemon twice should not create a duplicate party row"


def test_party_caps_at_six_pokemon(db_conn):
    run_id, attempt_id = seed_run_and_attempt(db_conn)
    pokemon_ids = [seed_pokemon(db_conn, run_id, attempt_id, species_id=i) for i in range(1, 8)]

    slots = [backend_module.add_to_party_for_attempt(db_conn, run_id, 1, pid) for pid in pokemon_ids[:6]]
    assert slots == [1, 2, 3, 4, 5, 6]

    seventh_slot = backend_module.add_to_party_for_attempt(db_conn, run_id, 1, pokemon_ids[6])
    assert seventh_slot is None, "a 7th pokemon must not fit in a 6-slot party"


def test_remove_from_party_frees_the_slot_for_reuse(db_conn):
    run_id, attempt_id = seed_run_and_attempt(db_conn)
    pokemon_ids = [seed_pokemon(db_conn, run_id, attempt_id, species_id=i) for i in range(1, 8)]
    for pid in pokemon_ids[:6]:
        backend_module.add_to_party_for_attempt(db_conn, run_id, 1, pid)

    backend_module.remove_from_party_for_attempt(db_conn, run_id, 1, pokemon_ids[2])  # frees slot 3
    new_slot = backend_module.add_to_party_for_attempt(db_conn, run_id, 1, pokemon_ids[6])

    assert new_slot == 3


def test_add_to_party_unknown_attempt_returns_none(db_conn):
    run_id, attempt_id = seed_run_and_attempt(db_conn)
    pokemon_id = seed_pokemon(db_conn, run_id, attempt_id)

    slot = backend_module.add_to_party_for_attempt(db_conn, run_id, attempt_number=999, pokemon_id=pokemon_id)

    assert slot is None


# ---------------------------------------------------------------------------
# encounters -- first-encounter-only / fainted-is-dead bookkeeping
# ---------------------------------------------------------------------------

def test_upsert_encounter_creates_new_pokebank_row(db_conn):
    run_id, attempt_id = seed_run_and_attempt(db_conn)

    pokemon_id = backend_module.upsert_encounter(
        db_conn, run_id, 1, location_id=5, species_id=25,
        nickname="Sparky", nature="Jolly", status="Captured", shiny=False,
    )

    row = db_conn.execute(
        "select * from pokebank where pokemon_id = %s", (pokemon_id,)
    ).fetchone()
    assert row["species_id"] == 25
    assert row["status"] == "Captured"
    assert row["nickname"] == "Sparky"


def test_upsert_encounter_with_existing_id_updates_in_place(db_conn):
    run_id, attempt_id = seed_run_and_attempt(db_conn)
    pokemon_id = seed_pokemon(db_conn, run_id, attempt_id, species_id=1, status="Captured")

    returned_id = backend_module.upsert_encounter(
        db_conn, run_id, 1, location_id=5, species_id=1,
        nickname=None, nature=None, status="Dead", shiny=False,
        pokemon_id=pokemon_id,
    )

    assert returned_id == pokemon_id
    row = db_conn.execute(
        "select status from pokebank where pokemon_id = %s", (pokemon_id,)
    ).fetchone()
    assert row["status"] == "Dead"

    total = db_conn.execute("select count(*) as n from pokebank").fetchone()
    assert total["n"] == 1, "updating a fainted pokemon's status must not create a second row"


def test_delete_encounter_removes_the_row(db_conn):
    run_id, attempt_id = seed_run_and_attempt(db_conn)
    pokemon_id = seed_pokemon(db_conn, run_id, attempt_id)

    backend_module.delete_encounter(db_conn, pokemon_id)

    row = db_conn.execute(
        "select * from pokebank where pokemon_id = %s", (pokemon_id,)
    ).fetchone()
    assert row is None


# ---------------------------------------------------------------------------
# bonus locations -- the most complex single feature in backend.py
# ---------------------------------------------------------------------------

def seed_canon_and_event_location(db_conn, *, canonical_location_id=1, version_group_id=10,
                                   name="Route 1", sort_order=5, event_type="Location"):
    db_conn.execute(
        "insert into canon_locations (canonical_location_id, canonical_location_name) values (%s, %s)",
        (canonical_location_id, name),
    )
    db_conn.execute(
        "insert into event_locations (canonical_location_id, version_group_id, sort_order, "
        "secondary_sort_order, event_type) values (%s, %s, %s, %s, %s)",
        (canonical_location_id, version_group_id, sort_order, 0, event_type),
    )
    db_conn.commit()


def test_create_bonus_location_round_trip(db_conn):
    run_id, attempt_id = seed_run_and_attempt(db_conn, version_group_id=10)
    seed_canon_and_event_location(db_conn, canonical_location_id=7, version_group_id=10)

    result = backend_module.create_bonus_location(db_conn, run_id, 1, canonical_location_id=7)

    assert result["success"] is True
    assert result["display_name"] == "Route 1 - Bonus"
    assert result["secondary_sort_order"] == 1

    rename_result = backend_module.rename_bonus_location(
        db_conn, run_id, 1, canonical_location_id=7,
        secondary_sort_order=1, canonical_name="My Custom Name",
    )
    assert rename_result["success"] is True

    delete_result = backend_module.delete_bonus_location(
        db_conn, run_id, 1, canonical_location_id=7, secondary_sort_order=1
    )
    assert delete_result["success"] is True

    remaining = db_conn.execute(
        "select count(*) as n from bonus_locations where run_id = %s", (run_id,)
    ).fetchone()
    assert remaining["n"] == 0


def test_create_bonus_location_unknown_attempt_fails_cleanly(db_conn):
    run_id, attempt_id = seed_run_and_attempt(db_conn)
    result = backend_module.create_bonus_location(db_conn, run_id, attempt_number=999, canonical_location_id=1)
    assert result == {"success": False, "error": "Attempt not found"}


def test_create_bonus_location_unknown_base_location_fails_cleanly(db_conn):
    run_id, attempt_id = seed_run_and_attempt(db_conn, version_group_id=10)
    # No canon_locations/event_locations row seeded for this id.
    result = backend_module.create_bonus_location(db_conn, run_id, 1, canonical_location_id=999)
    assert result == {"success": False, "error": "Base location not found"}


def test_delete_bonus_location_also_clears_party_and_pokebank(db_conn):
    run_id, attempt_id = seed_run_and_attempt(db_conn, version_group_id=10)
    seed_canon_and_event_location(db_conn, canonical_location_id=7, version_group_id=10)
    bonus = backend_module.create_bonus_location(db_conn, run_id, 1, canonical_location_id=7)

    pokemon_id = backend_module.upsert_encounter(
        db_conn, run_id, 1, location_id=7, species_id=1,
        nickname=None, nature=None, status="Captured", shiny=False,
        bonus_location=bonus["secondary_sort_order"],
    )
    backend_module.add_to_party_for_attempt(db_conn, run_id, 1, pokemon_id)

    result = backend_module.delete_bonus_location(
        db_conn, run_id, 1, canonical_location_id=7,
        secondary_sort_order=bonus["secondary_sort_order"],
    )

    assert result["success"] is True
    assert db_conn.execute("select * from pokebank where pokemon_id = %s", (pokemon_id,)).fetchone() is None
    assert db_conn.execute("select * from party where pokemon_id = %s", (pokemon_id,)).fetchone() is None
