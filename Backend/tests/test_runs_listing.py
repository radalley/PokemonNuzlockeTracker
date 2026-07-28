"""
Tests for get_runs() after batching it (Fix 2 in docs/fix-proposal-hot-path.md).

The critical correctness risk with batching is Lockley's core premise: a
single user's runs can span *different games* (different generations), so
species stat/type/ability patching must use each attempt's own game
generation -- not one shared value across the whole batch. That's the
scenario test_get_runs_patches_stats_per_run_generation exists to catch.
"""
import backend as backend_module


def seed_game(db_conn, game_id, generation, name="Game"):
    db_conn.execute(
        "insert into games (game_id, name, game_tag, generation, version_group_id) "
        "values (%s, %s, %s, %s, %s)",
        (game_id, name, name[:2].upper(), generation, game_id),
    )
    db_conn.commit()


def seed_run_with_party(db_conn, *, game_id, user_id=1, species_id=25, run_name="Run"):
    row = db_conn.execute(
        "insert into runs (game_id, name, user_id) values (%s, %s, %s) returning run_id",
        (game_id, run_name, user_id),
    ).fetchone()
    run_id = row["run_id"]
    attempt_row = db_conn.execute(
        "insert into attempts (run_id, attempt_number, starter) values (%s, 1, 'Fire') returning attempt_id",
        (run_id,),
    ).fetchone()
    attempt_id = attempt_row["attempt_id"]
    pokemon_row = db_conn.execute(
        "insert into pokebank (run_id, attempt_id, species_id, canonical_location_id, status) "
        "values (%s, %s, %s, 1, 'Captured') returning pokemon_id",
        (run_id, attempt_id, species_id),
    ).fetchone()
    pokemon_id = pokemon_row["pokemon_id"]
    db_conn.execute(
        "insert into party (attempt_id, party_slot, pokemon_id) values (%s, 1, %s)",
        (attempt_id, pokemon_id),
    )
    db_conn.commit()
    return run_id, attempt_id, pokemon_id


def seed_species(db_conn, species_id=25, name="Pikachu"):
    db_conn.execute(
        "insert into species (species_id, name) values (%s, %s) on conflict do nothing",
        (species_id, name),
    )
    db_conn.commit()


def seed_generational_stats(db_conn, species_id, generation, bst):
    """Seed one generation-specific row of stats/types/abilities for a species."""
    db_conn.execute(
        "insert into species_stats (species_id, generation, bst, hp, atk, def, spa, spd, spe) "
        "values (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
        (species_id, generation, bst, bst, bst, bst, bst, bst, bst),
    )
    db_conn.execute(
        "insert into species_types (species_id, generation, type1, type2) values (%s, %s, %s, %s)",
        (species_id, generation, f"type-gen{generation}", None),
    )
    db_conn.execute(
        "insert into species_abilities (species_id, generation, ability1, ability2, ability3) "
        "values (%s, %s, %s, %s, %s)",
        (species_id, generation, f"ability-gen{generation}", None, None),
    )
    db_conn.commit()


def test_get_runs_attaches_party_stats_and_badges_for_latest_attempt(db_conn):
    seed_game(db_conn, game_id=1, generation=3, name="Emerald")
    seed_species(db_conn, species_id=25, name="Pikachu")
    seed_generational_stats(db_conn, species_id=25, generation=3, bst=320)
    run_id, attempt_id, pokemon_id = seed_run_with_party(db_conn, game_id=1)

    runs = backend_module.get_runs(db_conn, user_id=1)

    assert len(runs) == 1
    run = runs[0]
    assert run["run_id"] == run_id
    assert len(run["latest_party"]) == 1
    assert run["latest_party"][0]["pokemon_id"] == pokemon_id
    assert run["latest_party"][0]["species_name"] == "Pikachu"
    assert run["latest_party"][0]["bst"] == 320
    assert run["latest_attempt_stats"]["pokemon_caught"] == 1
    assert run["latest_attempt_stats"]["run_id"] == run_id
    assert run["latest_attempt_badges"] == []


def test_get_runs_run_with_no_attempts_has_empty_defaults(db_conn):
    seed_game(db_conn, game_id=1, generation=3, name="Emerald")
    db_conn.execute(
        "insert into runs (game_id, name, user_id) values (%s, %s, %s)",
        (1, "Empty Run", 1),
    )
    db_conn.commit()

    runs = backend_module.get_runs(db_conn, user_id=1)

    assert len(runs) == 1
    assert runs[0]["latest_party"] == []
    assert runs[0]["latest_attempt_stats"] is None
    assert runs[0]["latest_attempt_badges"] == []


def test_get_runs_patches_stats_per_run_generation(db_conn):
    """
    The scenario that makes naive batching wrong: the same species has
    different stats in different generations, and a single user has one run
    on an old-gen game and one run on a new-gen game. Batching must patch
    each run's party using *that run's own* generation, not bleed the wrong
    generation's stats across runs.
    """
    seed_species(db_conn, species_id=25, name="Pikachu")
    seed_generational_stats(db_conn, species_id=25, generation=1, bst=200)
    seed_generational_stats(db_conn, species_id=25, generation=6, bst=400)

    seed_game(db_conn, game_id=1, generation=1, name="Red")
    seed_game(db_conn, game_id=2, generation=6, name="X")

    gen1_run_id, _, _ = seed_run_with_party(db_conn, game_id=1, species_id=25, run_name="Gen1 Run")
    gen6_run_id, _, _ = seed_run_with_party(db_conn, game_id=2, species_id=25, run_name="Gen6 Run")

    runs = backend_module.get_runs(db_conn, user_id=1)
    runs_by_id = {r["run_id"]: r for r in runs}

    gen1_party = runs_by_id[gen1_run_id]["latest_party"]
    gen6_party = runs_by_id[gen6_run_id]["latest_party"]

    assert gen1_party[0]["bst"] == 200, "gen1 run must use gen1 stats, not bleed gen6's"
    assert gen1_party[0]["type1"] == "type-gen1"
    assert gen6_party[0]["bst"] == 400, "gen6 run must use gen6 stats, not bleed gen1's"
    assert gen6_party[0]["type1"] == "type-gen6"


def test_get_runs_query_count_does_not_scale_with_run_count(db_conn):
    """
    Regression guard for the N+1 fix: query count for get_runs() should be
    roughly constant, not proportional to the number of runs returned.
    """
    seed_game(db_conn, game_id=1, generation=3, name="Emerald")
    seed_species(db_conn, species_id=25, name="Pikachu")
    seed_generational_stats(db_conn, species_id=25, generation=3, bst=320)
    for i in range(8):
        seed_run_with_party(db_conn, game_id=1, species_id=25, run_name=f"Run {i}")

    # Warm up the schema-check memoization (Fix 1) before measuring. The very
    # first call to _ensure_badge_schema against a brand-new, never-migrated
    # database does real one-time work (creating tables/indexes and running a
    # guarded data migration for badge_id backfill) -- that's legitimate,
    # unavoidable cold-start cost, not part of the N+1 problem being fixed
    # here, and it would already be long done on the real production DB.
    # This test measures steady-state behavior, which is what Fix 1 and
    # Fix 2 together are actually meant to fix.
    backend_module._ensure_badge_schema(db_conn)
    backend_module._ensure_auth_schema(db_conn)

    query_count = {"n": 0}
    real_execute = db_conn.execute

    def counting_execute(sql, params=()):
        query_count["n"] += 1
        return real_execute(sql, params)

    db_conn.execute = counting_execute
    try:
        runs = backend_module.get_runs(db_conn, user_id=1)
    finally:
        db_conn.execute = real_execute

    assert len(runs) == 8
    # Before the fix this scaled at roughly 4N+ queries, each one carrying
    # its own ~10-query schema-check burst on top. After batching, at
    # steady state, it should be a small constant regardless of run count.
    assert query_count["n"] < 10, f"expected roughly constant query count, got {query_count['n']} for 8 runs"
