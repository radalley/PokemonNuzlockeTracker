"""
Caught-Pokemon IVs: the encounter panel's six IV slots round-trip through
the pokebank save/read paths, come back nested as `ivs`, and out-of-range
or blank slots are dropped rather than failing the save.
"""
import backend as backend_module


def seed_world(db_conn):
    db_conn.execute(
        "insert into games (game_id, name, version_group_id, generation) values (17, 'Black', 11, 5)")
    db_conn.execute("insert into species (species_id, name) values (495, 'SNIVY')")
    run_id = db_conn.execute(
        "insert into runs (game_id, name) values (17, 'IV Run') returning run_id").fetchone()["run_id"]
    db_conn.execute(
        "insert into attempts (run_id, attempt_number, starter) values (%s, 1, 'Grass')", (run_id,))
    db_conn.commit()
    return run_id


def test_normalize_ivs_accepts_stat_or_column_keys_and_drops_bad_values():
    assert backend_module.normalize_ivs(None) == {
        'hp': None, 'atk': None, 'def': None, 'spa': None, 'spd': None, 'spe': None}
    # 0 is a real IV and is kept; 32 and -1 are outside the range.
    assert backend_module.normalize_ivs(
        {'hp': 31, 'iv_atk': '7', 'def': 0, 'spa': 32, 'spd': -1, 'spe': 'x'}
    ) == {'hp': 31, 'atk': 7, 'def': 0, 'spa': None, 'spd': None, 'spe': None}


def test_ivs_round_trip_through_pokebank(db_conn):
    run_id = seed_world(db_conn)

    pokemon_id = backend_module.upsert_encounter(
        db_conn, run_id, 1, 233, 495, 'Salad', 'Modest', 'Captured', None,
        gender='female', ability='Overgrow',
        ivs={'hp': 31, 'atk': 2, 'def': 20, 'spa': 31, 'spd': 19, 'spe': 31})

    rows = backend_module.get_pokebank_for_attempt(db_conn, run_id, 1)
    assert rows[0]["ivs"] == {'hp': 31, 'atk': 2, 'def': 20, 'spa': 31, 'spd': 19, 'spe': 31}
    assert 'iv_hp' not in rows[0]

    box = backend_module.get_pokebank_with_stats(db_conn, run_id, 1)
    assert box[0]["ivs"]["spe"] == 31
    assert box[0]["ability"] == "Overgrow"

    # A partial re-save keeps what was given and clears the rest (explicit
    # save semantics, same as ability).
    backend_module.upsert_encounter(
        db_conn, run_id, 1, 233, 495, 'Salad', 'Modest', 'Captured', None,
        pokemon_id=pokemon_id, gender='female', ability='Overgrow', ivs={'hp': 12})
    rows = backend_module.get_pokebank_for_attempt(db_conn, run_id, 1)
    assert rows[0]["ivs"] == {'hp': 12, 'atk': None, 'def': None, 'spa': None, 'spd': None, 'spe': None}


def test_save_route_accepts_ivs(client, db_conn, monkeypatch):
    run_id = seed_world(db_conn)
    import api as api_module
    monkeypatch.setattr(api_module, "get_db", lambda: db_conn)
    monkeypatch.setattr(api_module, "require_run_access", lambda conn, rid: ({'user_id': 1}, None))

    response = client.post("/api/pokebank/save", json={
        'run_id': run_id, 'attempt_number': 1, 'location_id': 233, 'species_id': 495,
        'status': 'Captured', 'ivs': {'hp': '31', 'atk': 0, 'spe': 31},
    })

    assert response.status_code == 200
    rows = backend_module.get_pokebank_for_attempt(db_conn, run_id, 1)
    assert rows[0]["ivs"] == {'hp': 31, 'atk': 0, 'def': None, 'spa': None, 'spd': None, 'spe': 31}
