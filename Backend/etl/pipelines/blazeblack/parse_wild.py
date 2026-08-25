"""Parse "Wild Pokemon.txt" -- Blaze Black's encounter tables.

Sections are split by ===== rules; each starts with a location header and
holds encounter lines:

    Route 1
    Grass, Normal: Lillipup (20%), Pidgey (20%), ...
    Surf, Special: Basculin (60%), Azumarill (30%), Feebas (10%)

LEGENDARY ENCOUNTER blocks name a species, level, location, and slot:

    LEGENDARY ENCOUNTER
    Darkrai, Level 70
    Challenger's Cave, B1F
    Cave, Normal, 1%.

Version exclusives (doc preamble): Blaze Black gets Zekrom and Thundurus,
Volt White gets Reshiram and Tornadus; everything else loads for both games.
"""
import re

from ... import normalize
from . import reference

ENCOUNTER_LINE = re.compile(r"^(?P<method>[A-Za-z ]+),\s*(?P<kind>[A-Za-z ]+):\s*(?P<slots>.+)$")
SLOT_PATTERN = re.compile(r"(?P<species>[^,()]+?)\s*\((?P<rate>\d+)%\)")
LEGENDARY_SPECIES = re.compile(r"^(?P<species>[^,]+),\s*Level\s*(?P<level>\d+)", re.IGNORECASE)

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
    sections = re.split(r"^=+\s*$", cleaned, flags=re.MULTILINE)
    rows, problems = [], []
    seen = set()

    def add(location, species_raw, rate, method_label, level=None):
        species = reference.resolve_species(species_raw)
        if species is None:
            problems.append(f"unresolved wild species at {location and location[1]}: {species_raw!r}")
            return
        for game_id in GAME_EXCLUSIVES.get(species, ALL_GAMES):
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
    # line switches the current location targets.
    targets = []
    last_title = None
    reported_titles = set()
    pending_legendary = None

    for raw_line in cleaned.splitlines():
        line = raw_line.strip()
        if not line or re.match(r"^=+$", line):
            continue

        if line.upper().startswith("LEGENDARY ENCOUNTER"):
            pending_legendary = {"stage": "species"}
            continue
        if pending_legendary is not None:
            if pending_legendary["stage"] == "species":
                match = LEGENDARY_SPECIES.match(line)
                if match:
                    pending_legendary.update(
                        species=match.group("species").strip(),
                        level=match.group("level"), stage="location",
                    )
                continue
            if pending_legendary["stage"] == "location":
                spot = reference.resolve_location(strip_floor(line))
                pending_legendary["location"] = spot or (targets[0] if targets else None)
                pending_legendary["stage"] = "slot"
                continue
            if pending_legendary["stage"] == "slot":
                rate = re.search(r"(\d+)%", line)
                target = pending_legendary.get("location")
                if target is not None:
                    add(target, pending_legendary["species"],
                        int(rate.group(1)) if rate else 1,
                        "legendary", pending_legendary.get("level"))
                else:
                    problems.append(
                        f"legendary with no resolvable location: {pending_legendary.get('species')!r}"
                    )
                pending_legendary = None
                continue

        match = ENCOUNTER_LINE.match(line)
        if match:
            if not targets:
                if last_title and last_title not in reported_titles:
                    problems.append(f"unresolved wild location header: {last_title!r}")
                    reported_titles.add(last_title)
                continue
            method_label = f"{match.group('method').strip().lower()}-{match.group('kind').strip().lower()}"
            for target in targets:
                for slot in SLOT_PATTERN.finditer(match.group("slots")):
                    add(target, slot.group("species"), int(slot.group("rate")), method_label)
            continue

        if ":" not in line:
            # A pure floor/area marker ('B2F', '1F - 2F', 'Outside') stays
            # within the current location rather than resetting it.
            if re.match(r"^(B?\d+F(\s*-\s*B?\d+F)?|Outside|Inside|Entrance|Summit|Depths)\s*$",
                        line, flags=re.IGNORECASE):
                continue
            resolved = [reference.resolve_location(name) for name in header_locations(line)]
            found = [r for r in resolved if r is not None]
            if found:
                targets = found
                last_title = line
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
