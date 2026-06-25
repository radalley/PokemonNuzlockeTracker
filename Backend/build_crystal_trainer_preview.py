import argparse
import csv
import json
import re
import subprocess
from collections import OrderedDict, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parent
DECOMP_ROOT = Path(r"C:\Users\radal\Lockley Game Decomps\pokecrystal-master\pokecrystal-master")
OUT_DIR = ROOT / "crystal_build4_preview"
PSQL = Path(r"C:\Program Files\PostgreSQL\18\bin\psql.exe")

VERSION_GROUP_ID = 4
LOAD_BUILD = 4
SOURCE_LABEL = "crystal"


MANUAL_MAP_TO_CANON = {
    "AzaleaGym": "Azalea Town",
    "BlackthornGym1F": "Blackthorn City",
    "BlackthornGym2F": "Blackthorn City",
    "BrunosRoom": "Victory Road",
    "BurnedTower1F": "Burned Tower",
    "BurnedTowerB1F": "Burned Tower",
    "CeladonGym": "Celadon City",
    "CeruleanGym": "Cerulean City",
    "CianwoodGym": "Cianwood City",
    "DanceTheater": "Ecruteak City",
    "DragonsDenB1F": "Dragon's Den",
    "EcruteakGym": "Ecruteak City",
    "FastShipB1F": "Vermilion City",
    "FastShipCabins_NNW_NNE_NE": "Vermilion City",
    "FastShipCabins_SE_SSE_CaptainsCabin": "Vermilion City",
    "FastShipCabins_SW_SSW_NW": "Vermilion City",
    "FuchsiaGym": "Fuschia City",
    "GoldenrodGym": "Goldenrod City",
    "GoldenrodUnderground": "Goldenrod City",
    "GoldenrodUndergroundSwitchRoomEntrances": "Goldenrod City",
    "GoldenrodUndergroundWarehouse": "Goldenrod City",
    "IndigoPlateauPokecenter1F": "Victory Road",
    "KarensRoom": "Victory Road",
    "KogasRoom": "Victory Road",
    "LancesRoom": "Victory Road",
    "MahoganyGym": "Mahogany Town",
    "MountMortar1FInside": "Mt. Mortar",
    "MountMortar2FInside": "Mt. Mortar",
    "MountMortarB1F": "Mt. Mortar",
    "MountMoon": "Mt. Moon",
    "OlivineLighthouse2F": "Olivine City",
    "OlivineLighthouse3F": "Olivine City",
    "OlivineLighthouse4F": "Olivine City",
    "OlivineLighthouse5F": "Olivine City",
    "OlivineGym": "Olivine City",
    "PewterGym": "Pewter City",
    "RadioTower1F": "Goldenrod City",
    "RadioTower2F": "Goldenrod City",
    "RadioTower3F": "Goldenrod City",
    "RadioTower4F": "Goldenrod City",
    "RadioTower5F": "Goldenrod City",
    "RuinsOfAlphOutside": "Ruins of Alph",
    "SaffronGym": "Saffron City",
    "SeafoamGym": "Seafoam Islands",
    "SilphCo1F": "Saffron City",
    "SilverCaveRoom3": "Mt. Silver",
    "SlowpokeWellB1F": "Slowpoke Well",
    "SlowpokeWellB2F": "Slowpoke Well",
    "SproutTower1F": "Sprout Tower",
    "SproutTower2F": "Sprout Tower",
    "SproutTower3F": "Sprout Tower",
    "TeamRocketBaseB1F": "Rocket Hideout",
    "TeamRocketBaseB2F": "Rocket Hideout",
    "TeamRocketBaseB3F": "Rocket Hideout",
    "TrainerHouseB1F": "Viridian City",
    "UnionCave1F": "Union Cave",
    "UnionCaveB1F": "Union Cave",
    "UnionCaveB2F": "Union Cave",
    "VermilionGym": "Vermilion City",
    "VioletGym": "Violet City",
    "ViridianGym": "Viridian City",
    "WillsRoom": "Victory Road",
    "WiseTriosRoom": "Ecruteak City",
}


def read_database_url():
    env_path = ROOT / ".env"
    if not env_path.exists():
        return None
    for line in env_path.read_text(encoding="utf-8", errors="replace").splitlines():
        match = re.match(r"\s*DATABASE_URL\s*=\s*(.+?)\s*$", line)
        if match:
            return match.group(1).strip().strip("\"'")
    return None


def psql_rows(sql):
    database_url = read_database_url()
    if not database_url:
        raise RuntimeError("DATABASE_URL was not found in Backend/.env")
    result = subprocess.run(
        [str(PSQL), database_url, "-X", "-v", "ON_ERROR_STOP=1", "-A", "-F", "\t", "-P", "pager=off", "-c", sql],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    lines = [line for line in result.stdout.splitlines() if line and not line.startswith("(")]
    if not lines:
        return []
    header = lines[0].split("\t")
    rows = []
    for line in lines[1:]:
        if line.startswith("-"):
            continue
        values = line.split("\t")
        if len(values) == len(header):
            rows.append(dict(zip(header, values)))
    return rows


def load_event_locations():
    event_rows = psql_rows(
        f"""
        select el.canonical_location_id, cl.canonical_location_name, el.sort_order
        from event_locations el
        join canon_locations cl on cl.canonical_location_id = el.canonical_location_id
        where el.version_group_id = {VERSION_GROUP_ID}
        order by el.sort_order, el.canonical_location_id
        """
    )
    canon_rows = psql_rows(
        """
        select canonical_location_id, canonical_location_name
        from canon_locations
        order by canonical_location_id
        """
    )
    event_ids = {row["canonical_location_id"] for row in event_rows}
    by_name = {}
    for row in canon_rows:
        key = row["canonical_location_name"].replace("  ", " ").lower()
        enriched = dict(row)
        enriched["in_event_locations"] = row["canonical_location_id"] in event_ids
        if key not in by_name or enriched["in_event_locations"]:
            by_name[key] = enriched
    return event_rows, by_name


def parse_trainer_constants():
    constants = (DECOMP_ROOT / "constants" / "trainer_constants.asm").read_text(encoding="utf-8", errors="replace").splitlines()
    classes = []
    ids = OrderedDict()
    current = None
    for line in constants:
        clean = line.split(";", 1)[0].strip()
        match = re.match(r"trainerclass\s+(\w+)", clean)
        if match:
            current = match.group(1)
            classes.append(current)
            ids[current] = []
            continue
        match = re.match(r"const\s+(\w+)", clean)
        if match and current and current != "TRAINER_NONE":
            ids[current].append(match.group(1))
    return [c for c in classes if c != "TRAINER_NONE"], ids


def parse_party_group_order():
    order = []
    for line in (DECOMP_ROOT / "data" / "trainers" / "party_pointers.asm").read_text(encoding="utf-8", errors="replace").splitlines():
        match = re.search(r"dw\s+([A-Za-z0-9_]+)Group", line)
        if match:
            order.append(match.group(1))
    return order


def camel_to_upper_snake(value):
    value = re.sub(r"([a-z])([A-Z])", r"\1_\2", value)
    value = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", value)
    return value.upper()


def parse_trainer_pic_map(classes):
    pics = []
    for line in (DECOMP_ROOT / "data" / "trainers" / "pic_pointers.asm").read_text(encoding="utf-8", errors="replace").splitlines():
        match = re.search(r"dba_pic\s+(\w+)Pic", line)
        if match:
            pics.append(match.group(1))
    return {
        trainer_class: f"TRAINER_PIC_{camel_to_upper_snake(pic)}"
        for trainer_class, pic in zip(classes, pics)
    }


def parse_parties(group_to_class, ids_by_class):
    lines = (DECOMP_ROOT / "data" / "trainers" / "parties.asm").read_text(encoding="utf-8", errors="replace").splitlines()
    groups = OrderedDict()
    current_group = None
    current = None
    for line_no, line in enumerate(lines, 1):
        clean = line.split(";", 1)[0].strip()
        match = re.match(r"([A-Za-z0-9_]+)Group:", clean)
        if match:
            current_group = match.group(1)
            groups[current_group] = []
            current = None
            continue
        if current_group is None:
            continue
        match = re.match(r'db\s+"([^"]*)@",\s*(TRAINERTYPE_\w+)', clean)
        if match:
            trainer_class = group_to_class[current_group]
            trainer_idx = len(groups[current_group])
            trainer_id = ids_by_class[trainer_class][trainer_idx]
            encounter_name = f"TRAINER_{trainer_class}_{trainer_id}"
            current = {
                "line": line_no,
                "encounter_name": encounter_name,
                "trainer_name": "" if match.group(1) == "?" else match.group(1),
                "trainer_class": f"TRAINER_CLASS_{trainer_class}",
                "crystal_class": trainer_class,
                "crystal_id": trainer_id,
                "party_type": match.group(2),
                "pokemon": [],
            }
            groups[current_group].append(current)
            continue
        if current and clean.startswith("db ") and not clean.startswith("db -1"):
            values = [value.strip() for value in clean[3:].split(",")]
            if len(values) >= 2 and re.match(r"\d+$", values[0]):
                mon = {
                    "lvl": int(values[0]),
                    "species_name": values[1],
                    "held_item": "",
                    "moves": "",
                }
                move_start = 2
                if "ITEM" in current["party_type"] and len(values) >= 3:
                    mon["held_item"] = "" if values[2] in ("NO_ITEM", "ITEM_NONE") else values[2]
                    move_start = 3
                if "MOVES" in current["party_type"]:
                    moves = [move for move in values[move_start:move_start + 4] if move != "NO_MOVE"]
                    mon["moves"] = ",".join(moves)
                current["pokemon"].append(mon)
    return {trainer["encounter_name"]: trainer for group in groups.values() for trainer in group}


def build_rematch_keys(parties):
    generic_names = {"", "GRUNT", "EXECUTIVE", "CAL"}
    excluded_classes = {"RIVAL1", "RIVAL2", "TWINS"}
    grouped = defaultdict(list)
    for encounter_name, party in parties.items():
        if party["crystal_class"] in excluded_classes or party["trainer_name"] in generic_names:
            continue
        base = re.sub(r"\d+$", "", party["crystal_id"])
        if not base or base == party["crystal_id"]:
            continue
        grouped[(party["crystal_class"], party["trainer_name"], base)].append((party["crystal_id"], encounter_name))

    rematches = set()
    for values in grouped.values():
        if len(values) <= 1:
            continue
        for trainer_id, encounter_name in values:
            suffix = re.search(r"(\d+)$", trainer_id)
            if suffix and int(suffix.group(1)) > 1:
                rematches.add(encounter_name)
    return rematches


def parse_map_references():
    trainer_macros = []
    loadtrainers = []
    object_trainers = []
    for path in (DECOMP_ROOT / "maps").glob("*.asm"):
        current_label = None
        for line_no, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            stripped = line.split(";", 1)[0].rstrip()
            label = re.match(r"^([A-Za-z_][A-Za-z0-9_]*):\s*$", stripped)
            if label:
                current_label = label.group(1)
            clean = stripped.strip()
            if clean.startswith("trainer "):
                args = [arg.strip() for arg in clean[len("trainer "):].split(",")]
                if len(args) >= 7:
                    trainer_macros.append({
                        "map": path.stem,
                        "file": path.name,
                        "line": line_no,
                        "label": current_label,
                        "class": args[0],
                        "id": args[1],
                        "event": args[2],
                    })
            if clean.startswith("loadtrainer "):
                args = [arg.strip() for arg in clean[len("loadtrainer "):].split(",")]
                if len(args) >= 2:
                    loadtrainers.append({
                        "map": path.stem,
                        "file": path.name,
                        "line": line_no,
                        "label": current_label,
                        "class": args[0],
                        "id": args[1],
                        "event": "",
                    })
            if clean.startswith("object_event "):
                args = [arg.strip() for arg in clean[len("object_event "):].split(",")]
                if len(args) >= 13 and args[9] == "OBJECTTYPE_TRAINER":
                    object_trainers.append({
                        "file": path.name,
                        "map": path.stem,
                        "x": args[0],
                        "y": args[1],
                        "script": args[11],
                    })
    positions = {(row["file"], row["script"]): row for row in object_trainers}
    refs = []
    for row in trainer_macros:
        position = positions.get((row["file"], row["label"]), {})
        refs.append({**row, **{"source": "trainer", "x": position.get("x", ""), "y": position.get("y", "")}})
    for row in loadtrainers:
        refs.append({**row, **{"source": "loadtrainer", "x": "", "y": ""}})
    return refs


def split_camel(name):
    name = name.replace("_", " ")
    name = re.sub(r"([a-z])([A-Z])", r"\1 \2", name)
    name = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1 \2", name)
    return re.sub(r"\s+", " ", name).strip()


def infer_location(map_name, event_by_name):
    manual = MANUAL_MAP_TO_CANON.get(map_name)
    if manual:
        row = event_by_name.get(manual.replace("  ", " ").lower())
        if row and row.get("in_event_locations"):
            return row, "manual"
        return row, "canon_not_in_event" if row else "manual_missing"

    spaced = split_camel(map_name)
    candidates = [
        spaced,
        re.sub(r"\bB\d+F\b|\b\d+F\b", "", spaced).strip(),
        re.sub(r"\bNorth\b|\bSouth\b|\bEast\b|\bWest\b", "", spaced).strip(),
    ]
    for candidate in candidates:
        row = event_by_name.get(candidate.replace("  ", " ").lower())
        if row:
            return row, "direct" if row.get("in_event_locations") else "canon_not_in_event"

    route_match = re.search(r"Route\s*(\d+)", spaced)
    if route_match:
        row = event_by_name.get(f"route {route_match.group(1)}")
        if row:
            return row, "route" if row.get("in_event_locations") else "canon_not_in_event"

    for suffix in (" City", " Town", " Cave", " Tower", " Forest", " Park", " Islands"):
        if spaced.endswith(suffix):
            row = event_by_name.get(spaced.replace("  ", " ").lower())
            if row:
                return row, "suffix" if row.get("in_event_locations") else "canon_not_in_event"

    return None, "unmapped"


def main():
    global DECOMP_ROOT, OUT_DIR, VERSION_GROUP_ID, LOAD_BUILD, SOURCE_LABEL

    parser = argparse.ArgumentParser(description="Build Gen II trainer preview CSVs from a pokecrystal-style decomp.")
    parser.add_argument("--decomp-root", default=str(DECOMP_ROOT), help="Path to the decomp root.")
    parser.add_argument("--out-dir", default=str(OUT_DIR), help="Directory for generated preview CSVs.")
    parser.add_argument("--version-group-id", type=int, default=VERSION_GROUP_ID)
    parser.add_argument("--load-build", type=int, default=LOAD_BUILD)
    parser.add_argument("--source-label", default=SOURCE_LABEL, help="Short label used in details text.")
    args = parser.parse_args()

    DECOMP_ROOT = Path(args.decomp_root)
    OUT_DIR = Path(args.out_dir)
    VERSION_GROUP_ID = args.version_group_id
    LOAD_BUILD = args.load_build
    SOURCE_LABEL = args.source_label

    event_rows, event_by_name = load_event_locations()
    classes, ids_by_class = parse_trainer_constants()
    trainer_pic_by_class = parse_trainer_pic_map(classes)
    group_order = parse_party_group_order()
    group_to_class = {group: trainer_class for group, trainer_class in zip(group_order, classes)}
    parties = parse_parties(group_to_class, ids_by_class)
    rematch_keys = build_rematch_keys(parties)
    refs = parse_map_references()

    by_encounter = {}
    ref_details = defaultdict(list)
    for ref in refs:
        encounter = f"TRAINER_{ref['class']}_{ref['id']}"
        location, method = infer_location(ref["map"], event_by_name)
        detail = {**ref, "location_method": method}
        if location:
            detail.update({
                "canonical_location_id": int(location["canonical_location_id"]),
                "canonical_location_name": location["canonical_location_name"],
            })
        else:
            detail.update({"canonical_location_id": "", "canonical_location_name": ""})
        ref_details[encounter].append(detail)
        if encounter in parties and encounter not in by_encounter:
            by_encounter[encounter] = detail

    trainer_rows = []
    pokemon_rows = []
    unmapped = []
    non_displayable = []
    for encounter_name, party in parties.items():
        ref = by_encounter.get(encounter_name)
        is_referenced = ref is not None
        is_rematch = "True" if encounter_name in rematch_keys else ""
        if ref and ref["source"] == "loadtrainer":
            is_event = "True"
        else:
            is_event = ""
        location_method = ref["location_method"] if ref else "unreferenced"
        displayable_location = ref and location_method in {"manual", "direct", "route", "suffix"}
        details = []
        if ref:
            details.append(f"{SOURCE_LABEL}_map={ref['map']}")
            details.append(f"source={ref['source']}")
            details.append(f"script_label={ref.get('label', '')}")
            details.append(f"map_line={ref['line']}")
            if ref.get("x") and ref.get("y"):
                details.append(f"object_xy={ref['x']},{ref['y']}")
            if location_method == "canon_not_in_event":
                details.append(
                    f"canonical candidate {ref['canonical_location_id']} {ref['canonical_location_name']} is not in Crystal event_locations"
                )
            elif location_method in {"manual_missing", "unmapped"}:
                details.append("no canonical event_location match in current Crystal script")
        else:
            details.append("party exists in decomp but no map trainer/loadtrainer reference was found")
        if is_rematch:
            details.append("rematch variant; base fight should drive current app display")

        row = {
            "encounter_name": encounter_name,
            "trainer_name": party["trainer_name"],
            "trainer_class": party["trainer_class"],
            "canonical_location_id": ref["canonical_location_id"] if displayable_location else "",
            "canonical_location_name": ref["canonical_location_name"] if displayable_location else "",
            "is_rematch": is_rematch,
            "is_event": is_event,
            "trainer_items": "",
            "trainer_pic": trainer_pic_by_class.get(party["crystal_class"], ""),
            "trainer_double": "",
            "details": "; ".join(detail for detail in details if detail),
            "version_group_id": VERSION_GROUP_ID,
            "load_build": LOAD_BUILD,
            "game_id": "",
            "crystal_class": party["crystal_class"],
            "crystal_id": party["crystal_id"],
            "map": ref["map"] if ref else "",
            "source": ref["source"] if ref else "",
            "map_line": ref["line"] if ref else "",
            "x": ref["x"] if ref else "",
            "y": ref["y"] if ref else "",
            "location_method": location_method,
        }
        trainer_rows.append(row)
        if not row["canonical_location_id"] and is_referenced:
            unmapped.append(row)
        if not row["canonical_location_id"] or is_rematch:
            non_displayable.append(row)
        for slot, mon in enumerate(party["pokemon"], 1):
            pokemon_rows.append({
                "encounter_name": encounter_name,
                "species_name": mon["species_name"],
                "lvl": mon["lvl"],
                "moves": mon["moves"],
                "held_item": mon["held_item"],
                "iv": 0,
                "version_group_id": VERSION_GROUP_ID,
                "load_build": LOAD_BUILD,
                "slot": slot,
            })

    OUT_DIR.mkdir(exist_ok=True)
    write_csv(OUT_DIR / "trainer_pool_preview.csv", trainer_rows)
    write_csv(OUT_DIR / "trainer_pool_displayable_preview.csv", [row for row in trainer_rows if row["canonical_location_id"] and row["is_rematch"] != "True"])
    write_csv(OUT_DIR / "trainer_pool_non_displayable_preview.csv", non_displayable)
    write_csv(OUT_DIR / "trainer_pokemon_preview.csv", pokemon_rows)
    write_csv(OUT_DIR / "unmapped_referenced_trainers.csv", unmapped)
    write_csv(OUT_DIR / "map_reference_details.csv", [item for values in ref_details.values() for item in values])
    summary = {
        "version_group_id": VERSION_GROUP_ID,
        "load_build": LOAD_BUILD,
        "event_locations": len(event_rows),
        "party_entries": len(parties),
        "pokemon_rows": len(pokemon_rows),
        "map_references": len(refs),
        "trainer_rows_with_location": sum(1 for row in trainer_rows if row["canonical_location_id"]),
        "trainer_rows_without_location": sum(1 for row in trainer_rows if not row["canonical_location_id"]),
        "displayable_non_rematch_trainers": sum(1 for row in trainer_rows if row["canonical_location_id"] and row["is_rematch"] != "True"),
        "rematch_trainers": sum(1 for row in trainer_rows if row["is_rematch"] == "True"),
        "referenced_trainers_unmapped": len(unmapped),
        "unreferenced_party_entries": sum(1 for row in trainer_rows if row["location_method"] == "unreferenced"),
        "location_methods": dict(sorted({method: sum(1 for row in trainer_rows if row["location_method"] == method) for method in {row["location_method"] for row in trainer_rows}}.items())),
    }
    (OUT_DIR / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


def write_csv(path, rows):
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    main()
