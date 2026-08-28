"""Reference data the Blaze Black parsers resolve against.

Everything here comes from the live database (species names, ability
vocabulary, the vanilla BW boss skeleton, location ids, class sprites), so
the parsers fail loudly when the docs and the database disagree instead of
guessing.
"""
import re
from functools import lru_cache

from ... import db, normalize

VERSION_GROUP_ID = 1001
BASE_VERSION_GROUP_ID = 11
LOAD_BUILD = 7
BLAZE_BLACK_GAME_ID = 1001
VOLT_WHITE_GAME_ID = 1002
BASE_GAME_IDS = {17: BLAZE_BLACK_GAME_ID, 18: VOLT_WHITE_GAME_ID}

# Doc spellings that differ from canon location names.
LOCATION_ALIASES = {
    "striation city": "Striaton City",
    "fuschia city": "Fuchsia City",
    "challengers cave": "Challenger's Cave",
    "wellspring cave": "Wellspring Cave",
    "moor of icirrus": "Moor of Icirrus",
    "p2 laboratory": "P2 Laboratory",
    "cold storage": "Cold Storage",
    "driftveil drawbidge": "Driftveil Drawbridge",
    "dragonspiral tower": "Dragonspiral Tower",
    "abundant shrine": "Abundant Shrine",
    "giant chasm": "Giant Chasm",
    "n's castle": "N's Castle",
    "nuvema town": "Nuvema Town",
}

# Doc species spellings that upper-casing alone does not resolve.
SPECIES_ALIASES = {
    "NIDORANM": "NIDORAN M",
    "NIDORANF": "NIDORAN F",
    "NIDORAN♂": "NIDORAN M",
    "NIDORAN♀": "NIDORAN F",
    "NIDORAN M": "NIDORAN M",
    "NIDORAN F": "NIDORAN F",
    "MR. MIME": "MR-MIME",
    "MR MIME": "MR-MIME",
    "MIME JR.": "MIME-JR",
    "MIME JR": "MIME-JR",
    "FARFETCH'D": "FARFETCHD",
    "GASTRODON-E": "GASTRODON",
    "GASTRODON-W": "GASTRODON",
    "SHELLOS-E": "SHELLOS",
    "SHELLOS-W": "SHELLOS",
    "BACULIN": "BASCULIN",
    "PORYGON-Z": "PORYGON-Z",
    "PORYGON2": "PORYGON2",
    "HO-OH": "HO-OH",
}

STARTER_LINES = {
    "SNIVY": "grass", "SERVINE": "grass", "SERPERIOR": "grass",
    "OSHAWOTT": "water", "DEWOTT": "water", "SAMUROTT": "water",
    "TEPIG": "fire", "PIGNITE": "fire", "EMBOAR": "fire",
}

# Derived from the vanilla BW boss rows: which player starter faces which
# rival alternative. Bianca picks the mon weak to the player's starter,
# Cheren the one strong against it. The Striaton trio is handled by name
# matching against the base rows, not by this table.
RIVAL_STARTER_MAP = {
    "BIANCA": {"grass": "Fire", "water": "Grass", "fire": "Water"},
    "CHEREN": {"grass": "Water", "water": "Fire", "fire": "Grass"},
}


@lru_cache(maxsize=1)
def species_names():
    return {row[0] for row in db.query_rows("select name from species")}


@lru_cache(maxsize=1)
def ability_vocabulary():
    rows = db.query_rows(
        "select distinct a from ("
        "select ability1 a from species_abilities union "
        "select ability2 from species_abilities union "
        "select ability3 from species_abilities) x where a is not null and a <> ''"
    )
    return {row[0] for row in rows}


@lru_cache(maxsize=1)
def locations():
    """Canonical name -> id, restricted to the base BW script's locations."""
    rows = db.query_rows(
        "select cl.canonical_location_id, cl.canonical_location_name "
        "from canon_locations cl "
        "join event_locations el on el.canonical_location_id = cl.canonical_location_id "
        f"where el.version_group_id = {BASE_VERSION_GROUP_ID} group by 1, 2"
    )
    return {name: int(location_id) for location_id, name in rows}


@lru_cache(maxsize=1)
def class_sprites():
    """Most common trainer_pic per trainer_class among vanilla BW trainers."""
    rows = db.query_rows(
        "select distinct on (trainer_class) trainer_class, trainer_pic from ("
        "  select trainer_class, trainer_pic, count(*) n from trainer_pool "
        f" where version_group_id = {BASE_VERSION_GROUP_ID} and trainer_pic is not null "
        "  group by 1, 2) x order by trainer_class, n desc"
    )
    return dict(rows)


# The doc's class constants vs vanilla's: the doc collapses gendered classes
# (Preschooler, not Preschooler F/M) and spells a few its own way, so a name
# match must accept these vanilla classes for a doc class.
CLASS_COMPAT = {
    "TRAINER_CLASS_ACE_TRAINER": ("TRAINER_CLASS_ACE_TRAINER_F", "TRAINER_CLASS_ACE_TRAINER_M"),
    "TRAINER_CLASS_ARIST": ("TRAINER_CLASS_ARTIST",),
    "TRAINER_CLASS_ARTIST": ("TRAINER_CLASS_ARTIST",),
    "TRAINER_CLASS_BACKPACKER": ("TRAINER_CLASS_BACKPACKER_F", "TRAINER_CLASS_BACKPACKER_M"),
    "TRAINER_CLASS_CLERK": ("TRAINER_CLASS_CLERK_F", "TRAINER_CLASS_CLERK_M"),
    "TRAINER_CLASS_CYCLING": ("TRAINER_CLASS_CYCLIST_F", "TRAINER_CLASS_CYCLIST_M"),
    "TRAINER_CLASS_DUO": ("TRAINER_CLASS_HOOLIGANS", "TRAINER_CLASS_BACKERS", "TRAINER_CLASS_TWINS"),
    "TRAINER_CLASS_PKMN_BREEDER": ("TRAINER_CLASS_PKMN_BREEDER_F", "TRAINER_CLASS_PKMN_BREEDER_M"),
    "TRAINER_CLASS_PKMN_RANGER": ("TRAINER_CLASS_PKMN_RANGER_F", "TRAINER_CLASS_PKMN_RANGER_M"),
    "TRAINER_CLASS_POKEFAN": ("TRAINER_CLASS_POKEFAN_F", "TRAINER_CLASS_POKEFAN_M"),
    "TRAINER_CLASS_PRESCHOOLER": ("TRAINER_CLASS_PRESCHOOLER_F", "TRAINER_CLASS_PRESCHOOLER_M"),
    "TRAINER_CLASS_PSYCHIC": ("TRAINER_CLASS_PSYCHIC_F", "TRAINER_CLASS_PSYCHIC_M"),
    "TRAINER_CLASS_SCHOOL_KID": ("TRAINER_CLASS_SCHOOL_KID_F", "TRAINER_CLASS_SCHOOL_KID_M"),
    "TRAINER_CLASS_SWIMMER": ("TRAINER_CLASS_SWIMMER_F", "TRAINER_CLASS_SWIMMER_M"),
    "TRAINER_CLASS_VETERAN": ("TRAINER_CLASS_VETERAN_F", "TRAINER_CLASS_VETERAN_M"),
    "TRAINER_CLASS_PLASMA_GRUNT": ("TRAINER_CLASS_TEAM_PLASMA",),
    "TRAINER_CLASS_TEAM_PLASMA_GRUNT": ("TRAINER_CLASS_TEAM_PLASMA",),
}

# Classes whose doc entries are anonymous (no vanilla namesake to inherit
# from). Grunts default to the male grunt art, matching the vanilla majority.
CLASS_FALLBACK_PICS = {
    "TRAINER_CLASS_PLASMA_GRUNT": "TRAINER_PIC_BW_PLASMA_GRUNT_M",
    "TRAINER_CLASS_TEAM_PLASMA_GRUNT": "TRAINER_PIC_BW_PLASMA_GRUNT_M",
}

# Doc names the vanilla name match cannot reach (the doc folds the class into
# the name: vanilla calls the Driftveil duo just "JIM & CAS").
NAME_PIC_OVERRIDES = {
    "HOOLIGANS JIM & CAS": "TRAINER_PIC_BW_HOOLIGANS",
}


@lru_cache(maxsize=1)
def name_pics():
    """Vanilla BW trainer_name -> [(trainer_class, trainer_pic), ...]."""
    rows = db.query_rows(
        "select upper(trainer_name), trainer_class, trainer_pic from trainer_pool "
        f"where version_group_id = {BASE_VERSION_GROUP_ID} "
        "and trainer_name is not null and trainer_pic is not null"
    )
    out = {}
    for name, klass, pic in rows:
        out.setdefault(name, []).append((klass, pic))
    return out


def resolve_trainer_pic(trainer_name, klass):
    """Sprite for a doc trainer: the vanilla namesake's pic first (it carries
    the right gender for classes the doc leaves ungendered), then the class's
    most common vanilla pic, then the anonymous-class fallback."""
    override = NAME_PIC_OVERRIDES.get((trainer_name or "").upper())
    if override:
        return override
    allowed = CLASS_COMPAT.get(klass, (klass,))
    for vanilla_class, pic in name_pics().get((trainer_name or "").upper(), ()):
        if vanilla_class in allowed:
            return pic
    return class_sprites().get(klass) or CLASS_FALLBACK_PICS.get(klass, "")


@lru_cache(maxsize=1)
def base_bosses():
    """The vanilla BW boss skeleton, one entry per boss row."""
    rows = db.query_rows(
        "select eb.event_id, coalesce(eb.encounter_title, ''), coalesce(eb.sort_order, ''), "
        "coalesce(eb.starter, ''), coalesce(eb.type_focus, ''), coalesce(eb.event_type, ''), "
        "coalesce(eb.game_id::text, ''), coalesce(eb.badge_id::text, ''), "
        "coalesce(eb.is_level_cap::text, ''), coalesce(tp.trainer_name, ''), "
        "coalesce(tp.trainer_class, ''), coalesce(tp.trainer_pic, '')"
        " from event_bosses eb join trainer_pool tp on tp.trainer_id = eb.trainer_id "
        f"where eb.version_group_id = {BASE_VERSION_GROUP_ID} "
        "order by eb.sort_order::numeric, eb.event_id"
    )
    bosses = []
    for row in rows:
        (event_id, title, sort_order, starter, type_focus, event_type,
         game_id, badge_id, is_level_cap, name, klass, pic) = row
        bosses.append({
            "event_id": int(event_id),
            "encounter_title": title,
            "sort_order": sort_order,
            "starter": starter,
            "type_focus": type_focus,
            "event_type": event_type,
            "game_id": game_id,
            "badge_id": badge_id,
            "is_level_cap": is_level_cap,
            "trainer_name": name,
            "trainer_class": klass,
            "trainer_pic": pic,
        })
    return bosses


def resolve_location(raw_name):
    """Doc location header -> (canonical_location_id, canonical_name) or None."""
    cleaned = normalize.clean_text(raw_name or "").strip().rstrip(".")
    if not cleaned:
        return None
    key = normalize.title_key(re.sub(r"[’']", "", cleaned))
    aliased = LOCATION_ALIASES.get(key)
    if aliased:
        cleaned = aliased
    match_key = normalize.location_match_key(cleaned)
    for name, location_id in locations().items():
        if normalize.location_match_key(name) == match_key:
            return location_id, name
    return None


def resolve_species(raw_name):
    """Doc species name -> canonical species.name, or None."""
    cleaned = normalize.clean_text(raw_name or "").strip().upper()
    if not cleaned:
        return None
    for candidate in (
        SPECIES_ALIASES.get(cleaned),
        cleaned,
        cleaned.replace("’", "'"),
        cleaned.replace(".", "").replace("'", ""),
        re.sub(r"[^A-Z0-9]+", "-", cleaned).strip("-"),
        re.sub(r"[^A-Z0-9]+", " ", cleaned).strip(),
    ):
        if candidate and candidate in species_names():
            return candidate
    return None


def split_abilities(cell, count):
    """Split a space-joined run of `count` ability names using the known
    vocabulary ("Contrary Vital Spirit Adaptability" -> 3 names)."""
    tokens = normalize.clean_text(cell or "").split()
    vocabulary = ability_vocabulary()

    def backtrack(index, remaining):
        if remaining == 0:
            return [] if index == len(tokens) else None
        for take in range(1, min(4, len(tokens) - index) + 1):
            candidate = " ".join(tokens[index:index + take])
            if candidate in vocabulary:
                rest = backtrack(index + take, remaining - 1)
                if rest is not None:
                    return [candidate] + rest
        return None

    return backtrack(0, count)
