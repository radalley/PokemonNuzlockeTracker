"""
WP8 tests: the Blaze Black doc parsers.

Pure-logic tests; the DB-backed vocabularies are patched in. The full
pipeline's own validation (61/61 skeleton fights matched, zero unresolved
names) ran against the real docs and database before loading.
"""
import pytest

from etl.pipelines.blazeblack import (parse_bosses, parse_learnsets,
                                      parse_species_changes, parse_trainers,
                                      parse_wild, reference)


SPECIES_CHANGES_DOC = """
#216 Teddiursa - #217 Ursaring
Ability One: Pickup (Teddiursa) / Guts (Ursaring)
Ability Two: Honey Gather (Teddiursa) / Sheer Force (Ursaring)

#351 Castform
Ability One: Colour Change
Ability Two: Colour Change

#012 Butterfree
Special Attack: 80 à 95
Speed: 70 à 90
Total: 385 à 420
Ability One: Compoundeyes
Ability Two: Tinted Lens

#083 Farfetch'd
Type: Fighting / Flying
Ability One: Defiant
Ability Two: Defiant
"""

LEARNSET_DOC = """
General Attack Changes
Rock Slide is now 80 power and 95% accurate.
Fire, Water and Grass Pledge are now 100 power.

Key
+ means the move is totally new to the level up set.
- means the move has replaced the move usually learned at that level.

#006 Charizard
+ Level 1 - Crunch
- Level 41 - Dragon Pulse
= Level 61 - Inferno
+ Belly Drum - Level 83

#041 Zubat, #042 Golbat, #169 Crobat
+ Level 1 - Flail (Zubat)
= Level 16 - Wing Attack
+ Level 49 / 63 / 63 - Nasty Plot
+ Level 21 / 24 - Aqua Jet (Zubat and Golbat only)
+ Level 17 - Reflect, Light Screen (Crobat)
"""


def test_species_changes_parse_all_dialects(monkeypatch):
    monkeypatch.setattr(parse_species_changes, "ability_canon", lambda: {
        "pickup": "Pickup", "guts": "Guts", "honeygather": "Honey Gather",
        "sheerforce": "Sheer Force", "colorchange": "Color Change",
        "compoundeyes": "Compoundeyes", "tintedlens": "Tinted Lens",
        "defiant": "Defiant",
    })
    monkeypatch.setattr(parse_species_changes, "_species_name_to_id", lambda: {
        "teddiursa": 216, "ursaring": 217,
    })
    changes, problems = parse_species_changes.parse(SPECIES_CHANGES_DOC)

    assert changes[216]["ability1"] == "Pickup"
    assert changes[217]["ability1"] == "Guts"
    assert changes[217]["ability2"] == "Sheer Force"
    # British spelling resolves through the alias map.
    assert changes[351]["ability1"] == "Color Change"
    assert changes[12]["stats"] == {"spa": 95, "spe": 90}
    assert changes[83]["types"] == ("Fighting", "Flying")
    assert not problems


def test_unresolved_member_restriction_is_loud_not_global():
    doc = """
Key
#041 Zubat, #042 Golbat, #169 Crobat
+ Level 5 - Bite (Zubbat)
"""
    _, deltas, problems = parse_learnsets.parse(doc)
    # The typo'd restriction must not silently apply to every member.
    assert not any(d for d in deltas.values())
    assert any("unresolved member restriction" in p for p in problems)


def test_learnset_parse_all_dialects():
    move_changes, deltas, problems = parse_learnsets.parse(LEARNSET_DOC)

    assert not problems
    names = {c["name"]: c for c in move_changes}
    assert names["Rock Slide"]["power"] == 80
    assert names["Rock Slide"]["accuracy"] == 95
    assert {"Fire Pledge", "Water Pledge", "Grass Pledge"} <= set(names)

    assert deltas[6] == [
        ("+", 1, "Crunch"), ("-", 41, "Dragon Pulse"),
        ("=", 61, "Inferno"), ("+", 83, "Belly Drum"),
    ]
    # Family header: restriction, all-members, per-member levels,
    # restricted-zip levels, comma pairs.
    assert ("+", 1, "Flail") in deltas[41]
    assert ("+", 1, "Flail") not in deltas[42]
    assert ("=", 16, "Wing Attack") in deltas[41] and ("=", 16, "Wing Attack") in deltas[169]
    assert ("+", 49, "Nasty Plot") in deltas[41]
    assert ("+", 63, "Nasty Plot") in deltas[42] and ("+", 63, "Nasty Plot") in deltas[169]
    assert ("+", 21, "Aqua Jet") in deltas[41] and ("+", 24, "Aqua Jet") in deltas[42]
    assert not any(m == "Aqua Jet" for _, _, m in deltas[169])
    assert ("+", 17, "Reflect") in deltas[169] and ("+", 17, "Light Screen") in deltas[169]


@pytest.fixture(autouse=True)
def patched_vocabularies(monkeypatch):
    monkeypatch.setattr(reference, "species_names", lambda: {
        "SNIVY", "OSHAWOTT", "TEPIG", "STARLY", "PANSAGE", "PANSEAR", "PANPOUR",
        "VAPOREON", "ABSOL", "NIDORAN M", "NIDORAN F", "MR-MIME", "GASTRODON",
        "BASCULIN", "DRAPION", "SERPERIOR", "VENUSAUR", "MEGANIUM",
        "SANDILE", "MAROWAK", "VIRIZION", "TORNADUS", "THUNDURUS",
        "MUSHARNA", "RESHIRAM", "ZEKROM",
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
    monkeypatch.setattr(reference, "name_pics", lambda: {
        "KUMI & AMY": [("TRAINER_CLASS_TWINS", "TRAINER_PIC_BW_TWINS")],
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
    # The vanilla namesake's pic wins over the class fallback, across the
    # doc-class/vanilla-class divide (Duo vs Twins).
    assert by_name["KUMI & AMY"]["trainer_pic"] == "TRAINER_PIC_BW_TWINS"
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


WILD_DIALECTS_DOC = """
Route 1

Grass, Normal: Snivy (20%), Tepig (30%), Basculin (20%), Starly (20%),
Absol (10%)
Sand: Sandile (100%)

LEGENDARY ENCOUNTER

Virizion. Level 56
Rumination Field
==================================================================
Route 10

Grass, Normal: Marowak (100%)

LEGENDARY ENCOUNTER
 /
Tornadus, Level 40 (Volt White) / Thundurus, Level 40 (Blaze Black)
Route 10, Main Route
Grass, Shaking, 1%

SPECIAL ENCOUNTER

Musharna, Level 70
Dream Basement
==================================================================
N's Castle

LEGENDARY ENCOUNTER
 /
Reshiram (Blaze Black) | Zekrom (Volt White)
Level 70
N's Castle
==================================================================
Striaton City

Grass, Normal: Vaporeon (100%)
"""


def test_wild_parser_dialects():
    rows, problems = parse_wild.parse(WILD_DIALECTS_DOC)

    # An unresolvable location inside an unknown section is loud, not leaked.
    assert sorted(problems) == [
        "legendary encounter with no resolvable location: 'Reshiram'",
        "legendary encounter with no resolvable location: 'Zekrom'",
    ]
    assert not any(r["species_id"] in ("RESHIRAM", "ZEKROM") for r in rows)

    route1 = [r for r in rows if r["canonical_location_id"] == 3]
    # The wrapped slot list continues onto the bare species line.
    assert any(r["species_id"] == "ABSOL" and r["method"] == "grass-normal" for r in route1)
    # Single-label desert lines get a default kind.
    assert any(r["species_id"] == "SANDILE" and r["method"] == "sand-normal" for r in route1)
    # 'Virizion. Level 56' (period) parses; with no slot line it lands as a
    # 1%-style static without eating the next section's header.
    virizion = [r for r in route1 if r["species_id"] == "VIRIZION"]
    assert {(r["min_level"], r["enounter_rate"]) for r in virizion} == {("56", 1)}

    route10 = [r for r in rows if r["canonical_location_id"] == 20]
    assert any(r["species_id"] == "MAROWAK" for r in route10)
    # Inline split-game legendary: one row per named game.
    split = {(r["species_id"], r["game_id"]) for r in route10
             if r["species_id"] in ("TORNADUS", "THUNDURUS")}
    assert split == {("TORNADUS", reference.VOLT_WHITE_GAME_ID),
                     ("THUNDURUS", reference.BLAZE_BLACK_GAME_ID)}
    # SPECIAL ENCOUNTER blocks load with their own method label.
    musharna = [r for r in route10 if r["species_id"] == "MUSHARNA"]
    assert {r["method"] for r in musharna} == {"special"}
    assert {r["game_id"] for r in musharna} == set(parse_wild.ALL_GAMES)

    # The section after the unknown one recovers cleanly.
    striaton = [r for r in rows if r["canonical_location_id"] == 7]
    assert {r["species_id"] for r in striaton} == {"VAPOREON"}
