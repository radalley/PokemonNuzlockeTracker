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
        # the encounter-table fixtures
        "WOOBAT", "ZUBAT", "DRILBUR", "GOLBAT", "CHERUBI", "DEERLING", "FINNEON",
        "SNOVER", "SEEL", "MIENSHAO", "SAWSBUCK", "SEADRA", "BEARTIC", "DRUDDIGON",
        "BALTOY", "GOLETT", "ARTICUNO", "SUICUNE", "PHANPY", "DONPHAN", "REGICE",
        "ONIX", "STEELIX", "UXIE", "COBALION", "KROKOROK", "REGIROCK", "REGIGIGAS",
        "VOLCARONA", "MISDREAVUS", "CRESSELIA", "MANTINE", "KYOGRE", "PALPITOAD",
        "MAWILE", "PATRAT", "MEW", "EMOLGA", "SUNFLORA", "VESPIQUEN",
    })
    monkeypatch.setattr(reference, "ability_vocabulary", lambda: {
        "Contrary", "Vital Spirit", "Adaptability", "Overgrow", "Torrent",
        "Blaze", "Sniper", "Keen Eye",
    })
    monkeypatch.setattr(reference, "locations", lambda: {
        "Route 1": 3, "Route 10": 20, "Striaton City": 7, "Challenger's Cave": 495,
        "Route 2": 4, "Route 6": 15, "Route 8": 12, "Route 12": 23, "Icirrus City": 498,
        "Wellspring Cave": 235, "Relic Castle": 240, "Mistralton Cave": 243,
        "Celestial Tower": 246, "Twist Mountain": 247, "Dragonspiral Tower": 249,
        "Undella Bay": 259,
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
    assert {r["method"] for r in route1} == {"grass"}
    assert {(r["area"], r["area_sort"], r["condition"], r["slot_kind"]) for r in route1} == {("", 0, "", "slot")}

    cave = [r for r in rows if r["canonical_location_id"] == 495]
    species = {r["species_id"] for r in cave}
    # The floor marker keeps encounters in the cave, as their own floor.
    assert species == {"BASCULIN", "DRAPION"}
    basculin = next(r for r in cave if r["species_id"] == "BASCULIN")
    assert (basculin["method"], basculin["area"], basculin["area_sort"]) == ("cave", "B2F", 1)
    # The legendary is a 1% overlay on the cave's host method, filed under
    # the floor it names -- a floor no table lists becomes its own area.
    legendary = next(r for r in cave if r["species_id"] == "DRAPION")
    assert (legendary["method"], legendary["slot_kind"], legendary["tag"]) == ("cave", "overlay", "legendary")
    assert (legendary["area"], legendary["area_sort"], legendary["enounter_rate"]) == ("B1F", 2, 1)
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
    assert any(r["species_id"] == "ABSOL" and r["method"] == "grass" for r in route1)
    # Single-label desert lines map like any other label.
    assert any(r["species_id"] == "SANDILE" and r["method"] == "sand" for r in route1)
    # 'Virizion. Level 56' (period) parses; with no slot line it is a
    # static encounter (no rate) in the room it names, and it does not eat
    # the next section's header.
    virizion = [r for r in route1 if r["species_id"] == "VIRIZION"]
    assert {(r["min_level"], r["enounter_rate"], r["slot_kind"], r["method"], r["tag"], r["area"])
            for r in virizion} == {("56", "", "static", "static", "legendary", "Rumination Field")}

    route10 = [r for r in rows if r["canonical_location_id"] == 20]
    assert any(r["species_id"] == "MAROWAK" for r in route10)
    # Inline split-game legendary: one row per named game, as overlays on
    # the shaking grass of the area the block names.
    split = {(r["species_id"], r["game_id"], r["method"], r["slot_kind"], r["area"]) for r in route10
             if r["species_id"] in ("TORNADUS", "THUNDURUS")}
    assert split == {("TORNADUS", reference.VOLT_WHITE_GAME_ID, "grass-spots", "overlay", "Main Route"),
                     ("THUNDURUS", reference.BLAZE_BLACK_GAME_ID, "grass-spots", "overlay", "Main Route")}
    # SPECIAL ENCOUNTER blocks with no slot line are statics tagged special.
    musharna = [r for r in route10 if r["species_id"] == "MUSHARNA"]
    assert {(r["method"], r["slot_kind"], r["tag"], r["area"]) for r in musharna} == {
        ("static", "static", "special", "Dream Basement")}
    assert {r["game_id"] for r in musharna} == set(parse_wild.ALL_GAMES)

    # The section after the unknown one recovers cleanly.
    striaton = [r for r in rows if r["canonical_location_id"] == 7]
    assert {r["species_id"] for r in striaton} == {"VAPOREON"}


WILD_TABLES_DOC = """
Wellspring Cave 1F

1F
Cave, Normal: Woobat (60%), Zubat (40%)
Cave, Special: Drilbur (100%)

B1F
Cave, Normal: Woobat (50%), Golbat (50%)
==================================================================
Route 6 - Spring / Summer / Autumn

Grass, Normal: Cherubi (60%), Deerling (40%)
Surf, Normal: Finneon (100%)

Route 6 - Winter
Grass, Normal: Snover (60%), Deerling (40%)
Surf, Normal: Seel (100%)

LEGENDARY ENCOUNTER

Mew, Level 50
Route 6, Summer
Grass, Normal, 1%
==================================================================
Dragonspiral Tower

Outside (Both Areas) - Spring, Summer, Autumn
Grass, Doubles: Mienshao (50%), Sawsbuck (50%)
Surf, Special: Seadra (100%)

Outside (Both Areas) - Winter
Grass, Doubles: Mienshao (50%), Beartic (50%)
Surf, Special: Seadra (100%)

Inside - Room One
Tower, Normal: Druddigon (40%), Baltoy (30%), Golett (30%)

LEGENDARY ENCOUNTER

Articuno, Level 50
Dragonspiral Tower, Outside, Winter
Doubles Grass, 1%.
* Only in the doubles grass right outside the tower!

LEGENDARY ENCOUNTER

Suicune, Level 50
Dragonspiral Tower, Outside, Spring, Summer & Autumn
Surf, Special, 1%.
==================================================================
Twist Mountain

1F - All Seasons
Cave, Normal: Phanpy (100%)

Not 1F - All Seasons
Cave, Normal: Donphan (100%)

LEGENDARY ENCOUNTER

Regice, Level 50
Twist Mountain, Ice Rock Room, Winter
Cave, Normal, 1%
==================================================================
Mistralton Cave 1F - 2F

Cave, Normal: Onix (100%)

Mistralton Cave 3F (Guidance Chamber)
Cave, Normal: Steelix (100%)

LEGENDARY ENCOUNTER

Uxie, Level 50
Mistralton Cave, 1F
Cave, Normal, 1%

LEGENDARY ENCOUNTER

Cobalion, Level 56
Guidance Chamber
==================================================================
Relic Castle

B2F, B3F, B4F, B5F
Sand: Krokorok (100%)

LEGENDARY ENCOUNTER

Regirock, Level 50
Relic Castle, B5F
Sand, 1%

LEGENDARY ENCOUNTER

Regigigas. Level 70
Relic Castle, Volcarona Room
Floor, 1%

SPECIAL ENCOUNTER

Volcarona, Level 75
Relic Castle, Volcarona Room, Winter
* Only after the Regis wake.
==================================================================
Celestial Tower

5F (Roof)
Tower, Normal: Misdreavus (100%)

LEGENDARY ENCOUNTER

Cresselia, Level 50
Celestial Tower, Roof
Tower, Normal, 1%
==================================================================
Undella Bay

All Seasons
Surf, Special: Mantine (100%)

LEGENDARY ENCOUNTER

Kyogre, Level 70
Undella Bay, Summer
Surf, Special, 1%
==================================================================
Icirrus City, Route 8

Puddle, Normal: Palpitoad (100%)
==================================================================
Challenger's Cave - All Floors

Cave, Normal: Mawile (100%)
"""


def _table(rows, location_id, key, area="", condition=""):
    return [r for r in rows if r["canonical_location_id"] == location_id and r["method"] == key
            and r["area"] == area and r["condition"] == condition and r["slot_kind"] == "slot"]


def test_wild_parser_keeps_floors_and_seasons_apart():
    rows, problems = parse_wild.parse(WILD_TABLES_DOC)
    assert not problems, problems

    def loc(name):
        return reference.resolve_location(name)[0]

    # A cave's floors are separate tables in doc order; both sum to 100.
    wellspring = loc("Wellspring Cave")
    first = _table(rows, wellspring, "cave", area="1F")
    basement = _table(rows, wellspring, "cave", area="B1F")
    assert sum(r["enounter_rate"] for r in first if r["game_id"] == 1001) == 100
    assert sum(r["enounter_rate"] for r in basement if r["game_id"] == 1001) == 100
    assert {r["area_sort"] for r in first} == {1} and {r["area_sort"] for r in basement} == {2}
    assert {r["method"] for r in _table(rows, wellspring, "cave-spots", area="1F")} == {"cave-spots"}

    # A seasonal title splits the route into two conditioned tables.
    route6 = loc("Route 6")
    warm = _table(rows, route6, "grass", condition="season:spring,summer,autumn")
    cold = _table(rows, route6, "grass", condition="season:winter")
    assert {r["species_id"] for r in warm} == {"CHERUBI", "DEERLING"}
    assert {r["species_id"] for r in cold} == {"SNOVER", "DEERLING"}
    assert not _table(rows, route6, "grass")

    # '(Both Areas)' is dropped, the marker's season is kept, and a marker
    # without one is all seasons; 'Inside - Room One' stays one label.
    tower = loc("Dragonspiral Tower")
    assert _table(rows, tower, "dark-grass", area="Outside", condition="season:winter")
    assert _table(rows, tower, "dark-grass", area="Outside", condition="season:spring,summer,autumn")
    assert _table(rows, tower, "tower", area="Inside - Room One")

    # 'All Seasons' on a marker or a bare line means no condition.
    twist = loc("Twist Mountain")
    assert _table(rows, twist, "cave", area="1F") and _table(rows, twist, "cave", area="Not 1F")
    assert _table(rows, loc("Undella Bay"), "surf-spots")

    # Floor ranges and parenthesised floors ride on the title.
    mistralton = loc("Mistralton Cave")
    assert _table(rows, mistralton, "cave", area="1F - 2F")
    assert _table(rows, mistralton, "cave", area="3F (Guidance Chamber)")

    # 'All Floors' is no area; a two-place header feeds both places.
    assert _table(rows, loc("Challenger's Cave"), "cave")
    assert _table(rows, loc("Icirrus City"), "puddle") and _table(rows, loc("Route 8"), "puddle")


def test_wild_parser_files_overlays_and_statics_by_room():
    rows, problems = parse_wild.parse(WILD_TABLES_DOC)
    assert not problems, problems

    def one(species):
        matches = [r for r in rows if r["species_id"] == species and r["game_id"] == 1001]
        assert len(matches) == 1, species
        return matches[0]

    # A seasonal overlay joins the table whose seasons cover it and keeps
    # the host method, its own season, the badge, the level and the note.
    articuno = one("ARTICUNO")
    assert (articuno["method"], articuno["area"], articuno["condition"]) == ("dark-grass", "Outside", "season:winter")
    assert (articuno["slot_kind"], articuno["tag"], articuno["enounter_rate"], articuno["min_level"]) == ("overlay", "legendary", 1, "50")
    assert articuno["note"] == "Only in the doubles grass right outside the tower!"
    suicune = one("SUICUNE")
    assert (suicune["method"], suicune["area"], suicune["condition"]) == ("surf-spots", "Outside", "season:spring,summer,autumn")
    assert suicune["note"] == ""
    # A season on an all-seasons table stays on the overlay row.
    kyogre = one("KYOGRE")
    assert (kyogre["area"], kyogre["condition"], kyogre["method"]) == ("", "season:summer", "surf-spots")
    # An overlay with its own season joins the seasonal table covering it
    # (spring/summer/autumn, not winter) and keeps its own season.
    mew = one("MEW")
    assert (mew["method"], mew["area"], mew["condition"], mew["slot_kind"]) == ("grass", "", "season:summer", "overlay")
    # Room aliases, floor membership and parenthesised floors all resolve.
    assert (one("REGICE")["area"], one("REGICE")["condition"]) == ("Not 1F", "season:winter")
    assert one("UXIE")["area"] == "1F - 2F"
    assert one("REGIROCK")["area"] == "B2F, B3F, B4F, B5F"
    assert one("CRESSELIA")["area"] == "5F (Roof)"
    # A room no table lists becomes its own area, shared by the static
    # that names the same room; a static resolves its room the same way.
    regigigas, volcarona = one("REGIGIGAS"), one("VOLCARONA")
    assert (regigigas["method"], regigigas["slot_kind"], regigigas["area"]) == ("floor", "overlay", "Volcarona Room")
    assert (volcarona["method"], volcarona["slot_kind"], volcarona["tag"], volcarona["enounter_rate"]) == ("static", "static", "special", "")
    assert volcarona["area_sort"] == regigigas["area_sort"] > 0
    # A static keeps its season, and a footnote after it lands on it alone.
    assert (volcarona["condition"], volcarona["note"]) == ("season:winter", "Only after the Regis wake.")
    assert regigigas["note"] == ""
    assert one("COBALION")["area"] == "3F (Guidance Chamber)"


WILD_BROKEN_DOC = """
Route 1

Grass, Normal: Snivy (60%), Tepig (30%)
Sky, Normal: Starly (100%)
Grass, Doubles: Snivy (60%), Snivy (40%)
==================================================================
Route 12

Grass, Special: Emolga (95%), Sunflora (5%), Vespiquen (5%)
==================================================================
Route 2

Grass, Normal: Patrat (100%)

LEGENDARY ENCOUNTER

Mew, Level 30
Route 2
Grass, Normal, 10%
"""


WILD_MIXED_DOC = """
Route 1

Grass, Normal: Snivy (100%)

Outside
Grass, Doubles: Tepig (100%)

Route 1 - Winter
Grass, Normal: Starly (100%)

SPECIAL ENCOUNTER

Musharna, Level 70
Route 1
"""


def test_wild_parser_handles_mixed_areas_and_a_trailing_static():
    rows, problems = parse_wild.parse(WILD_MIXED_DOC)
    assert not problems, problems
    # whole-location, floor and seasonal tables coexist without upsetting the sum check
    assert {(r["area"], r["condition"], r["method"]) for r in rows if r["slot_kind"] == "slot" and r["game_id"] == 1001} == {
        ("", "", "grass"), ("Outside", "", "dark-grass"), ("", "season:winter", "grass"),
    }
    # a static block that ends the document is still flushed
    musharna = [r for r in rows if r["species_id"] == "MUSHARNA" and r["game_id"] == 1001]
    assert [(r["slot_kind"], r["tag"], r["min_level"]) for r in musharna] == [("static", "special", "70")]


def test_wild_parser_reports_broken_tables():
    rows, problems = parse_wild.parse(WILD_BROKEN_DOC)
    assert "table sums to 90%: Route 1 / whole location / all seasons / grass" in problems
    assert "unknown encounter method 'Sky, Normal' at Route 1" in problems
    assert any(p.startswith("duplicate slot with a different rate at Route 1") and "SNIVY" in p for p in problems)
    assert any(p.startswith("overlay rate above 5% at Route 2") for p in problems)
    # The doc's own 105% shaking-grass table on Route 12 is allowlisted...
    assert not any("Route 12" in p for p in problems)
    assert not any(r["species_id"] == "STARLY" for r in rows)
    # ...but only at exactly that sum.
    _, problems = parse_wild.parse(WILD_BROKEN_DOC.replace("Vespiquen (5%)", "Vespiquen (10%)"))
    assert "table sums to 110%: Route 12 / whole location / all seasons / grass-spots" in problems


def test_wild_parser_method_vocabulary_is_the_registry():
    import encounter_methods
    assert set(parse_wild.METHOD_KEYS.values()) <= set(encounter_methods.METHOD_KEYS)
    assert "static" in encounter_methods.METHOD_KEYS


def test_floor_ranges_expand_to_every_floor_between():
    assert parse_wild.expand_floors("1F - 4F") == {"1F", "2F", "3F", "4F"}
    assert parse_wild.expand_floors("B2F, B3F, B4F, B5F") == {"B2F", "B3F", "B4F", "B5F"}
    assert parse_wild.expand_floors("5F (Roof)") == {"5F"}
    assert parse_wild.expand_floors("Outside") == set()
    assert parse_wild.expand_floors("B1F - B3F") == {"B1F", "B2F", "B3F"}
    assert parse_wild.expand_floors("B3F - B1F") == {"B1F", "B2F", "B3F"}
    # a range across the basement boundary is not expanded: just its endpoints
    assert parse_wild.expand_floors("B1F - 1F") == {"B1F", "1F"}
    assert parse_wild.expand_floors("Not 1F") == {"1F"}
    assert parse_wild.expand_floors("Pot Rooms") == set()


WILD_OVERLAY_EDGES_DOC = """
Twist Mountain

Not 1F - All Seasons
Cave, Normal: Donphan (100%)

LEGENDARY ENCOUNTER

Regice, Level 50
Twist Mountain, 1F
Cave, Normal, 1%
==================================================================
Mistralton Cave 1F - 4F

Cave, Normal: Onix (100%)

LEGENDARY ENCOUNTER

Uxie, Level 50
Mistralton Cave, 3F
Cave, Normal, 1%
==================================================================
Undella Bay

All Seasons
Surf, Special: Mantine (100%)

Summer
Surf, Special: Seadra (100%)

LEGENDARY ENCOUNTER

Kyogre, Level 70
Undella Bay
Surf, Special, 1%
"""


def test_overlay_filing_edges():
    rows, problems = parse_wild.parse(WILD_OVERLAY_EDGES_DOC)
    assert not problems, problems
    one = lambda name: next(r for r in rows if r["species_id"] == name and r["game_id"] == 1001)
    # '1F' must not fall into 'Not 1F' by floor membership: it becomes its own area
    assert one("REGICE")["area"] == "1F"
    # a floor inside a range joins the range's table
    assert one("UXIE")["area"] == "1F - 4F"
    # an unconditioned overlay prefers the all-seasons table over a seasonal one
    assert one("KYOGRE")["condition"] == ""


WILD_OVERLAY_SEASONS_DOC = """
Dragonspiral Tower

Outside - Winter
Grass, Normal: Snover (100%)

Outside - All Seasons
Surf, Normal: Seadra (100%)

LEGENDARY ENCOUNTER

Articuno, Level 50
Dragonspiral Tower, Outside
Grass, Normal, 1%
==================================================================
Route 6 - Winter

Grass, Normal: Snover (100%)

LEGENDARY ENCOUNTER

Mew, Level 50
Route 6, Summer
Grass, Normal, 1%
"""


def test_overlay_seasons_follow_the_host_method_and_uncovered_ones_are_loud():
    rows, problems = parse_wild.parse(WILD_OVERLAY_SEASONS_DOC)
    one = lambda name: next(r for r in rows if r["species_id"] == name and r["game_id"] == 1001)
    # An unconditioned overlay inherits the season of the table with its own
    # method, not the all-seasons table of another method at the same area.
    assert (one("ARTICUNO")["area"], one("ARTICUNO")["condition"]) == ("Outside", "season:winter")
    # A season no grass table covers is reported; the row still lands with
    # its own season rather than vanishing.
    assert problems == ["overlay season no table covers at Route 6 / whole location: Mew grass season:summer"]
    assert one("MEW")["condition"] == "season:summer"


def test_wild_parser_pipe_split_block_emits_one_static_per_game():
    doc = """Route 1

Grass, Normal: Snivy (100%)

LEGENDARY ENCOUNTER
/
Reshiram (Blaze Black) | Zekrom (Volt White)
Level 70
Route 1
==================================================================
Striaton City

Grass, Normal: Vaporeon (100%)
"""
    rows, problems = parse_wild.parse(doc)
    assert not problems, problems
    split = {(r["species_id"], r["game_id"], r["slot_kind"], r["min_level"], r["canonical_location_id"])
             for r in rows if r["species_id"] in ("RESHIRAM", "ZEKROM")}
    assert split == {("RESHIRAM", 1001, "static", "70", 3), ("ZEKROM", 1002, "static", "70", 3)}
    # the static closed at the section rule, so the next title still resolves
    assert _table(rows, 7, "grass")


def test_wild_parser_all_floors_marker_line_means_no_area():
    rows, problems = parse_wild.parse("""Route 10

All Floors
Cave, Normal: Mawile (100%)
""")
    assert not problems, problems
    assert {r["area"] for r in _table(rows, 20, "cave")} == {""}
