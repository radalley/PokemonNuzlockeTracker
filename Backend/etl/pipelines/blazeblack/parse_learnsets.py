"""Parse "Level Up Move Changes.txt" -- learnset deltas and move rebalances.

The doc opens with prose move rebalances:

    Rock Slide is now 80 power and 95% accurate.
    Fire, Water and Grass Pledge are now 100 power.

then learnset DELTAS against vanilla Black/White, grouped per species or per
evolution family (the header lists every member):

    #041 Zubat, #042 Golbat, #169 Crobat
    + Level 1 - Flail (Zubat)               restricted to named members
    = Level 16 - Wing Attack                all members, one level
    + Level 49 / 63 / 63 - Nasty Plot       one level per member, in order
    +/= Level 1 - Metronome (Cleffa, ...)   op decided per member (auto)
    + Nature Power between A and B, Level 20 (Sunkern)   positional prose

Dialect quirks: reversed "+ Belly Drum - Level 50", "(X only)" suffixes,
footnote asterisks. The parser expands everything into per-species
(op, level, move) deltas -- op '+' add, '-' replace-at-level, '=' shift,
'auto' shift-if-known-else-add. Materialization happens in the build step.
"""
import re

from ... import normalize

HEADER_ID_PATTERN = re.compile(r"#(?P<id>\d{3})\s*(?P<name>[^,#]*)")
OPS_PATTERN = re.compile(r"^(?P<ops>[+=-](?:\s*/\s*[+=-])*)\s*(?P<rest>.+)$")
LEVEL_FIRST = re.compile(r"^Level\s*(?P<levels>\d+(?:\s*/\s*\d+)*)\s*-\s*(?P<move>.+)$")
MOVE_FIRST = re.compile(r"^(?P<move>.+?)\s*-\s*Level\s*(?P<levels>\d+(?:\s*/\s*\d+)*)$")
BETWEEN = re.compile(r"^(?P<move>.+?)\s+between\s+.+?,?\s*Level\s*(?P<levels>\d+)$", re.IGNORECASE)
POWER_PATTERN = re.compile(r"(\d+)\s+power", re.IGNORECASE)
ACCURACY_PATTERN = re.compile(r"(\d+)%\s*(?:accuracy|accurate|accuarcy)", re.IGNORECASE)
TYPE_PATTERN = re.compile(r"([A-Za-z]+)-type", re.IGNORECASE)


def _slug(text):
    return re.sub(r"[^a-z0-9]+", "", (text or "").lower())


def parse(text):
    """Returns (move_changes, learnset_deltas, problems).

    move_changes: [{name, power?, accuracy?, type?}]
    learnset_deltas: species_id -> [(op, level, move_name)] with op in +-=auto
    """
    move_changes, problems = [], []
    deltas = {}
    header = []            # [(species_id, name)] of the current block
    in_species_section = False

    def add_delta(species_id, op, level, move):
        deltas.setdefault(species_id, []).append((op, level, move))

    # The elemental-monkey block restructures "the first forms" only: its
    # op-less slash lines carry one move per BASE form, while the evolved
    # forms keep their vanilla sets plus any op-ful deltas.
    MONKEY_HEADER = (511, 512, 513, 514, 515, 516)
    opless_targets = None  # subset of the header the op-less lines apply to

    for raw_line in normalize.clean_text(text).splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("Key"):
            in_species_section = True
            continue

        if line.startswith("#"):
            members = [(int(m.group("id")), m.group("name").strip())
                       for m in HEADER_ID_PATTERN.finditer(line)]
            if members:
                in_species_section = True
                header = members
                opless_targets = None
                for species_id, _ in members:
                    deltas.setdefault(species_id, [])
                continue

        if not in_species_section:
            match = re.match(r"^(?P<names>.+?)\s+(?:is|are)\s+now\s+(?P<rest>.+)$", line)
            if not match:
                continue
            names_text, rest = match.group("names").strip(), match.group("rest")
            power = POWER_PATTERN.search(rest)
            accuracy = ACCURACY_PATTERN.search(rest)
            type_match = TYPE_PATTERN.search(rest)
            if not (power or accuracy or type_match):
                continue
            if re.search(r",| and ", names_text):
                bits = re.split(r",\s*|\s+and\s+", names_text)
                suffix = bits[-1].split()[-1] if len(bits[-1].split()) > 1 else ""
                names = [b.strip() if b.strip().endswith(suffix) or not suffix
                         else f"{b.strip()} {suffix}" for b in bits if b.strip()]
            else:
                names = [names_text]
            for name in names:
                move_changes.append({
                    "name": name,
                    "power": int(power.group(1)) if power else None,
                    "accuracy": int(accuracy.group(1)) if accuracy else None,
                    "type": type_match.group(1).title() if type_match else None,
                })
            continue

        if " means " in line:
            continue  # the Key legend

        # A block prose-marked "completely redone" (the Eevee family) or
        # "restructure" (the elemental monkeys' first forms) lists a FULL
        # new learnset for the affected members: reset them and treat
        # op-less "Level X - Move" lines as entries.
        if header and ("completely redone" in line.lower() or "restructure" in line.lower()):
            header_ids = tuple(sid for sid, _ in header)
            if header_ids == MONKEY_HEADER and "first forms" in line.lower():
                opless_targets = [511, 513, 515]
            else:
                opless_targets = [sid for sid, _ in header]
            for species_id in opless_targets:
                add_delta(species_id, "reset", 0, "")
            continue
        # The monkey block later pivots to the evolved trio (additions onto
        # vanilla, no reset).
        if header and tuple(sid for sid, _ in header) == MONKEY_HEADER \
                and "second evolutions" in line.lower():
            opless_targets = [512, 514, 516]
            continue

        ops_match = OPS_PATTERN.match(line)
        opless = re.match(r"^Level\s*\d", line)
        if not ops_match and not opless:
            continue
        if not header:
            problems.append(f"delta before any species header: {line!r}")
            continue

        if ops_match:
            ops = [o.strip() for o in ops_match.group("ops").split("/")]
            op = ops[0] if len(ops) == 1 else "auto"
            rest = ops_match.group("rest").strip().rstrip(".")
        else:
            op = "="
            rest = line.strip().rstrip(".")

        # Trailing "(Zubat)", "(Cleffa only)", "[Braviary]" restricts
        # members; other parentheticals ("(Same for all eight.)") are prose
        # and dropped.
        members = None
        paren = re.search(r"[\(\[](?P<only>[^()\[\]]*)[\)\]]\s*$", rest)
        if paren:
            names = re.split(r",\s*|\s+and\s+", paren.group("only"))
            names = [re.sub(r"\bonly\b", "", n, flags=re.IGNORECASE).strip() for n in names]
            resolved = [sid for sid, name in header if _slug(name) in {_slug(n) for n in names if n}]
            if resolved:
                members = resolved
            rest = rest[:paren.start()].strip()

        delta = LEVEL_FIRST.match(rest) or MOVE_FIRST.match(rest) or BETWEEN.match(rest)
        if not delta:
            problems.append(f"unparsed delta for #{header[0][0]:03d}: {line!r}")
            continue
        levels = [int(v) for v in re.split(r"\s*/\s*", delta.group("levels"))]
        move_cell = delta.group("move").strip().rstrip("*").strip()
        moves = [m.strip().rstrip("*").strip() for m in re.split(r"\s*/\s*", move_cell)]

        if members is not None:
            targets = members
        elif opless_targets is not None:
            # Inside a restructure block every unrestricted line -- op-less
            # or op-ful -- addresses the block's current target subset.
            targets = opless_targets
        else:
            targets = [sid for sid, _ in header]

        if len(moves) > 1:
            # One move per targeted member ("Yawn / Water Pulse / ..."); a
            # "Nothing" entry skips that member.
            member_order = [sid for sid, _ in header if sid in targets]
            if len(moves) != len(member_order) or len(levels) != 1:
                problems.append(f"move count mismatch for #{header[0][0]:03d}: {line!r}")
                continue
            for species_id, move in zip(member_order, moves):
                if move.lower() not in ("nothing", "none", "-"):
                    add_delta(species_id, op, levels[0], move)
            continue

        # 'Reflect, Light Screen' is a comma pair: both moves at that level.
        comma_moves = [m.strip() for m in moves[0].split(",") if m.strip()]
        if len(levels) == 1:
            for species_id in targets:
                for move in comma_moves:
                    add_delta(species_id, op, levels[0], move)
        elif len(levels) == len(targets):
            # One level per targeted member, in header order.
            ordered_targets = [sid for sid, _ in header if sid in targets]
            for species_id, level in zip(ordered_targets, levels):
                add_delta(species_id, op, level, moves[0])
        else:
            problems.append(
                f"level count mismatch for #{header[0][0]:03d}: {line!r} "
                f"({len(levels)} levels, {len(targets)} targets)")

    return move_changes, {sid: d for sid, d in deltas.items() if d}, problems
