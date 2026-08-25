"""
WP1 tests: trainer identity hardening.

Covers the trainer_id-keyed party lookup (get_trainer_party_by_id), its
slot ordering and encounter-name fallback, the fact that same-named trainers
no longer merge into one party, and the 20260824_trainer_identity.sql
backfill (run against the real throwaway Postgres, twice, to prove the
schema_migrations guard).
"""
from pathlib import Path

import backend as backend_module

MIGRATION_SQL = (
    Path(backend_module.__file__).resolve().parent
    / "migrations"
    / "20260824_trainer_identity.sql"
).read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def seed_trainer(db_conn, *, encounter_name, version_group_id=11, trainer_name="Tester", game_id=None):
    row = db_conn.execute(
        "insert into trainer_pool (encounter_name, trainer_name, version_group_id, game_id) "
        "values (%s, %s, %s, %s) returning trainer_id",
        (encounter_name, trainer_name, version_group_id, game_id),
    ).fetchone()
    db_conn.commit()
    return row["trainer_id"]


def seed_party_row(db_conn, *, encounter_name, species_name, lvl=10,
                   version_group_id=11, trainer_id=None, slot=None, ability=None):
    db_conn.execute(
        "insert into trainer_pokemon (encounter_name, species_name, lvl, version_group_id, trainer_id, slot, ability) "
        "values (%s, %s, %s, %s, %s, %s, %s)",
        (encounter_name, species_name, lvl, version_group_id, trainer_id, slot, ability),
    )
    db_conn.commit()


def seed_species(db_conn, species_id, name):
    db_conn.execute(
        "insert into species (species_id, name) values (%s, %s)",
        (species_id, name),
    )
    db_conn.commit()


# ---------------------------------------------------------------------------
# get_trainer_party_by_id
# ---------------------------------------------------------------------------

def test_party_by_id_returns_rows_in_slot_order(db_conn):
    trainer_id = seed_trainer(db_conn, encounter_name="TRAINER_YOUNGSTER_JOEY")
    seed_species(db_conn, 19, "rattata")
    seed_species(db_conn, 16, "pidgey")
    # Inserted out of slot order on purpose.
    seed_party_row(db_conn, encounter_name="TRAINER_YOUNGSTER_JOEY",
                   species_name="pidgey", lvl=12, trainer_id=trainer_id, slot=2)
    seed_party_row(db_conn, encounter_name="TRAINER_YOUNGSTER_JOEY",
                   species_name="rattata", lvl=14, trainer_id=trainer_id, slot=1)

    party = backend_module.get_trainer_party_by_id(db_conn, trainer_id)

    assert [p["species_name"] for p in party] == ["rattata", "pidgey"]
    assert [p["slot"] for p in party] == [1, 2]
    assert party[0]["species_id"] == 19


def test_party_by_id_does_not_merge_same_named_trainers(db_conn):
    # Same encounter_name in two version groups -- the vanilla-vs-variant
    # collision that broke the name-keyed endpoint.
    vanilla_id = seed_trainer(db_conn, encounter_name="TRAINER_LENORA", version_group_id=11)
    hack_id = seed_trainer(db_conn, encounter_name="TRAINER_LENORA", version_group_id=1001)
    seed_party_row(db_conn, encounter_name="TRAINER_LENORA", species_name="watchog",
                   version_group_id=11, trainer_id=vanilla_id, slot=1)
    seed_party_row(db_conn, encounter_name="TRAINER_LENORA", species_name="miltank",
                   version_group_id=1001, trainer_id=hack_id, slot=1)
    seed_party_row(db_conn, encounter_name="TRAINER_LENORA", species_name="cinccino",
                   version_group_id=1001, trainer_id=hack_id, slot=2)

    vanilla_party = backend_module.get_trainer_party_by_id(db_conn, vanilla_id)
    hack_party = backend_module.get_trainer_party_by_id(db_conn, hack_id)

    assert [p["species_name"] for p in vanilla_party] == ["watchog"]
    assert [p["species_name"] for p in hack_party] == ["miltank", "cinccino"]


def test_party_by_id_falls_back_to_encounter_name(db_conn):
    trainer_id = seed_trainer(db_conn, encounter_name="TRAINER_LASS_EVA", version_group_id=11)
    # Legacy rows: no trainer_id link yet.
    seed_party_row(db_conn, encounter_name="TRAINER_LASS_EVA", species_name="oddish",
                   version_group_id=11, trainer_id=None)
    # A different version group's same-named rows must NOT leak into the fallback.
    seed_party_row(db_conn, encounter_name="TRAINER_LASS_EVA", species_name="bellsprout",
                   version_group_id=14, trainer_id=None)

    party = backend_module.get_trainer_party_by_id(db_conn, trainer_id)

    assert [p["species_name"] for p in party] == ["oddish"]


def test_party_by_id_unknown_trainer_returns_none(db_conn):
    assert backend_module.get_trainer_party_by_id(db_conn, 999999) is None


def test_party_by_id_exposes_trainer_ability(db_conn):
    trainer_id = seed_trainer(db_conn, encounter_name="TRAINER_ACE_CAITLIN")
    seed_party_row(db_conn, encounter_name="TRAINER_ACE_CAITLIN", species_name="musharna",
                   trainer_id=trainer_id, slot=1, ability="Magic Guard")

    party = backend_module.get_trainer_party_by_id(db_conn, trainer_id)

    assert party[0]["trainer_ability"] == "Magic Guard"


def test_hack_parties_resolve_movesets_against_base_version_group(db_conn):
    """A ROM hack's reserved version group (1000+) must resolve level-up
    movesets against its BASE game's version group -- the resolvers assume
    chronologically ordered vanilla ids, so raw vg 1001 would select the
    newest vanilla learnset instead of Black/White's."""
    db_conn.execute(
        "insert into games (game_id, name, game_tag, generation, version_group_id, valid_game, base_game_id, is_rom_hack) values "
        "(17, 'Black', 'B', 5, 11, 'valid', null, false), "
        "(1001, 'Blaze Black', 'BB', 5, 1001, 'valid', 17, true)"
    )
    db_conn.execute("insert into species (species_id, name) values (504, 'PATRAT')")
    # Distinct learnsets for BW (vg 11) and B2W2 (vg 14).
    db_conn.execute(
        "insert into movesets (species_id, move_id, learn_method, learn_level, version_group_id) values "
        "(504, 33, 'level-up', 1, 11), (504, 44, 'level-up', 1, 14)"
    )
    db_conn.execute(
        "insert into moves (move_id, move_name, type, damage_class, power, accuracy, version_group_id) values "
        "(33, 'Tackle', 'normal', 'physical', 40, 100, null), "
        "(44, 'Bite', 'dark', 'physical', 60, 100, null)"
    )
    db_conn.commit()
    trainer_id = seed_trainer(db_conn, encounter_name="TRAINER_BB_PATRAT_GUY", version_group_id=1001)
    seed_party_row(db_conn, encounter_name="TRAINER_BB_PATRAT_GUY", species_name="PATRAT",
                   version_group_id=1001, trainer_id=trainer_id, slot=1, lvl=5)

    party = backend_module.get_trainer_party_by_id(db_conn, trainer_id, game_id=1001)

    assert party[0]["debug_moveset_selected_version_group_id"] == 11
    assert [m["move_name"] for m in party[0]["resolved_moves"]] == ["Tackle"]


# ---------------------------------------------------------------------------
# the 20260824 migration backfill
# ---------------------------------------------------------------------------

def test_trainer_identity_migration_backfills_and_is_guarded(db_conn):
    trainer_id = seed_trainer(db_conn, encounter_name="TRAINER_HIKER_BRET", version_group_id=11)
    seed_party_row(db_conn, encounter_name="TRAINER_HIKER_BRET", species_name="gigalith",
                   version_group_id=11, trainer_id=None, slot=None)
    seed_party_row(db_conn, encounter_name="TRAINER_HIKER_BRET", species_name="conkeldurr",
                   version_group_id=11, trainer_id=None, slot=None)
    # An orphan with no trainer_pool row must stay unlinked.
    seed_party_row(db_conn, encounter_name="TRAINER_NOBODY", species_name="unown",
                   version_group_id=11, trainer_id=None, slot=None)

    db_conn.execute(MIGRATION_SQL)
    db_conn.commit()

    rows = db_conn.execute(
        "select species_name, trainer_id, slot from trainer_pokemon order by pk_id"
    ).fetchall()
    assert [(r["species_name"], r["trainer_id"], r["slot"]) for r in rows] == [
        ("gigalith", trainer_id, 1),
        ("conkeldurr", trainer_id, 2),
        ("unown", None, 1),
    ]

    # Second run must be a no-op thanks to the schema_migrations guard: a row
    # added afterwards keeps its null trainer_id and slot.
    seed_party_row(db_conn, encounter_name="TRAINER_HIKER_BRET", species_name="probopass",
                   version_group_id=11, trainer_id=None, slot=None)
    db_conn.execute(MIGRATION_SQL)
    db_conn.commit()

    row = db_conn.execute(
        "select trainer_id, slot from trainer_pokemon where species_name = 'probopass'"
    ).fetchone()
    assert row["trainer_id"] is None
    assert row["slot"] is None


# ---------------------------------------------------------------------------
# the legacy name-keyed endpoint still works
# ---------------------------------------------------------------------------

def test_legacy_name_endpoint_unchanged(db_conn):
    db_conn.execute(
        "insert into games (game_id, name, game_tag, generation, version_group_id) "
        "values (17, 'Black', 'B', 5, 11)"
    )
    db_conn.commit()
    seed_trainer(db_conn, encounter_name="TRAINER_FISHERMAN_SEAN", version_group_id=11)
    seed_party_row(db_conn, encounter_name="TRAINER_FISHERMAN_SEAN", species_name="seaking",
                   version_group_id=11)

    party = backend_module.get_trainer_parties_by_encounter(db_conn, "TRAINER_FISHERMAN_SEAN", game_id=17)

    assert [p["species_name"] for p in party] == ["seaking"]
