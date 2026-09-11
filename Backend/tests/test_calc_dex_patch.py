"""
The damage calculator's dex patch: a hack's override rows (its reserved
version group's species stats/types/abilities and move data) come back as
one payload; vanilla games get an empty patch so the calculator's stock
data stands.
"""
import backend as backend_module


def seed_world(db_conn):
    db_conn.execute(
        "insert into games (game_id, name, version_group_id, generation) "
        "values (17, 'Black', 11, 5), (1001, 'Blaze Black', 1001, 5)")
    db_conn.execute(
        "update games set base_game_id = 17, is_rom_hack = true where game_id = 1001")
    db_conn.execute(
        "insert into species (species_id, name) values (497, 'SERPERIOR'), (83, 'FARFETCHD')")
    # Hack overrides live under the reserved version group; the vanilla rows
    # (vg 11 / null) must never leak into the patch.
    db_conn.execute(
        "insert into species_stats (species_id, hp, atk, def, spa, spd, spe, version_group_id) "
        "values (497, 75, 75, 95, 75, 95, 113, 11), "
        "       (497, 82, 75, 95, 75, 95, 113, 1001)")
    db_conn.execute(
        "insert into species_types (species_id, type1, type2, version_group_id) "
        "values (83, 'normal', 'flying', 11), "
        "       (83, 'fighting', 'flying', 1001)")
    db_conn.execute(
        "insert into species_abilities (species_id, ability1, version_group_id) "
        "values (497, 'Overgrow', 11), (497, 'Contrary', 1001)")
    db_conn.execute(
        "insert into moves (move_id, move_name, type, damage_class, power, accuracy, version_group_id) "
        "values (15, 'cut', 'normal', 'physical', 50, 95, null), "
        "       (15, 'Cut', 'grass', 'physical', 60, 100, 1001)")
    db_conn.commit()


def test_hack_patch_carries_only_the_override_rows(db_conn):
    seed_world(db_conn)

    patch = backend_module.get_calc_dex_patch(db_conn, 1001)

    assert patch["generation"] == 5
    assert patch["species"]["SERPERIOR"]["stats"] == {
        "hp": 82, "atk": 75, "def": 95, "spa": 75, "spd": 95, "spe": 113}
    assert patch["species"]["SERPERIOR"]["ability"] == "Contrary"
    assert patch["species"]["FARFETCHD"]["types"] == ["fighting", "flying"]
    assert patch["moves"]["Cut"] == {
        "power": 60, "type": "grass", "damage_class": "physical"}


def test_vanilla_game_gets_an_empty_patch(db_conn):
    seed_world(db_conn)

    patch = backend_module.get_calc_dex_patch(db_conn, 17)

    assert patch == {"generation": 5, "species": {}, "moves": {}}


def test_unknown_game_returns_none(db_conn):
    seed_world(db_conn)

    assert backend_module.get_calc_dex_patch(db_conn, 999999) is None
