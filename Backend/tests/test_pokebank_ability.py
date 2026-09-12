"""
Caught-Pokemon abilities: the picker's options resolve version-group-aware
(a hack's override layer wins), and the chosen ability round-trips through
the pokebank save/read paths.
"""
import backend as backend_module


def seed_world(db_conn):
    db_conn.execute(
        "insert into games (game_id, name, version_group_id, generation) "
        "values (17, 'Black', 11, 5), (1001, 'Blaze Black', 1001, 5)")
    db_conn.execute("update games set base_game_id = 17 where game_id = 1001")
    db_conn.execute("insert into species (species_id, name) values (495, 'SNIVY')")
    # Vanilla generation row + a Blaze Black override row.
    db_conn.execute(
        "insert into species_abilities (species_id, generation, ability1, ability2, ability3) "
        "values (495, 5, 'Overgrow', null, 'Contrary')")
    db_conn.execute(
        "insert into species_abilities (species_id, generation, ability1, ability2, ability3, version_group_id) "
        "values (495, 5, 'Contrary', 'Overgrow', null, 1001)")
    db_conn.commit()


def test_species_abilities_resolve_per_game(db_conn):
    seed_world(db_conn)

    vanilla = backend_module.get_species_abilities(db_conn, 495, game_id=17)
    hack = backend_module.get_species_abilities(db_conn, 495, game_id=1001)

    assert vanilla == [{'name': 'Overgrow', 'hidden': False}, {'name': 'Contrary', 'hidden': True}]
    # The override row wins for the hack; its Contrary is a regular slot.
    assert hack == [{'name': 'Contrary', 'hidden': False}, {'name': 'Overgrow', 'hidden': False}]


def test_ability_round_trips_through_pokebank(db_conn):
    seed_world(db_conn)
    run_id = db_conn.execute(
        "insert into runs (game_id, name) values (1001, 'BB Run') returning run_id").fetchone()["run_id"]
    db_conn.execute(
        "insert into attempts (run_id, attempt_number, starter) values (%s, 1, 'Fire')", (run_id,))
    db_conn.commit()

    pokemon_id = backend_module.upsert_encounter(
        db_conn, run_id, 1, 233, 495, None, 'Adamant', 'Captured', None,
        gender='male', ability='Contrary')

    rows = backend_module.get_pokebank_for_attempt(db_conn, run_id, 1)
    assert rows[0]["ability"] == "Contrary"

    # Re-save without an ability clears it (explicit save semantics).
    backend_module.upsert_encounter(
        db_conn, run_id, 1, 233, 495, None, 'Adamant', 'Captured', None,
        pokemon_id=pokemon_id, gender='male', ability=None)
    rows = backend_module.get_pokebank_for_attempt(db_conn, run_id, 1)
    assert rows[0]["ability"] is None
