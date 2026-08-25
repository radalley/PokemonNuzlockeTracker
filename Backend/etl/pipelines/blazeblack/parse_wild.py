"""Parse "Wild Pokemon.txt" -- Blaze Black's encounter tables.

Sections are split by ===== rules; each starts with a location header and
holds encounter lines:

    Route 1
    Grass, Normal: Lillipup (20%), Pidgey (20%), ...
    Surf, Special: Basculin (60%), Azumarill (30%), Feebas (10%)

Deserts and special grass use a single label ('Sand:', 'Shaking Grass:'),
and long slot lists wrap onto a bare continuation line:

    Grass, Normal: Golduck (20%), Bisharp (20%), ..., Gligar (10%),
    Marowak (10%), Purugly (10%), Skuntank (10%)

LEGENDARY/SPECIAL ENCOUNTER blocks name a species, level, location, and an
optional slot line (absent for static overworld encounters):

    LEGENDARY ENCOUNTER
    Darkrai, Level 70
    Challenger's Cave, B1F
    Cave, Normal, 1%.

Dialect quirks: 'Virizion. Level 56' (period), '/' filler lines, and two
split-game formats -- 'Reshiram (Blaze Black) | Zekrom (Volt White)' with
the level on the next line, and 'Tornadus, Level 40 (Volt White) /
Thundurus, Level 40 (Blaze Black)' inline.

Version exclusives (doc preamble): Blaze Black gets Zekrom and Thundurus,
Volt White gets Reshiram and Tornadus; everything else loads for both games.
A section whose header does not resolve (N's Castle) reports its contents
loudly rather than attributing them to the previous section.
"""
import re

from ... import normalize
from . import reference

ENCOUNTER_LINE = re.compile(r"^(?P<method>[A-Za-z ]+),\s*(?P<kind>[A-Za-z ]+):\s*(?P<slots>.+)$")
# 'Sand: ...', 'Shaking Grass: ...' -- one label, no kind. The slots must
# carry a (N%) so prose with a colon can never match.
SINGLE_LABEL_LINE = re.compile(r"^(?P<method>[A-Za-z ]+):\s*(?P<slots>.*\(\d+%\).*)$")
# A wrapped slot list: nothing but 'Species (N%)' items and separators.
CONTINUATION_LINE = re.compile(r"^(?:[^,:()]+\(\d+%\)\s*,?\s*)+$")
SLOT_PATTERN = re.compile(r"(?P<species>[^,()]+?)\s*\((?P<rate>\d+)%\)")
LEGENDARY_SPECIES = re.compile(r"^(?P<species>[^,.]+)[.,]\s*Level\s*(?P<level>\d+)\s*$", re.IGNORECASE)
# 'Tornadus, Level 40 (Volt White) / Thundurus, Level 40 (Blaze Black)'
SPLIT_INLINE = re.compile(
    r"^(?P<a>[^,]+),\s*Level\s*(?P<la>\d+)\s*\((?P<ga>Blaze Black|Volt White)\)\s*/\s*"
    r"(?P<b>[^,]+),\s*Level\s*(?P<lb>\d+)\s*\((?P<gb>Blaze Black|Volt White)\)$",
    re.IGNORECASE)
# 'Reshiram (Blaze Black) | Zekrom (Volt White)' -- level on the next line.
SPLIT_PIPE = re.compile(
    r"^(?P<a>[^(|]+)\((?P<ga>Blaze Black|Volt White)\)\s*\|\s*(?P<b>[^(|]+)\((?P<gb>Blaze Black|Volt White)\)$",
    re.IGNORECASE)
LEVEL_ONLY = re.compile(r"^Level\s*(?P<level>\d+)$", re.IGNORECASE)

GAME_BY_NAME = {
    "blaze black": reference.BLAZE_BLACK_GAME_ID,
    "volt white": reference.VOLT_WHITE_GAME_ID,
}
GAME_EXCLUSIVES = {
    "ZEKROM": [reference.BLAZE_BLACK_GAME_ID],
    "THUNDURUS": [reference.BLAZE_BLACK_GAME_ID],
    "RESHIRAM": [reference.VOLT_WHITE_GAME_ID],
    "TORNADUS": [reference.VOLT_WHITE_GAME_ID],
}
ALL_GAMES = [reference.BLAZE_BLACK_GAME_ID, reference.VOLT_WHITE_GAME_ID]


def strip_floor(header):
    """Reduce a header to its place name: drop floor designators and
    qualifier suffixes ('Route 6 - Spring / Summer / Autumn',
    "Challenger's Cave - All Floors", 'Mistralton Cave 1F - 2F')."""
    text = header.strip().split(" - ")[0].strip()
    return re.sub(r",?\s*(B?\d+F|\d+F|B\d+)\s*$", "", text, flags=re.IGNORECASE).strip()


def header_locations(header):
    """A header may name several places ('Icirrus City, Route 8')."""
    text = header.strip()
    if re.search(r",\s*(B?\d+F|\d+F)\s*$", text, flags=re.IGNORECASE):
        return [strip_floor(text)]
    return [strip_floor(part) for part in text.split(",") if part.strip()]


def parse(text):
    """Returns (rows, problems). Rows are encounter_pool preview dicts."""
    cleaned = normalize.clean_text(text)
    rows, problems = [], []
    seen = set()

    def add(location, species_raw, rate, method_label, level=None, games=None):
        species = reference.resolve_species(species_raw)
        if species is None:
            problems.append(f"unresolved wild species at {location and location[1]}: {species_raw!r}")
            return
        for game_id in (games or GAME_EXCLUSIVES.get(species, ALL_GAMES)):
            identity = (game_id, location[0], species, method_label)
            if identity in seen:
                continue
            seen.add(identity)
            rows.append({
                "game_id": game_id,
                "location_id": "",
                "canonical_location_id": location[0],
                "species_id": species,  # resolved to an id by the orchestrator
                "min_level": level or "",
                "max_level": level or "",
                "method": method_label,
                "enounter_rate": rate,
            })

    # Linear scan: the doc does not reliably separate sections (there is no
    # ===== rule between the preamble and Route 1), so any resolvable title
    # line switches the current location targets. A ===== rule marks a
    # section boundary: the title right after it that fails to resolve
    # starts an UNKNOWN section (targets cleared, contents reported loudly);
    # an unresolvable title mid-section is a sub-area of the current one.
    targets = []
    last_title = None
    reported_titles = set()
    pending = None          # LEGENDARY/SPECIAL state machine
    last_encounter = None   # (targets, method_label) for continuation lines
    at_section_start = False

    def finalize(rate):
        target = pending.get("location")
        for species_raw, level, games in pending["entries"]:
            if target is not None:
                add(target, species_raw, rate, pending["method"], level, games)
            else:
                problems.append(
                    f"{pending['method']} encounter with no resolvable location: {species_raw!r}")

    def split_entries(match, level_a=None, level_b=None):
        return [
            (match.group("a").strip(), level_a, [GAME_BY_NAME[match.group("ga").lower()]]),
            (match.group("b").strip(), level_b, [GAME_BY_NAME[match.group("gb").lower()]]),
        ]

    def feed_pending(line):
        """Advance the encounter-block machine. Returns True if the line
        was consumed; on False the machine is done and the line must be
        reprocessed as a normal line."""
        nonlocal pending
        stage = pending["stage"]
        if stage == "species":
            if re.fullmatch(r"/+", line):
                return True  # decorative filler between header and species
            inline = SPLIT_INLINE.match(line)
            if inline:
                pending.update(entries=split_entries(
                    inline, inline.group("la"), inline.group("lb")), stage="location")
                return True
            pipe = SPLIT_PIPE.match(line)
            if pipe:
                pending.update(entries=split_entries(pipe), stage="level")
                return True
            single = LEGENDARY_SPECIES.match(line)
            if single:
                pending.update(
                    entries=[(single.group("species").strip(), single.group("level"), None)],
                    stage="location")
                return True
            problems.append(f"unparsed {pending['method']} species line: {line!r}")
            pending = None
            return False
        if stage == "level":
            level = LEVEL_ONLY.match(line)
            if level:
                pending["entries"] = [
                    (species, level.group("level"), games)
                    for species, _, games in pending["entries"]]
                pending["stage"] = "location"
                return True
            problems.append(f"unparsed {pending['method']} level line: {line!r}")
            pending = None
            return False
        if stage == "location":
            spot = reference.resolve_location(strip_floor(line))
            if spot is None and "," in line:
                spot = reference.resolve_location(strip_floor(line.split(",")[0]))
            pending["location"] = spot or (targets[0] if targets else None)
            pending["stage"] = "slot"
            return True
        # stage == "slot": a static encounter has no slot line at all --
        # anything without a rate finalizes at 1% and is reprocessed.
        if "%" in line:
            rate = re.search(r"(\d+)%", line)
            finalize(int(rate.group(1)) if rate else 1)
            pending = None
            return True
        finalize(1)
        pending = None
        return False

    def add_slots(slot_targets, method_label, slots_text):
        for target in slot_targets:
            for slot in SLOT_PATTERN.finditer(slots_text):
                add(target, slot.group("species"), int(slot.group("rate")), method_label)

    for raw_line in cleaned.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if re.match(r"^=+$", line):
            at_section_start = True
            last_encounter = None
            continue

        if pending is not None and feed_pending(line):
            continue

        header = re.match(r"^(?P<kind>LEGENDARY|SPECIAL)\s+ENCOUNTER", line.upper())
        if header:
            pending = {"stage": "species", "entries": [],
                       "method": header.group("kind").lower()}
            last_encounter = None
            continue

        if line.startswith("*"):
            continue  # footnote prose

        match = ENCOUNTER_LINE.match(line)
        if match:
            at_section_start = False
            if not targets:
                if last_title and last_title not in reported_titles:
                    problems.append(f"unresolved wild location header: {last_title!r}")
                    reported_titles.add(last_title)
                continue
            method_label = f"{match.group('method').strip().lower()}-{match.group('kind').strip().lower()}"
            add_slots(targets, method_label, match.group("slots"))
            last_encounter = (list(targets), method_label)
            continue

        single = SINGLE_LABEL_LINE.match(line)
        if single:
            at_section_start = False
            if not targets:
                if last_title and last_title not in reported_titles:
                    problems.append(f"unresolved wild location header: {last_title!r}")
                    reported_titles.add(last_title)
                continue
            method_label = f"{single.group('method').strip().lower()}-normal"
            add_slots(targets, method_label, single.group("slots"))
            last_encounter = (list(targets), method_label)
            continue

        if last_encounter is not None and ":" not in line and CONTINUATION_LINE.match(line):
            add_slots(last_encounter[0], last_encounter[1], line)
            continue

        if ":" not in line:
            last_encounter = None
            # A pure floor/area marker ('B2F', '1F - 2F', 'Outside') stays
            # within the current location rather than resetting it.
            if re.match(r"^(B?\d+F(\s*-\s*B?\d+F)?|Outside|Inside|Entrance|Summit|Depths|Main)\s*$",
                        line, flags=re.IGNORECASE):
                continue
            resolved = [reference.resolve_location(name) for name in header_locations(line)]
            found = [r for r in resolved if r is not None]
            if found:
                targets = found
                last_title = line
                at_section_start = False
            elif at_section_start:
                # The title of a brand-new section failed to resolve: its
                # contents must not leak into the previous section.
                targets = []
                last_title = line
                at_section_start = False
            elif targets:
                # Every top-level location header in the doc resolves, so an
                # unresolvable title while inside a location is a sub-area
                # ('Pot Rooms', 'Inside - Room One'); its encounters belong
                # to the current location.
                continue
            elif len(line) < 60:
                targets = []
                last_title = line

    return rows, problems
