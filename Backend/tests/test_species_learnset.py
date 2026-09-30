"""
Box summary learnsets: the full level-up learnset for a species resolves
against the run's game (a hack's own rows win, vanilla falls back to the
base game's chronology) and each move's stats come from the same
past-values machinery trainer parties use.
"""
import backend as backend_module


def seed_world(db_conn):
    db_conn.execute(
        "insert into games (game_id, name, version_group_id, generation) "
        "values (17, 'Black', 11, 5), (1001, 'Blaze Black', 1001, 5)")
    db_conn.execute("update games set base_game_id = 17 where game_id = 1001")
    db_conn.execute("insert into species (species_id, name) values (495, 'SNIVY')")
    # Tackle: one default row. Leaf Storm: modern default (130) plus a
    # past-values row keyed at vg 15, so games before B2W2 see 140.
    db_conn.execute(
        "insert into moves (move_id, move_name, type, damage_class, power, accuracy, version_group_id) values "
        "(33, 'tackle', 'normal', 'physical', 40, 100, null), "
        "(22, 'vine-whip', 'grass', 'physical', 45, 100, null), "
        "(437, 'leaf-storm', 'grass', 'special', 130, 90, null), "
        "(437, 'leaf-storm', 'grass', 'special', 140, 90, 15)")
    # Vanilla BW learnset (with a duplicate row) and a Blaze Black override.
    db_conn.execute(
        "insert into movesets (species_id, move_id, learn_method, learn_level, version_group_id) values "
        "(495, 33, 'level-up', 1, 11), (495, 33, 'level-up', 1, 11), "
        "(495, 22, 'level-up', 7, 11), (495, 437, 'level-up', 40, 11), "
        "(495, 22, 'egg', 0, 11), "
        "(495, 33, 'level-up', 1, 1001), (495, 437, 'level-up', 5, 1001)")
    db_conn.commit()


def test_learnset_resolves_for_vanilla_game(db_conn):
    seed_world(db_conn)

    result = backend_module.get_species_learnset(db_conn, 495, game_id=17)

    assert result["version_group_id"] == 11
    assert [(m["learn_level"], m["move_name"]) for m in result["moves"]] == [
        (1, "Tackle"), (7, "Vine Whip"), (40, "Leaf Storm")]
    leaf_storm = result["moves"][-1]
    # Gen 5 value from the past-values row, not the modern default.
    assert leaf_storm["power"] == 140
    assert leaf_storm["type"] == "Grass"
    assert leaf_storm["damage_class"] == "Special"


def test_learnset_prefers_hack_rows(db_conn):
    seed_world(db_conn)

    result = backend_module.get_species_learnset(db_conn, 495, game_id=1001)

    assert result["version_group_id"] == 1001
    assert [(m["learn_level"], m["move_name"]) for m in result["moves"]] == [
        (1, "Tackle"), (5, "Leaf Storm")]
    # Move stats still resolve through the base game's chronology.
    assert result["moves"][-1]["power"] == 140


def test_learnset_without_game_context_uses_newest_vanilla(db_conn):
    seed_world(db_conn)

    result = backend_module.get_species_learnset(db_conn, 495)

    assert result["version_group_id"] == 11
    assert result["moves"][-1]["power"] == 130


def test_learnset_empty_for_unknown_species(db_conn):
    seed_world(db_conn)

    assert backend_module.get_species_learnset(db_conn, 999, game_id=17) == {
        "version_group_id": None, "moves": []}


def test_learnset_route(client, db_conn, monkeypatch):
    seed_world(db_conn)
    import api as api_module
    monkeypatch.setattr(api_module, "get_db", lambda: db_conn)

    response = client.get("/api/species/495/learnset?game_id=17")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["version_group_id"] == 11
    assert [m["move_name"] for m in payload["moves"]] == ["Tackle", "Vine Whip", "Leaf Storm"]
