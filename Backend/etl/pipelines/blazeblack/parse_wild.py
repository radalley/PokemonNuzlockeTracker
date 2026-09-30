"""Parse "Wild Pokemon.txt" -- Blaze Black's encounter tables.

The doc is one section per location (===== rules between them), each a
title and lines of the form

    Grass, Normal: Lillipup (20%), Pidgey (20%), ...
    Surf, Special: Basculin (60%), Azumarill (30%), Feebas (10%)
    Sand: Sandile (20%), ...                      (single-label dialect)

A table may be split by floor/area marker lines ('1F', 'B1F', 'Outside',
'Inside - Room One', 'B2F, B3F, B4F, B5F') and by season, either in the
title ('Route 6 - Winter') or on a marker ('Outside (Both Areas) - Winter').
Every table keeps its (area, condition) here so a cave's floors never merge
into one 300% table. Slot lists may wrap onto a bare continuation line.

LEGENDARY/SPECIAL ENCOUNTER blocks name a species, level, location (with
an optional area and season: 'Chargestone Cave, B2F.', 'Twist Mountain,
Ice Rock Room, Winter') and, for a wild one, a slot line ('Cave, Normal,
1%.') -- those become 1% OVERLAY rows attached to the matching table. A
block with no slot line is a STATIC encounter (rate empty). A '*' footnote
after a block is kept as its note.

Method labels map onto encounter_methods.METHOD_KEYS; an unknown label is a
problem, never a silent row. After the scan every slot table must sum to
99-100% (KNOWN_RATE_SUMS lists the doc's own arithmetic slips).

Dialect quirks: 'Virizion. Level 56' (period), '/' filler lines, and two
split-game shapes: 'Reshiram (Blaze Black) | Zekrom (Volt White)' with
the level on the next line, and 'Tornadus, Level 40 (Volt White) /
Thundurus, Level 40 (Blaze Black)' inline.
"""
import re
from collections import defaultdict

import encounter_methods

from ... import normalize
from . import reference

ENCOUNTER_LINE = re.compile(r"^(?P<method>[A-Za-z ]+),\s*(?P<kind>[A-Za-z ]+):\s*(?P<slots>.+)$")
# Single-label lines ('Sand: ...', 'Shaking Grass: ...'); the slots must
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
# 'Cave, Normal, 1%.' / 'Sand, 1%' / 'Doubles Grass, 1%.'
OVERLAY_SLOT_LINE = re.compile(r"^(?P<label>[A-Za-z ,]+?),\s*(?P<rate>\d+)%\.?\s*$")
FLOOR_TOKEN = re.compile(r"\bB?\d+F\b", re.IGNORECASE)
SEASONS = ("spring", "summer", "autumn", "winter")
SEASON_WORD = re.compile(r"\b(spring|summer|autumn|winter)\b", re.IGNORECASE)

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

# (method word, kind word or None) -> canonical key. The doc's 'Special'
# is the rare spot (shaking grass, dust cloud, rippling water).
METHOD_KEYS = {
    ("grass", "normal"): "grass",
    ("grass", "doubles"): "dark-grass",
    ("doubles grass", None): "dark-grass",
    ("grass", "special"): "grass-spots",
    ("grass", "shaking"): "grass-spots",
    ("shaking grass", None): "grass-spots",
    ("rocky grass", None): "rocky-grass",
    ("cave", "normal"): "cave",
    ("cave", "special"): "cave-spots",
    ("sand", None): "sand",
    ("puddle", "normal"): "puddle",
    ("tower", "normal"): "tower",
    ("floor", None): "floor",
    ("bridge", "special"): "bridge-spots",
    ("surf", "normal"): "surf",
    ("surf", "special"): "surf-spots",
    ("fish", "normal"): "fish",
    ("fish", "special"): "fish-spots",
}
# Tables the doc itself adds up wrong: (location, area, condition, key) -> sum.
KNOWN_RATE_SUMS = {
    ("Route 12", None, None, "grass-spots"): 105,   # Emolga 95 + Sunflora 5 + Vespiquen 5
}
# Overlay locations that name a room no table lists: (location, room) -> table area.
OVERLAY_AREA_ALIASES = {
    ("Twist Mountain", "ice rock room"): "Not 1F",   # the icy depths are the non-1F floors
}
AREA_MARKER_MAX_LENGTH = 48


def method_key(label):
    """'Cave, Normal' / 'Sand' / 'Doubles Grass' -> canonical key, or None."""
    parts = [p.strip().lower() for p in label.split(",") if p.strip()]
    if not parts:
        return None
    lookup = (parts[0], parts[1]) if len(parts) > 1 else (parts[0], None)
    return METHOD_KEYS.get(lookup)


def parse_condition(text):
    """Season words in text -> 'season:spring,summer' (calendar order), or
    None for 'All Seasons' / no season words."""
    low = (text or "").lower()
    if "all seasons" in low:
        return None
    found = [season for season in SEASONS if re.search(rf"\b{season}\b", low)]
    return "season:" + ",".join(found) if found else None


def condition_seasons(condition):
    if not condition or not condition.startswith("season:"):
        return set(SEASONS)
    return set(condition[len("season:"):].split(","))


def is_season_phrase(text):
    """True when text is nothing but season words and joiners."""
    stripped = re.sub(r"all seasons", "", text or "", flags=re.IGNORECASE)
    stripped = SEASON_WORD.sub("", stripped)
    stripped = re.sub(r"[\s/,&]|\band\b", "", stripped, flags=re.IGNORECASE)
    return stripped == "" and bool(text and text.strip())


def strip_season_words(text):
    stripped = re.sub(r"all seasons", "", text or "", flags=re.IGNORECASE)
    stripped = SEASON_WORD.sub("", stripped)
    stripped = re.sub(r"\band\b", "", stripped, flags=re.IGNORECASE)
    stripped = re.sub(r"[\s/,&]+$", "", stripped)
    stripped = re.sub(r"^[\s/,&]+", "", stripped)
    return re.sub(r"\s+", " ", stripped).strip()


def clean_label(text):
    text = re.sub(r"\(both areas\)", "", text or "", flags=re.IGNORECASE)
    text = re.sub(r"\s+", " ", text).strip().rstrip(".").strip()
    return text


def split_qualifier(text):
    """A marker line or a title's ' - ' remainder -> (area, condition).

    '1F' -> ('1F', None); 'Outside (Both Areas) - Winter' -> ('Outside',
    'season:winter'); 'Inside - Room One' -> ('Inside - Room One', None);
    'All Seasons' -> (None, None); 'All Floors' -> (None, None).
    """
    text = clean_label(text)
    if not text:
        return None, None
    area, condition = text, None
    if " - " in text:
        left, right = text.split(" - ", 1)
        if is_season_phrase(right):
            area, condition = left.strip(), parse_condition(right)
    elif is_season_phrase(text):
        return None, parse_condition(text)
    if not area or area.lower() == "all floors":
        area = None
    return area, condition


def split_header(title):
    """A title line -> (resolved places, area, condition).

    'Route 6 - Winter' -> ([Route 6], None, 'season:winter');
    'Wellspring Cave 1F' -> ([Wellspring Cave], '1F', None);
    'Mistralton Cave 1F - 2F' -> ([...], '1F - 2F', None);
    'Giant Chasm - Outside Area' -> ([...], 'Outside Area', None);
    'Icirrus City, Route 8' -> (both, None, None). Unresolvable text
    yields no places.
    """
    text = clean_label(title)
    area = condition = None
    place_text = text
    if " - " in text:
        left, right = text.split(" - ", 1)
        right = right.strip()
        trailing = re.search(r"\s(B?\d+F)\s*$", left, flags=re.IGNORECASE)
        if trailing and FLOOR_TOKEN.fullmatch(right):
            place_text = left[:trailing.start()]
            area = f"{trailing.group(1)} - {right}"
        elif is_season_phrase(right):
            place_text, condition = left, parse_condition(right)
        elif right.lower() == "all floors":
            place_text = left
        else:
            place_text, area = left, right
    if area is None:
        trailing = re.search(r"\s(B?\d+F)(\s*\([^)]*\))?\s*$", place_text, flags=re.IGNORECASE)
        if trailing:
            area = re.sub(r"\s+", " ", trailing.group(0)).strip()
            place_text = place_text[:trailing.start()]
    places = []
    for part in place_text.split(","):
        spot = reference.resolve_location(part.strip()) if part.strip() else None
        if spot:
            places.append(spot)
    return places, area, condition


def expand_floors(label):
    """Floor tokens named by an area label: 'B2F, B3F, B4F, B5F' -> {B2F..B5F},
    '1F - 2F' -> {1F, 2F}, '5F (Roof)' -> {5F}."""
    if not label:
        return set()
    text = label.upper()
    ranged = re.match(r"^\s*(B?)(\d+)F\s*-\s*(B?)(\d+)F\s*$", text)
    if ranged and ranged.group(1) == ranged.group(3):
        prefix, low, high = ranged.group(1), int(ranged.group(2)), int(ranged.group(4))
        return {f"{prefix}{n}F" for n in range(min(low, high), max(low, high) + 1)}
    return {token.upper() for token in FLOOR_TOKEN.findall(text)}


def area_words(label):
    """Lowercase words of an area label minus floor tokens and filler."""
    if not label:
        return set()
    text = FLOOR_TOKEN.sub(" ", label.lower())
    return {word for word in re.findall(r"[a-z]+", text) if word not in {"both", "areas", "the"}}


def parse(text):
    """Returns (rows, problems). Rows are encounter_pool preview dicts."""
    cleaned = normalize.clean_text(text)
    rows, problems = [], []
    seen = {}                       # identity -> rate
    area_labels = defaultdict(list)  # location_id -> [area labels in doc order]
    location_tables = defaultdict(dict)  # location_id -> {(area, condition): set(keys)}
    table_sums = defaultdict(int)   # (game, loc_id, loc_name, area, condition, key) -> sum

    def area_sort_for(location, area):
        if area is None:
            return 0
        labels = area_labels[location[0]]
        if area not in labels:
            labels.append(area)
        return labels.index(area) + 1

    def canonical_area(location, token):
        """Match an overlay/static's room token to an area label this
        location already has (exact, alias, floor membership, or word
        overlap); otherwise the token becomes its own label."""
        if token is None:
            return None
        labels = area_labels[location[0]]
        low = token.lower()
        for label in labels:
            if label.lower() == low:
                return label
        alias = OVERLAY_AREA_ALIASES.get((location[1], low))
        if alias:
            return alias
        floors = expand_floors(token)
        if floors:
            for label in labels:
                if label.lower().startswith("not "):
                    continue
                if floors <= expand_floors(label):
                    return label
        words = area_words(token)
        if words:
            for label in labels:
                if words <= area_words(label):
                    return label
        return token

    def add(location, species_raw, rate, key, level=None, games=None, *,
            area=None, condition=None, slot_kind="slot", tag=None):
        species = reference.resolve_species(species_raw)
        if species is None:
            problems.append(f"unresolved wild species at {location and location[1]}: {species_raw!r}")
            return []
        area_sort = area_sort_for(location, area)
        emitted = []
        for game_id in (games or GAME_EXCLUSIVES.get(species, ALL_GAMES)):
            identity = (game_id, location[0], area, condition, species, key, slot_kind)
            if identity in seen:
                if seen[identity] != rate:
                    problems.append(
                        f"duplicate slot with a different rate at {location[1]} / {area or 'whole location'}: "
                        f"{species} {key} {seen[identity]}% vs {rate}%")
                continue
            seen[identity] = rate
            row = {
                "game_id": game_id,
                "location_id": "",
                "canonical_location_id": location[0],
                "species_id": species,  # resolved to an id by the orchestrator
                "min_level": level or "",
                "max_level": level or "",
                "method": key,
                "enounter_rate": rate if rate is not None else "",
                "area": area or "",
                "area_sort": area_sort,
                "condition": condition or "",
                "slot_kind": slot_kind,
                "tag": tag or "",
                "note": "",
            }
            rows.append(row)
            emitted.append(row)
            if slot_kind == "slot":
                location_tables[location[0]].setdefault((area, condition), set()).add(key)
                table_sums[(game_id, location[0], location[1], area, condition, key)] += rate
            elif slot_kind == "overlay" and rate is not None and rate > 5:
                problems.append(f"overlay rate above 5% at {location[1]}: {species} {rate}%")
        return emitted

    def resolve_overlay(location, token, key, condition, species=None):
        """The (area, condition) an overlay row joins: the table with the
        same method whose area matches the token and whose seasons cover
        the overlay's; the overlay keeps its own season when it has one.
        A season no table at that area covers is reported, not hidden."""
        tables = location_tables.get(location[0], {})
        area = canonical_area(location, token)
        matches = [(a, c) for (a, c), keys in tables.items() if a == area and key in keys]
        if not matches:
            matches = [(a, c) for (a, c) in tables if a == area]
        chosen = None
        if condition:
            wanted = condition_seasons(condition)
            covering = [(a, c) for a, c in matches if wanted <= condition_seasons(c)]
            chosen = covering[0] if covering else None
            if matches and not covering:
                problems.append(
                    f"overlay season no table covers at {location[1]} / {area or 'whole location'}: "
                    f"{species} {key} {condition}")
        if chosen is None:
            unconditioned = [(a, c) for a, c in matches if c is None]
            chosen = unconditioned[0] if unconditioned else (matches[0] if matches else None)
        if chosen is None:
            return area, condition
        return chosen[0], condition or chosen[1]

    # Linear scan: the doc does not reliably separate sections (there is no
    # ===== rule between the preamble and Route 1), so any resolvable title
    # line switches the current location targets. A ===== rule marks a
    # section boundary: the title right after it that fails to resolve
    # starts an UNKNOWN section (targets cleared, contents reported loudly);
    # an unresolvable short line mid-section is an area marker.
    targets = []
    current_area = None
    current_condition = None
    last_title = None
    reported_titles = set()
    pending = None          # LEGENDARY/SPECIAL state machine
    last_encounter = None   # (targets, key, area, condition) for continuation lines
    last_block_rows = []    # rows a following '*' footnote belongs to
    at_section_start = False

    def finalize(rate, key, slot_kind):
        nonlocal last_block_rows
        location = pending.get("location")
        emitted = []
        for species_raw, level, games in pending["entries"]:
            if location is None:
                problems.append(
                    f"{pending['kind']} encounter with no resolvable location: {species_raw!r}")
                continue
            token, condition = pending.get("area"), pending.get("condition")
            if slot_kind == "overlay":
                area, condition = resolve_overlay(location, token, key, condition, species_raw)
            else:
                area = canonical_area(location, token)
            emitted += add(location, species_raw, rate, key, level, games,
                           area=area, condition=condition, slot_kind=slot_kind, tag=pending["kind"])
        last_block_rows = emitted

    def split_entries(match, level_a=None, level_b=None):
        return [
            (match.group("a").strip(), level_a, [GAME_BY_NAME[match.group("ga").lower()]]),
            (match.group("b").strip(), level_b, [GAME_BY_NAME[match.group("gb").lower()]]),
        ]

    def read_block_location(line):
        """'Twist Mountain, Ice Rock Room, Winter' -> the resolved place
        (or the section's first target) plus the room token and season."""
        text = clean_label(line)
        text = re.sub(r"\s*\([^)]*\)", "", text).strip()
        parts = [p.strip() for p in text.split(",") if p.strip()]
        spot = reference.resolve_location(parts[0]) if parts else None
        remainder = parts[1:] if spot else parts
        if spot is None:
            spot = targets[0] if targets else None
        rest = ", ".join(remainder)
        return spot, (strip_season_words(rest) or None), parse_condition(rest)

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
            problems.append(f"unparsed {pending['kind']} species line: {line!r}")
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
            problems.append(f"unparsed {pending['kind']} level line: {line!r}")
            pending = None
            return False
        if stage == "location":
            spot, area, condition = read_block_location(line)
            pending.update(location=spot, area=area, condition=condition, stage="slot")
            return True
        # stage == "slot": a wild legendary names its table and rate; a
        # static encounter has no slot line at all and is reprocessed.
        slot = OVERLAY_SLOT_LINE.match(line)
        if slot:
            key = method_key(slot.group("label"))
            if key is None:
                problems.append(
                    f"unknown encounter method {slot.group('label')!r} at "
                    f"{pending.get('location') and pending['location'][1]}")
            else:
                finalize(int(slot.group("rate")), key, "overlay")
            pending = None
            return True
        finalize(None, "static", "static")
        pending = None
        return False

    def add_slots(slot_targets, key, slots_text, area, condition):
        for target in slot_targets:
            for slot in SLOT_PATTERN.finditer(slots_text):
                add(target, slot.group("species"), int(slot.group("rate")), key,
                    area=area, condition=condition)

    def unknown_method(label):
        where = ", ".join(t[1] for t in targets) or last_title
        problems.append(f"unknown encounter method {label!r} at {where}")

    for raw_line in cleaned.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if re.match(r"^=+$", line):
            at_section_start = True
            last_encounter = None
            last_block_rows = []
            continue

        if pending is not None and feed_pending(line):
            continue

        header = re.match(r"^(?P<kind>LEGENDARY|SPECIAL)\s+ENCOUNTER", line.upper())
        if header:
            pending = {"stage": "species", "entries": [], "kind": header.group("kind").lower(),
                       "location": None, "area": None, "condition": None}
            last_encounter = None
            last_block_rows = []
            continue

        if line.startswith("*"):
            note = line.lstrip("*").strip()
            for row in last_block_rows:
                row["note"] = f"{row['note']} {note}".strip()
            continue

        match = ENCOUNTER_LINE.match(line)
        if match:
            at_section_start = False
            last_block_rows = []
            if not targets:
                if last_title and last_title not in reported_titles:
                    problems.append(f"unresolved wild location header: {last_title!r}")
                    reported_titles.add(last_title)
                continue
            key = method_key(f"{match.group('method')}, {match.group('kind')}")
            if key is None:
                unknown_method(f"{match.group('method').strip()}, {match.group('kind').strip()}")
                last_encounter = None
                continue
            add_slots(targets, key, match.group("slots"), current_area, current_condition)
            last_encounter = (list(targets), key, current_area, current_condition)
            continue

        single = SINGLE_LABEL_LINE.match(line)
        if single:
            at_section_start = False
            last_block_rows = []
            if not targets:
                if last_title and last_title not in reported_titles:
                    problems.append(f"unresolved wild location header: {last_title!r}")
                    reported_titles.add(last_title)
                continue
            key = method_key(single.group("method"))
            if key is None:
                unknown_method(single.group("method").strip())
                last_encounter = None
                continue
            add_slots(targets, key, single.group("slots"), current_area, current_condition)
            last_encounter = (list(targets), key, current_area, current_condition)
            continue

        if last_encounter is not None and ":" not in line and CONTINUATION_LINE.match(line):
            add_slots(*last_encounter[:2], line, *last_encounter[2:])
            continue

        if ":" not in line:
            last_encounter = None
            places, area, condition = split_header(line)
            if places:
                targets = places
                current_area, current_condition = area, condition
                last_title = line
                at_section_start = False
                continue
            if at_section_start:
                # The title of a brand-new section failed to resolve: its
                # contents must not leak into the previous section.
                targets = []
                current_area = current_condition = None
                last_title = line
                at_section_start = False
                continue
            if targets and len(line) < AREA_MARKER_MAX_LENGTH and "%" not in line:
                # A floor/area/season marker inside a location ('B1F',
                # 'Outside (Both Areas) - Winter', 'Pot Rooms', 'All Seasons').
                current_area, current_condition = split_qualifier(line)
                continue
            if not targets and len(line) < 60:
                last_title = line

    # A block still open at the end of the doc is a static (no slot line
    # ever came); any other stage means the block was cut short.
    if pending is not None:
        if pending["stage"] == "slot":
            finalize(None, "static", "static")
        else:
            problems.append(f"{pending['kind']} encounter block cut short at end of document")
        pending = None

    def sort_key(item):
        game_id, loc_id, loc_name, area, condition, key = item[0]
        return (game_id, loc_id, loc_name, area or "", condition or "", key)

    for (game_id, loc_id, loc_name, area, condition, key), total in sorted(table_sums.items(), key=sort_key):
        expected = KNOWN_RATE_SUMS.get((loc_name, area, condition, key))
        if expected is not None and total == expected:
            continue
        if not 99 <= total <= 100:
            message = (f"table sums to {total}%: {loc_name} / {area or 'whole location'} / "
                       f"{condition or 'all seasons'} / {key}")
            if message not in problems:
                problems.append(message)

    return rows, problems
