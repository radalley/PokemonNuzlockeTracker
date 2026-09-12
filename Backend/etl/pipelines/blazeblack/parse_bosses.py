"""Parse "Important Trainer Rosters.txt" -- Blaze Black's bosses.

The doc is a sequence of fights: a header line, then one or more
tab-separated team tables. Battle Type appears after the fight header
(rivals, gyms) or after a team header (Elite Four).

Row labels come in several dialects:

    Species / Level / Item / Ability
    Ability (Regular) / Ability (Reg.) / Ability (Clean)
    Item (Reg.) / Item (Clean)
    Move #1 .. Move #4
    Move #2 (Reg) / Move #2 (Cln)
    Move #2 (Reg) Move #2 (Cln)      <- combined: cells hold "reg cln" pairs

Rival teams put three space-separated alternatives in one cell -- the
starter trio ("Snivy Oshawott Tepig") and, later, other starter-dependent
mons ("Houndoom Whimsicott Gyarados"). The starter cell's token order
defines the variant order for every conditional cell in that team.
Multi-word values in joined cells are split against the known species /
ability / move vocabularies.

Team-name variants: "X's First Team" / "X's Second Team" (Elite Four round
two) and context suffixes "- Blaze Black" / "- Volt White" (the final N
fight's game split) and "- <place>; replaces <trainer>" (post-game
replacement fights).
"""
import re
from collections import defaultdict
from functools import lru_cache

from ... import db, normalize
from . import reference

# The 's' after the apostrophe is optional: the doc writes "Ghetsis' Team".
TEAM_PATTERN = re.compile(
    r"^(?P<person>.+?)['’]s?\s+(?P<variant>First|Second|Third)?\s*Team"
    r"(?:\s*-\s*(?P<context>.+))?\s*$"
)
BATTLE_TYPE_PATTERN = re.compile(r"^Battle Type:\s*(?P<kind>\w+)", re.IGNORECASE)
LABEL_PATTERN = re.compile(
    r"^(?P<base>species|level|item|ability|move #(?P<move>\d))\s*"
    r"(?:\((?P<mode>reg\.?|regular|cln\.?|clean)\))?$"
)
COMBINED_MOVE_PATTERN = re.compile(
    r"^move #(?P<move>\d)\s*\(reg\.?\)\s*move #\d\s*\(cln\.?\)$"
)


def _slug(text):
    """Fully collapsed: 'PoisonPowder', 'Poison Powder', and 'poison-powder'
    all become 'poisonpowder'."""
    return re.sub(r"[^a-z0-9]+", "", text.lower())


# Gen-5-era names that were later renamed, keyed by collapsed slug.
MOVE_RENAMES = {
    "hijumpkick": "highjumpkick",
    "faintattack": "feintattack",
    "smellingsalt": "smellingsalts",
    "twinneedle": "twineedle",
}


@lru_cache(maxsize=1)
def move_vocabulary():
    """collapsed slug -> canonical move name."""
    vocabulary = {}
    for (name,) in db.query_rows(
        "select distinct move_name from moves where move_name is not null and move_name <> ''"
    ):
        vocabulary.setdefault(_slug(name), name)
    for old, new in MOVE_RENAMES.items():
        if new in vocabulary:
            vocabulary.setdefault(old, vocabulary[new])
    return vocabulary


def split_known(cell, count, vocabulary):
    """Split a space-joined run of `count` known names. Comparison is
    slug-based so 'Will-O-Wisp' matches regardless of stored punctuation;
    footnote asterisks ('Shell Smash*') are ignored."""
    tokens = [t.rstrip("*") for t in normalize.clean_text(cell or "").split()]
    tokens = [t for t in tokens if t]
    if not tokens:
        return None

    def backtrack(index, remaining):
        if remaining == 0:
            return [] if index == len(tokens) else None
        for take in range(1, min(4, len(tokens) - index) + 1):
            candidate = vocabulary.get(_slug(" ".join(tokens[index:index + take])))
            if candidate:
                rest = backtrack(index + take, remaining - 1)
                if rest is not None:
                    return [candidate] + rest
        return None

    return backtrack(0, count)


def split_species_cell(cell):
    """Try to split a cell into exactly 3 known species (doc alternatives)."""
    tokens = normalize.clean_text(cell or "").split()
    if len(tokens) < 3:
        return None

    def backtrack(index, taken):
        if len(taken) == 3:
            return taken if index == len(tokens) else None
        for take in (1, 2):
            if index + take > len(tokens):
                break
            candidate = reference.resolve_species(" ".join(tokens[index:index + take]))
            if candidate:
                result = backtrack(index + take, taken + [candidate])
                if result is not None:
                    return result
        return None

    return backtrack(0, [])


def normalize_label(raw):
    """Raw first cell -> ('species'|'level'|'item'|'item_clean'|'ability'|
    'ability_clean'|'move<N>'|'move<N>_clean'|'move<N>_combined') or None."""
    text = re.sub(r"\s+", " ", (raw or "").strip().lower())
    combined = COMBINED_MOVE_PATTERN.match(text)
    if combined:
        return f"move{combined.group('move')}_combined"
    match = LABEL_PATTERN.match(text)
    if not match:
        return None
    base = match.group("base")
    mode = (match.group("mode") or "").rstrip(".")
    clean = mode in ("cln", "clean")
    if base.startswith("move"):
        return f"move{match.group('move')}" + ("_clean" if clean else "")
    if base == "ability":
        return "ability_clean" if clean else "ability"
    if base == "item":
        return "item_clean" if clean else "item"
    return base


def parse_document(text):
    """Returns (fights, problems). fight: {header, battle_type, teams};
    team: {person, variant, context, battle_type, rows: [(label, cells)]}."""
    lines = normalize.clean_text(text).splitlines()
    fights, problems = [], []
    current_fight = None
    current_team = None

    for raw in lines:
        line = raw.rstrip("\n")
        stripped = line.strip()

        battle = BATTLE_TYPE_PATTERN.match(stripped)
        if battle:
            kind = battle.group("kind").lower()
            if current_team is not None and not current_team["rows"]:
                current_team["battle_type"] = kind
            elif current_fight is not None:
                current_fight["battle_type"] = kind
            continue

        team = TEAM_PATTERN.match(stripped)
        if team and "\t" not in line:
            if current_fight is None:
                problems.append(f"team without a fight header: {stripped!r}")
                continue
            current_team = {
                "person": team.group("person").strip().strip(",").upper(),
                "variant": (team.group("variant") or "").lower(),
                "context": (team.group("context") or "").strip().rstrip("."),
                "battle_type": "",
                "rows": [],
            }
            current_fight["teams"].append(current_team)
            continue

        if "\t" in line and current_team is not None:
            parts = [cell.strip() for cell in line.split("\t")]
            while parts and parts[-1] == "":
                parts.pop()
            if all(cell == "" for cell in parts):
                current_team["rows"].append((None, []))  # block break
                continue
            label = normalize_label(parts[0])
            if label:
                current_team["rows"].append((label, parts[1:]))
            elif parts[0] == "":
                current_team["rows"].append(("", parts[1:]))
            else:
                problems.append(f"unparsed table row: {line!r}")
            continue

        if stripped and not stripped.startswith("*") and "\t" not in line:
            if stripped.lower().startswith(("location:", "reward:")):
                continue
            current_team = None
            current_fight = {"header": stripped, "battle_type": "", "teams": []}
            fights.append(current_fight)

    return [f for f in fights if f["teams"]], problems


def team_blocks(team, problems):
    """Split rows into blocks; label continuation rows positionally from the
    first block's label order."""
    blocks, current = [], []
    for label, cells in team["rows"]:
        if label is None:
            if current:
                blocks.append(current)
                current = []
            continue
        current.append((label, cells))
    if current:
        blocks.append(current)
    if not blocks:
        return []

    label_order = [label for label, _ in blocks[0] if label]
    resolved = []
    for block in blocks:
        rows, position = {}, 0
        for label, cells in block:
            if not label:
                if position >= len(label_order):
                    problems.append(f"continuation row overflow in {team['person']}")
                    continue
                label = label_order[position]
            rows[label] = cells
            position += 1
        resolved.append(rows)
    return resolved


def build_team_mons(team, problems):
    """Returns mons; conditional entries are {'conditional': [mon x3]} in the
    team's variant order (defined by its starter cell)."""
    mons = []
    for rows in team_blocks(team, problems):
        species_cells = rows.get("species", [])
        for column in range(len(species_cells)):

            def cell_at(label):
                values = rows.get(label, [])
                return values[column].strip() if column < len(values) else ""

            cell = species_cells[column].strip()
            if not cell or cell == "-":
                continue

            def moves_for(split_count=None, alternative=None):
                collected = []
                for n in range(1, 5):
                    value = cell_at(f"move{n}")
                    if not value:
                        combined = cell_at(f"move{n}_combined")
                        if combined:
                            pair = split_known(combined, 2, move_vocabulary())
                            value = pair[0] if pair else combined
                    value = (value or "").rstrip("*").strip()
                    if not value or value == "-":
                        continue
                    if split_count:
                        alternatives = split_known(value, split_count, move_vocabulary())
                        if alternatives is None:
                            problems.append(
                                f"unsplittable move cell for {team['person']}: {value!r}")
                            continue
                        value = alternatives[alternative]
                    else:
                        # Canonicalize era spellings ("SmokeScreen",
                        # "PoisonPowder") so display-time resolution works.
                        canonical = move_vocabulary().get(_slug(value))
                        if canonical is None:
                            problems.append(
                                f"unknown move for {team['person']}: {value!r}")
                            continue
                        value = canonical
                    collected.append(value)
                return collected

            level = re.sub(r"\D", "", cell_at("level"))
            item = cell_at("item").strip("-").strip()

            single = reference.resolve_species(cell)
            if single:
                mons.append({
                    "species": single, "level": level, "item": item,
                    "moves": moves_for(),
                    "ability": cell_at("ability"),
                    "ability_clean": cell_at("ability_clean"),
                })
                continue

            alternatives = split_species_cell(cell)
            if alternatives is None:
                problems.append(f"unresolved boss species for {team['person']}: {cell!r}")
                continue
            regular = reference.split_abilities(cell_at("ability"), 3) or ["", "", ""]
            clean = reference.split_abilities(cell_at("ability_clean"), 3) or ["", "", ""]
            conditional = []
            for i, species in enumerate(alternatives):
                conditional.append({
                    "species": species, "level": level, "item": item,
                    "moves": moves_for(split_count=3, alternative=i),
                    "ability": regular[i], "ability_clean": clean[i],
                })
            mons.append({"conditional": conditional})
    return mons


def variant_order(mons, person, problems):
    """Player-starter order for a team's conditional alternatives, from its
    starter-trio cell and the rival mapping."""
    for mon in mons:
        if "conditional" not in mon:
            continue
        lines = [reference.STARTER_LINES.get(m["species"]) for m in mon["conditional"]]
        if all(lines):
            mapping = reference.RIVAL_STARTER_MAP.get(person)
            if mapping is None:
                problems.append(f"conditional team for unmapped person {person}")
                return None
            return [mapping[line] for line in lines]
    return None


def base_fights_by_person():
    """person -> ordered fight groups (base rows sharing title+sort)."""
    groups = defaultdict(dict)
    for row in reference.base_bosses():
        key = (row["encounter_title"], row["sort_order"])
        groups[row["trainer_name"].upper()].setdefault(key, []).append(row)
    return {
        person: [fights[key] for key in sorted(fights, key=lambda k: (float(k[1] or 0), k[0]))]
        for person, fights in groups.items()
    }
