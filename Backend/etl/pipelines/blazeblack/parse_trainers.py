"""Parse "Trainer Rosters.txt" -- every regular Blaze Black trainer.

Format: location sections separated by a `---` underline after the header,
then one line per trainer:

    Route 1
    ---
    PKMN Ranger Brenda: Vaporeon L52, Absol L52
    * Bianca                       <- important trainer, covered by the boss doc

A trailing ` D` on the name marks a doubles pair ("Kumi & Amy D: ...").
Location headers give placement for free; a header that fails to resolve is
reported and its trainers load unplaced (curation handles them later).
"""
import re

from ... import normalize
from . import reference

ENTRY_PATTERN = re.compile(r"^(?P<who>[^:]+):\s*(?P<party>.+)$")
MON_PATTERN = re.compile(r"^(?P<species>.+?)\s+L(?P<level>\d+)$")

# Multi-word trainer classes seen in the doc; longest match wins, remainder
# is the trainer's name.
KNOWN_CLASSES = [
    "PKMN Ranger", "PKMN Breeder", "PKMN Trainer", "Nursery Aide", "School Kid",
    "Battle Girl", "Black Belt", "Ace Trainer", "Team Plasma Grunt", "Plasma Grunt",
    "Rich Boy", "Depot Agent", "Parasol Lady", "Cyclist", "Preschooler",
    "Youngster", "Lass", "Twins", "Fisherman", "Waiter", "Waitress", "Scientist",
    "Clerk", "Nurse", "Doctor", "Hiker", "Veteran", "Backpacker", "Biker",
    "Baker", "Dancer", "Artist", "Musician", "Harlequin", "Policeman",
    "Janitor", "Gentleman", "Socialite", "Psychic", "Infielder", "Linebacker",
    "Striker", "Hoopster", "Smasher", "Swimmer", "Pilot", "Worker", "Maid",
    "Butler", "Baseball Player", "Roughneck", "Guitarist", "Motorcyclist",
]


def split_class_and_name(who):
    text = normalize.clean_text(who).strip()
    double = False
    if text.endswith(" D"):
        double = True
        text = text[:-2].strip()
    for known in sorted(KNOWN_CLASSES, key=len, reverse=True):
        if text.lower().startswith(known.lower()):
            name = text[len(known):].strip()
            return known, name or known, double
    if "&" in text:
        # A classless pair ("Kumi & Amy") is a doubles duo.
        return "Duo", text, True
    # Unknown class: treat the first word as the class.
    bits = text.split(None, 1)
    return bits[0], (bits[1] if len(bits) > 1 else bits[0]), double


def class_constant(class_label):
    return "TRAINER_CLASS_" + re.sub(r"[^A-Za-z0-9]+", "_", class_label).strip("_").upper()


def parse(text):
    """Returns (trainers, pokemon, problems)."""
    lines = normalize.clean_text(text).splitlines()
    trainers, pokemon, problems = [], [], []
    seen_names = {}
    location = None          # (id, canonical name) or None
    location_header = None

    index = 0
    while index < len(lines):
        line = lines[index].strip()
        next_line = lines[index + 1].strip() if index + 1 < len(lines) else ""
        if line and next_line.startswith("---"):
            location_header = line
            location = reference.resolve_location(line)
            if location is None:
                problems.append(f"unresolved location header: {line!r}")
            index += 2
            continue
        index += 1

        if not line or line.startswith("---") or line.startswith("*"):
            continue
        if location_header is None:
            continue
        if ":" not in line:
            continue  # wrapped prose / doc commentary
        entry = ENTRY_PATTERN.match(line)
        if not entry:
            problems.append(f"unparsed line under {location_header!r}: {line!r}")
            continue

        class_label, name, double = split_class_and_name(entry.group("who"))
        base_key = "TRAINER_BB_" + re.sub(
            r"[^A-Za-z0-9]+", "_", f"{class_label}_{name}"
        ).strip("_").upper()
        occurrence = seen_names.get(base_key, 0) + 1
        seen_names[base_key] = occurrence
        encounter_name = base_key if occurrence == 1 else f"{base_key}_{occurrence}"

        klass = class_constant(class_label)
        trainers.append({
            "encounter_name": encounter_name,
            "trainer_name": name.upper(),
            "trainer_class": klass,
            "canonical_location_id": location[0] if location else "",
            "is_rematch": "",
            "is_event": "",
            "trainer_items": "",
            "trainer_pic": reference.class_sprites().get(klass, ""),
            "trainer_double": "true" if double else "",
            "details": f"blazeblack_doc=trainer_rosters; location_header={location_header}",
            "version_group_id": reference.VERSION_GROUP_ID,
            "load_build": reference.LOAD_BUILD,
            "game_id": "",
        })

        for slot, raw_mon in enumerate(entry.group("party").split(","), start=1):
            raw_mon = raw_mon.strip().rstrip(".")
            if not raw_mon:
                continue
            mon = MON_PATTERN.match(raw_mon)
            if not mon:
                problems.append(f"unparsed party member for {encounter_name}: {raw_mon!r}")
                continue
            species = reference.resolve_species(mon.group("species"))
            if species is None:
                problems.append(f"unresolved species for {encounter_name}: {mon.group('species')!r}")
                continue
            pokemon.append({
                "encounter_name": encounter_name,
                "species_name": species,
                "lvl": int(mon.group("level")),
                "moves": "",
                "held_item": "",
                "iv": "",
                "version_group_id": reference.VERSION_GROUP_ID,
                "load_build": reference.LOAD_BUILD,
                "slot": slot,
                "ability": "",
                "ability_clean": "",
                "nature": "",
            })

    return trainers, pokemon, problems
