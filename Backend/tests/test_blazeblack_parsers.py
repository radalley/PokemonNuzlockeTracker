"""
WP8 tests: the Blaze Black doc parsers.

Pure-logic tests; the DB-backed vocabularies are patched in. The full
pipeline's own validation (61/61 skeleton fights matched, zero unresolved
names) ran against the real docs and database before loading.
"""
import pytest

from etl.pipelines.blazeblack import parse_bosses, parse_trainers, parse_wild, reference


@pytest.fixture(autouse=True)
def patched_vocabularies(monkeypatch):
    monkeypatch.setattr(reference, "species_names", lambda: {
        "SNIVY", "OSHAWOTT", "TEPIG", "STARLY", "PANSAGE", "PANSEAR", "PANPOUR",
        "VAPOREON", "ABSOL", "NIDORAN M", "NIDORAN F", "MR-MIME", "GASTRODON",
        "BASCULIN", "DRAPION", "SERPERIOR", "VENUSAUR", "MEGANIUM",
    })
    monkeypatch.setattr(reference, "ability_vocabulary", lambda: {
        "Contrary", "Vital Spirit", "Adaptability", "Overgrow", "Torrent",
        "Blaze", "Sniper", "Keen Eye",
    })
    monkeypatch.setattr(reference, "locations", lambda: {
        "Route 1": 3, "Route 10": 20, "Striaton City": 7, "Challenger's Cave": 495,
    })
    monkeypatch.setattr(reference, "class_sprites", lambda: {
        "TRAINER_CLASS_PKMN_RANGER": "TRAINER_PIC_BW_RANGER_F",
    })
    monkeypatch.setattr(parse_bosses, "move_vocabulary", lambda: {
        parse_bosses._slug(m): m for m in [
            "Quick Attack", "Will-O-Wisp", "Cotton Guard", "Earthquake",
            "Tackle", "Growth", "High Jump Kick", "Stored Power", "Charge Beam",
            "Poison Powder", "Smokescreen",
        ]
    } | {"hijumpkick": "High Jump Kick"})


# ---------------------------------------------------------------------------
# shared resolution
# ---------------------------------------------------------------------------

def test_species_resolution_handles_doc_spellings():
    assert reference.resolve_species("Snivy") == "SNIVY"
    assert reference.resolve_species("NidoranM") == "NIDORAN M"
    assert reference.resolve_species("Nidoran♀") == "NIDORAN F"
    assert reference.resolve_species("Mr. Mime") == "MR-MIME"
    assert reference.resolve_species("Gastrodon-E") == "GASTRODON"
    assert reference.resolve_species("Baculin") == "BASCULIN"
    assert reference.resolve_species("Missingno") is None


def test_location_resolution_uses_aliases():
    assert reference.resolve_location("Striation City") == (7, "Striaton City")
    assert reference.resolve_location("Challengers Cave") == (495, "Challenger's Cave")
    assert reference.resolve_location("Castelia Sewers") is None


def test_ability_triple_splits_multiword_names():
    assert reference.split_abilities("Contrary Vital Spirit Adaptability", 3) == [
        "Contrary", "Vital Spirit", "Adaptability",
    ]
    assert reference.split_abilities("Not An Ability Here", 3) is None


def test_move_splitting_handles_renames_and_asterisks():
    vocab = parse_bosses.move_vocabulary()
    assert parse_bosses.split_known("Will-O-Wisp Cotton Guard Earthquake", 3, vocab) == [
        "Will-O-Wisp", "Cotton Guard", "Earthquake",
    ]
    assert parse_bosses.split_known("Stored Power Charge Beam", 2, vocab) == [
        "Stored Power", "Charge Beam",
    ]
    # Era rename + footnote asterisk.
    assert parse_bosses.split_known("Hi Jump Kick* Tackle", 2, vocab) == [
        "High Jump Kick", "Tackle",
    ]


# ---------------------------------------------------------------------------
# roster parser
# ---------------------------------------------------------------------------

ROSTER_DOC = """
Route 1
---
PKMN Ranger Brenda: Vaporeon L52, Absol L52
* Bianca
Kumi & Amy D: NidoranM L14, NidoranF L14

Unknown Place
---
Youngster Joey: Starly L4
"""


def test_roster_parser_places_and_flags(monkeypatch):
    trainers, pokemon, problems = parse_trainers.parse(ROSTER_DOC)

    by_name = {t["trainer_name"]: t for t in trainers}
    assert by_name["BRENDA"]["canonical_location_id"] == 3
    assert by_name["BRENDA"]["trainer_class"] == "TRAINER_CLASS_PKMN_RANGER"
    assert by_name["BRENDA"]["trainer_pic"] == "TRAINER_PIC_BW_RANGER_F"
    assert by_name["KUMI & AMY"]["trainer_double"] == "true"
    # Starred (boss) entries are skipped; unknown locations leave trainers
    # unplaced but still loaded.
    assert "BIANCA" not in by_name
    assert by_name["JOEY"]["canonical_location_id"] == ""
    assert any("Unknown Place" in p for p in problems)

    brenda = [p for p in pokemon if p["encounter_name"] == by_name["BRENDA"]["encounter_name"]]
    assert [(p["species_name"], p["lvl"], p["slot"]) for p in brenda] == [
        ("VAPOREON", 52, 1), ("ABSOL", 52, 2),
    ]


# ---------------------------------------------------------------------------
# boss parser
# ---------------------------------------------------------------------------

BOSS_DOC = """
Rival Cheren - 2
Battle Type: Single Battle
Location: Striaton City

  Cheren's Team
  \t \t \t
 Species\t Starly\tSnivy Oshawott Tepig\t
Level\t11\t12\t
Item\t-\tOran Berry\t
 Ability (Regular)\t Keen Eye\tContrary Vital Spirit Adaptability\t
 Ability (Clean)\t Keen Eye\tOvergrow Torrent Blaze\t

Team Plasma Ghetsis
Battle Type: Single Battle

 Ghetsis' Team
  \t \t
Species\tDrapion\t
Level\t75\t
Item\t-\t
Ability (Reg.)\tSniper\t
Move #1\tWill-O-Wisp\t
Move #2\tEarthquake\t
Move #3\t-\t
Move #4\t-\t
"""


def test_boss_parser_reads_fights_and_conditionals():
    fights, problems = parse_bosses.parse_document(BOSS_DOC)
    assert [f["header"] for f in fights] == ["Rival Cheren - 2", "Team Plasma Ghetsis"]
    assert fights[0]["battle_type"] == "single"

    cheren_mons = parse_bosses.build_team_mons(fights[0]["teams"][0], problems)
    assert cheren_mons[0]["species"] == "STARLY"
    conditional = cheren_mons[1]["conditional"]
    assert [m["species"] for m in conditional] == ["SNIVY", "OSHAWOTT", "TEPIG"]
    assert [m["ability"] for m in conditional] == ["Contrary", "Vital Spirit", "Adaptability"]
    assert [m["ability_clean"] for m in conditional] == ["Overgrow", "Torrent", "Blaze"]
    assert conditional[0]["item"] == "Oran Berry"

    # Cheren's Snivy variant faces the Water-starter player.
    order = parse_bosses.variant_order(cheren_mons, "CHEREN", problems)
    assert order == ["Water", "Fire", "Grass"]

    ghetsis_mons = parse_bosses.build_team_mons(fights[1]["teams"][0], problems)
    assert ghetsis_mons[0]["species"] == "DRAPION"
    assert ghetsis_mons[0]["moves"] == ["Will-O-Wisp", "Earthquake"]
    assert not problems


def test_label_normalization_covers_doc_dialects():
    cases = {
        "Species": "species",
        "Ability (Regular)": "ability",
        "Ability (Reg.)": "ability",
        "Ability (Clean)": "ability_clean",
        "Item (Reg.)": "item",
        "Item (Clean)": "item_clean",
        "Move #3": "move3",
        "Move #4 (Reg)": "move4",
        "Move #4 (Cln)": "move4_clean",
        "Move #2 (Reg) Move #2 (Cln)": "move2_combined",
        "Reward": None,
    }
    for raw, expected in cases.items():
        assert parse_bosses.normalize_label(raw) == expected, raw


# ---------------------------------------------------------------------------
# wild parser
# ---------------------------------------------------------------------------

WILD_DOC = """
Wild Pokémon
Preamble text about shaking grass.

Route 1

Grass, Normal: Snivy (20%), Tepig (80%)
==================================================================
Challenger's Cave

B2F
Cave, Normal: Basculin (100%)

LEGENDARY ENCOUNTER

Drapion, Level 70
Challenger's Cave, B1F
Cave, Normal, 1%.
"""


def test_wild_parser_attributes_preamble_fused_sections():
    rows, problems = parse_wild.parse(WILD_DOC)
    assert not problems

    route1 = [r for r in rows if r["canonical_location_id"] == 3]
    assert {(r["species_id"], r["enounter_rate"]) for r in route1} == {("SNIVY", 20), ("TEPIG", 80)}

    cave = [r for r in rows if r["canonical_location_id"] == 495]
    species = {r["species_id"] for r in cave}
    # The floor marker keeps encounters in the cave; the legendary lands there too.
    assert species == {"BASCULIN", "DRAPION"}
    legendary = next(r for r in cave if r["species_id"] == "DRAPION")
    assert legendary["method"] == "legendary"
    assert legendary["min_level"] == "70"
