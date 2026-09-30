"""Parse "Pokemon Changes.txt" -- Blaze Black's species rewrites.

Species blocks are keyed by national dex number, singly or as a range that
applies to every id in it:

    #001 Bulbasaur - #002 Ivysaur
    Ability One: Overgrow
    Ability Two: Chlorophyll
    Special Attack: 80 à 95
    Type: Fighting / Flying

Abilities are listed for every species regardless of change (Regular mode;
Clean keeps vanilla). Stats appear only when changed, as old-arrow-new
pairs; Type only for the 18 retyped species. Item / TM / HM / Evolution /
Base EXP / Happiness lines are flavor and are skipped.
"""
import re
from functools import lru_cache

from ... import db, normalize

HEADER_ID_PATTERN = re.compile(r"#(\d{3})")
STAT_PATTERN = re.compile(r"^(?P<stat>HP|Attack|Defense|Special Attack|Special Defense|Speed):\s*\d+\s*\S+\s*(?P<new>\d+)\s*$")
SKIP_LABELS = ("item", "items", "tm", "hm", "tutor", "evolution", "base exp",
               "base happiness", "catch rate", "total", "stat total")

STAT_COLUMNS = {
    "HP": "hp", "Attack": "atk", "Defense": "def",
    "Special Attack": "spa", "Special Defense": "spd", "Speed": "spe",
}

VALID_TYPES = {
    "Normal", "Fire", "Water", "Electric", "Grass", "Ice", "Fighting",
    "Poison", "Ground", "Flying", "Psychic", "Bug", "Rock", "Ghost",
    "Dragon", "Dark", "Steel",
}


def _slug(text):
    return re.sub(r"[^a-z0-9]+", "", (text or "").lower())


@lru_cache(maxsize=1)
def ability_canon():
    """collapsed slug -> canonical ability name ('compoundeyes' -> stored form)."""
    canon = {}
    for (name,) in db.query_rows(
        "select distinct a from (select ability1 a from species_abilities union "
        "select ability2 from species_abilities union select ability3 from species_abilities) x "
        "where a is not null and a <> ''"
    ):
        canon.setdefault(_slug(name), name)
    return canon


# Doc spellings the vocabulary lookup alone cannot resolve.
ABILITY_ALIASES = {
    "colourchange": "colorchange",
    "unburuden": "unburden",
    "compoundeyes": "compoundeyes",
}


def resolve_ability(raw, problems, context):
    text = normalize.clean_text(raw or "").strip()
    if not text or text.lower() in ("none", "-"):
        return None
    slug = ABILITY_ALIASES.get(_slug(text), _slug(text))
    canonical = ability_canon().get(slug)
    if canonical is None:
        problems.append(f"unknown ability {text!r} ({context})")
        return text
    return canonical


@lru_cache(maxsize=1)
def _species_name_to_id():
    return {
        _slug(name): int(sid)
        for sid, name in db.query_rows("select species_id, name from species")
    }


def assign_ability(changes, current_ids, key, raw_value, problems, context):
    """Assign an ability cell to every species in the block.

    Range blocks may name each member's ability parenthetically
    ('Pickup (Teddiursa) / Guts (Ursaring)'); form labels on a single
    species ('Pressure (Altered) / Levitate (Origin)') take the first
    part, matching the base form the species tables store.
    """
    text = normalize.clean_text(raw_value or "").strip()
    if "/" in text and "(" in text:
        parts = [p.strip() for p in text.split("/") if p.strip()]
        assigned = set()
        first_ability = None
        for part in parts:
            match = re.match(r"^(?P<ability>[^()]+?)\s*\((?P<label>[^()]+)\)$", part)
            if not match:
                break
            ability = resolve_ability(match.group("ability"), problems, context)
            if first_ability is None:
                first_ability = ability
            target = _species_name_to_id().get(_slug(match.group("label")))
            if target is not None and target in current_ids:
                changes[target][key] = ability
                assigned.add(target)
        for species_id in current_ids:
            if species_id not in assigned:
                changes[species_id][key] = first_ability
        if first_ability is not None:
            return
    value = resolve_ability(text, problems, context)
    for species_id in current_ids:
        changes[species_id][key] = value


def parse(text):
    """Returns (changes, problems). changes: species_id -> {ability1,
    ability2, stats: {col: value}, types: (t1, t2) | None}."""
    changes, problems = {}, []
    current_ids = []

    for raw_line in normalize.clean_text(text).splitlines():
        line = raw_line.strip()
        if not line:
            continue

        if line.startswith("#"):
            ids = [int(v) for v in HEADER_ID_PATTERN.findall(line)]
            if ids:
                if len(ids) == 2 and " - #" in line:
                    current_ids = list(range(ids[0], ids[1] + 1))
                else:
                    current_ids = ids
                for species_id in current_ids:
                    changes.setdefault(species_id, {"ability1": None, "ability2": None,
                                                    "stats": {}, "types": None})
                continue
        if not current_ids:
            continue

        label_match = re.match(r"^([A-Za-z ]+):", line)
        label = label_match.group(1).strip().lower() if label_match else None
        if label in SKIP_LABELS:
            continue

        if label == "ability one":
            assign_ability(changes, current_ids, "ability1", line.split(":", 1)[1], problems, line)
            continue
        if label == "ability two":
            assign_ability(changes, current_ids, "ability2", line.split(":", 1)[1], problems, line)
            continue

        stat = STAT_PATTERN.match(line)
        if stat:
            column = STAT_COLUMNS[stat.group("stat")]
            for species_id in current_ids:
                changes[species_id]["stats"][column] = int(stat.group("new"))
            continue

        if label == "type":
            parts = [p.strip().title() for p in line.split(":", 1)[1].split("/")]
            parts = [p for p in parts if p]
            bad = [p for p in parts if p not in VALID_TYPES]
            if bad or not parts:
                problems.append(f"unparsed type line: {line!r}")
                continue
            types = (parts[0], parts[1] if len(parts) > 1 else None)
            for species_id in current_ids:
                changes[species_id]["types"] = types
            continue

    missing_abilities = [sid for sid, c in changes.items() if not c["ability1"]]
    if missing_abilities:
        problems.append(f"{len(missing_abilities)} species blocks without Ability One (e.g. {missing_abilities[:5]})")
    return changes, problems
