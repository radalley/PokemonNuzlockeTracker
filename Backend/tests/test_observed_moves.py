"""
Observed-moves overlay: admin-recorded ground truth over moveset inference.

The overlay is keyed by ETL identity (version group + encounter name +
slot), never touched by loaders, and only attaches while the recorded
species still occupies the slot.
"""
import pytest

import backend as backend_module


def seed_trainer(db_conn, *, key="TRAINER_ACE_KAY", vg=11, species="SWOOBAT", lvl=27, slot=1):
    trainer_id = db_conn.execute(
        "insert into trainer_pool (encounter_name, trainer_name, version_group_id) "
        "values (%s, 'KAY', %s) returning trainer_id",
        (key, vg),
    ).fetchone()["trainer_id"]
    db_conn.execute(
        "insert into species (species_id, name) values (527, %s) on conflict do nothing",
        (species,),
    )
    db_conn.execute(
        "insert into trainer_pokemon (encounter_name, species_name, lvl, version_group_id, trainer_id, slot) "
        "values (%s, %s, %s, %s, %s, %s)",
        (key, species, lvl, vg, trainer_id, slot),
    )
    db_conn.execute(
        "insert into moves (move_id, move_name, type, damage_class, power, accuracy) "
        "values (403, 'Air Slash', 'FLYING', 'special', 75, 95), "
        "       (60, 'Psybeam', 'PSYCHIC', 'special', 65, 100)"
    )
    db_conn.commit()
    return trainer_id


def test_add_and_attach_observed_move(db_conn):
    trainer_id = seed_trainer(db_conn)

    details = backend_module.add_observed_move(db_conn, trainer_id, 1, "air slash")
    assert details["move_name"] == "Air Slash"  # canonicalized via the move vocabulary

    party = backend_module.get_trainer_party_by_id(db_conn, trainer_id)
    assert len(party) == 1
    observed = party[0]["observed_moves"]
    assert [m["move_name"] for m in observed] == ["Air Slash"]
    assert observed[0]["power"] == 75


def test_unknown_move_rejected(db_conn):
    trainer_id = seed_trainer(db_conn)
    with pytest.raises(ValueError):
        backend_module.add_observed_move(db_conn, trainer_id, 1, "Wood Horn")
    with pytest.raises(ValueError):
        backend_module.add_observed_move(db_conn, trainer_id, 99, "Air Slash")


def test_delete_observed_move(db_conn):
    trainer_id = seed_trainer(db_conn)
    backend_module.add_observed_move(db_conn, trainer_id, 1, "Air Slash")

    removed = backend_module.delete_observed_move(db_conn, trainer_id, 1, "Air Slash")
    assert removed == 1
    party = backend_module.get_trainer_party_by_id(db_conn, trainer_id)
    assert party[0]["observed_moves"] == []


def test_overlay_survives_reextraction_but_respects_species_change(db_conn):
    """Rows key on encounter_name, so recreating the trainer keeps them --
    unless the slot's species changed, in which case they go inert."""
    trainer_id = seed_trainer(db_conn)
    backend_module.add_observed_move(db_conn, trainer_id, 1, "Air Slash")

    # Simulated re-extraction: trainer rows dropped and recreated fresh.
    db_conn.execute("delete from trainer_pokemon where trainer_id = %s", (trainer_id,))
    db_conn.execute("delete from trainer_pool where trainer_id = %s", (trainer_id,))
    new_id = db_conn.execute(
        "insert into trainer_pool (encounter_name, trainer_name, version_group_id) "
        "values ('TRAINER_ACE_KAY', 'KAY', 11) returning trainer_id"
    ).fetchone()["trainer_id"]
    db_conn.execute(
        "insert into trainer_pokemon (encounter_name, species_name, lvl, version_group_id, trainer_id, slot) "
        "values ('TRAINER_ACE_KAY', 'SWOOBAT', 29, 11, %s, 1)",
        (new_id,),
    )
    db_conn.commit()

    party = backend_module.get_trainer_party_by_id(db_conn, new_id)
    assert [m["move_name"] for m in party[0]["observed_moves"]] == ["Air Slash"]

    # The slot's occupant changes: the observation must not mislabel it.
    db_conn.execute(
        "update trainer_pokemon set species_name = 'GOTHORITA' where trainer_id = %s", (new_id,))
    db_conn.commit()
    party = backend_module.get_trainer_party_by_id(db_conn, new_id)
    assert party[0]["observed_moves"] == []


def test_duplicate_add_is_idempotent(db_conn):
    trainer_id = seed_trainer(db_conn)
    backend_module.add_observed_move(db_conn, trainer_id, 1, "Air Slash")
    backend_module.add_observed_move(db_conn, trainer_id, 1, "AIR SLASH")

    rows = db_conn.execute("select count(*) as n from curated_trainer_moves").fetchone()
    assert rows["n"] == 1


def test_readd_after_species_change_revives_the_row(db_conn):
    """A stale observation from a previous extraction must not block
    re-observing the same move on the slot's new occupant."""
    trainer_id = seed_trainer(db_conn)
    backend_module.add_observed_move(db_conn, trainer_id, 1, "Air Slash")
    db_conn.execute(
        "update trainer_pokemon set species_name = 'GOTHORITA' where trainer_id = %s", (trainer_id,))
    db_conn.commit()

    backend_module.add_observed_move(db_conn, trainer_id, 1, "Air Slash")

    party = backend_module.get_trainer_party_by_id(db_conn, trainer_id)
    assert [m["move_name"] for m in party[0]["observed_moves"]] == ["Air Slash"]


def test_delete_accepts_any_spelling(db_conn):
    trainer_id = seed_trainer(db_conn)
    backend_module.add_observed_move(db_conn, trainer_id, 1, "Air Slash")

    removed = backend_module.delete_observed_move(db_conn, trainer_id, 1, "air slash")
    assert removed == 1


def test_comma_input_rejected(db_conn):
    trainer_id = seed_trainer(db_conn)
    with pytest.raises(ValueError):
        backend_module.add_observed_move(db_conn, trainer_id, 1, "Air Slash, Psybeam")


def test_move_name_search(db_conn):
    seed_trainer(db_conn)
    assert backend_module.search_move_names(db_conn, "air") == ["Air Slash"]
    assert backend_module.search_move_names(db_conn, "") == []
