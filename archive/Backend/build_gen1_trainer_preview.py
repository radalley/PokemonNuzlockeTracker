import argparse
import csv
import json
import re
import subprocess
from collections import OrderedDict, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parent
PSQL = Path(r"C:\Program Files\PostgreSQL\18\bin\psql.exe")


MANUAL_MAP_TO_CANON = {
    "AgathasRoom": "Victory Road",
    "BluesHouse": "Pallet Town",
    "BrunosRoom": "Victory Road",
    "CeladonGameCorner": "Celadon City",
    "CeladonGym": "Celadon City",
    "CeruleanCave1F": "Cerulean Cave",
    "CeruleanCave2F": "Cerulean Cave",
    "CeruleanCaveB1F": "Cerulean Cave",
    "CeruleanGym": "Cerulean City",
    "ChampionsRoom": "Victory Road",
    "CinnabarGym": "Cinnabar Island",
    "FightingDojo": "Saffron City",
    "FuchsiaGym": "Fuschia City",
    "GameCorner": "Celadon City",
    "IndigoPlateauLobby": "Victory Road",
    "LancesRoom": "Victory Road",
    "LoreleisRoom": "Victory Road",
    "MtMoon1F": "Mt. Moon",
    "MtMoonB1F": "Mt. Moon",
    "MtMoonB2F": "Mt. Moon",
    "OaksLab": "Pallet Town",
    "PewterGym": "Pewter City",
    "PokemonMansion1F": "Pokemon Mansion",
    "PokemonMansion2F": "Pokemon Mansion",
    "PokemonMansion3F": "Pokemon Mansion",
    "PokemonMansionB1F": "Pokemon Mansion",
    "PokemonTower1F": "Pokemon Tower",
    "PokemonTower2F": "Pokemon Tower",
    "PokemonTower3F": "Pokemon Tower",
    "PokemonTower4F": "Pokemon Tower",
    "PokemonTower5F": "Pokemon Tower",
    "PokemonTower6F": "Pokemon Tower",
    "PokemonTower7F": "Pokemon Tower",
    "RocketHideoutB1F": "Celadon City",
    "RocketHideoutB2F": "Celadon City",
    "RocketHideoutB3F": "Celadon City",
    "RocketHideoutB4F": "Celadon City",
    "RockTunnel1F": "Rock Tunnel",
    "RockTunnelB1F": "Rock Tunnel",
    "SaffronGym": "Saffron City",
    "SeafoamIslands1F": "Seafoam Islands",
    "SeafoamIslandsB1F": "Seafoam Islands",
    "SeafoamIslandsB2F": "Seafoam Islands",
    "SeafoamIslandsB3F": "Seafoam Islands",
    "SeafoamIslandsB4F": "Seafoam Islands",
    "SilphCo2F": "Saffron City",
    "SilphCo3F": "Saffron City",
    "SilphCo4F": "Saffron City",
    "SilphCo5F": "Saffron City",
    "SilphCo6F": "Saffron City",
    "SilphCo7F": "Saffron City",
    "SilphCo8F": "Saffron City",
    "SilphCo9F": "Saffron City",
    "SilphCo10F": "Saffron City",
    "SilphCo11F": "Saffron City",
    "SSAnne1FRooms": "Vermilion City",
    "SSAnne2F": "Vermilion City",
    "SSAnne2FRooms": "Vermilion City",
    "SSAnneB1FRooms": "Vermilion City",
    "SSAnneBow": "Vermilion City",
    "SSAnneCaptainsRoom": "Vermilion City",
    "SSAnneKitchen": "Vermilion City",
    "SSAnneStern": "Vermilion City",
    "VermilionGym": "Vermilion City",
    "VictoryRoad1F": "Victory Road",
    "VictoryRoad2F": "Victory Road",
    "VictoryRoad3F": "Victory Road",
    "ViridianForest": "Viridian Forest",
    "ViridianGym": "Viridian City",
}


def read_database_url():
    env_path = ROOT / ".env"
    if not env_path.exists():
        raise RuntimeError("Backend/.env not found")
    for line in env_path.read_text(encoding="utf-8", errors="replace").splitlines():
        match = re.match(r"\s*DATABASE_URL\s*=\s*(.+?)\s*$", line)
        if match:
            return match.group(1).strip().strip("\"'")
    raise RuntimeError("DATABASE_URL was not found in Backend/.env")


def psql_rows(sql):
    result = subprocess.run(
        [str(PSQL), read_database_url(), "-X", "-v", "ON_ERROR_STOP=1", "-A", "-F", "\t", "-P", "pager=off", "-c", sql],
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


def normalize_name(value):
    return re.sub(r"\s+", " ", value).strip().lower()


def load_event_locations(version_group_id):
    event_rows = psql_rows(
        f"""
        select el.canonical_location_id, cl.canonical_location_name, el.sort_order
        from event_locations el
        join canon_locations cl on cl.canonical_location_id = el.canonical_location_id
        where el.version_group_id = {version_group_id}
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
        enriched = dict(row)
        enriched["in_event_locations"] = row["canonical_location_id"] in event_ids
        key = normalize_name(row["canonical_location_name"])
        if key not in by_name or enriched["in_event_locations"]:
            by_name[key] = enriched
    return event_rows, by_name


def split_camel(name):
    name = name.replace("_", " ")
    name = re.sub(r"([a-z])([A-Z])", r"\1 \2", name)
    name = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1 \2", name)
    return re.sub(r"\s+", " ", name).strip()


def infer_location(map_name, event_by_name):
    manual = MANUAL_MAP_TO_CANON.get(map_name)
    if manual:
        row = event_by_name.get(normalize_name(manual))
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
        row = event_by_name.get(normalize_name(candidate))
        if row:
            return row, "direct" if row.get("in_event_locations") else "canon_not_in_event"

    route_match = re.search(r"Route\s*(\d+)", spaced)
    if route_match:
        row = event_by_name.get(f"route {route_match.group(1)}")
        if row:
            return row, "route" if row.get("in_event_locations") else "canon_not_in_event"

    return None, "unmapped"


def camel_to_upper_snake(value):
    value = re.sub(r"([a-z])([A-Z])", r"\1_\2", value)
    value = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", value)
    return value.upper()


def data_label_to_class(label):
    if label.endswith("Data"):
        label = label[:-4]
    return camel_to_upper_snake(label)


def parse_trainer_classes(decomp_root):
    classes = []
    for line in (decomp_root / "constants" / "trainer_constants.asm").read_text(encoding="utf-8", errors="replace").splitlines():
        clean = line.split(";", 1)[0].strip()
        match = re.match(r"trainer_const\s+(\w+)", clean)
        if match and match.group(1) != "NOBODY":
            classes.append(match.group(1))
    return classes


def parse_party_group_order(decomp_root):
    order = []
    for line in (decomp_root / "data" / "trainers" / "parties.asm").read_text(encoding="utf-8", errors="replace").splitlines():
        match = re.match(r"\s*dw\s+([A-Za-z0-9_]+Data)\s*$", line.split(";", 1)[0])
        if match:
            order.append(match.group(1))
    return order


def parse_pic_map(decomp_root, classes):
    pics = []
    for line in (decomp_root / "data" / "trainers" / "pic_pointers_money.asm").read_text(encoding="utf-8", errors="replace").splitlines():
        match = re.search(r"pic_money\s+(\w+)Pic", line)
        if match:
            pics.append(match.group(1))
    return {
        trainer_class: f"TRAINER_PIC_{camel_to_upper_snake(pic)}"
        for trainer_class, pic in zip(classes, pics)
    }


def parse_parties(decomp_root, group_to_class):
    lines = (decomp_root / "data" / "trainers" / "parties.asm").read_text(encoding="utf-8", errors="replace").splitlines()
    active_class = None
    class_index = 0
    parties = OrderedDict()
    in_pointer_table = True
    for line_no, line in enumerate(lines, 1):
        clean = line.split(";", 1)[0].strip()
        if "assert_table_length" in clean:
            in_pointer_table = False
            continue
        if in_pointer_table:
            continue
        label = re.match(r"([A-Za-z0-9_]+Data):", clean)
        if label:
            active_class = group_to_class.get(label.group(1), data_label_to_class(label.group(1)))
            class_index = 0
            continue
        if not active_class or not clean.startswith("db "):
            continue
        values = [value.strip() for value in clean[3:].split(",") if value.strip()]
        if not values:
            continue
        class_index += 1
        pokemon = []
        if values[0] == "$FF":
            pair_values = values[1:]
            for i in range(0, len(pair_values), 2):
                if i >= len(pair_values) or pair_values[i] == "0":
                    break
                if i + 1 < len(pair_values):
                    pokemon.append({"lvl": int(pair_values[i].replace("$", "0x"), 0), "species_name": pair_values[i + 1]})
        else:
            lvl = int(values[0].replace("$", "0x"), 0)
            for species in values[1:]:
                if species == "0":
                    break
                pokemon.append({"lvl": lvl, "species_name": species})
        encounter_name = f"TRAINER_{active_class}_{class_index}"
        parties[encounter_name] = {
            "encounter_name": encounter_name,
            "trainer_class_key": active_class,
            "trainer_index": class_index,
            "line": line_no,
            "pokemon": pokemon,
        }
    expected_classes = list(group_to_class.values())
    missing_groups = [group for group in expected_classes if not any(p["trainer_class_key"] == group for p in parties.values())]
    return parties, missing_groups


def parse_object_references(decomp_root):
    refs = []
    for path in (decomp_root / "data" / "maps" / "objects").glob("*.asm"):
        for line_no, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            clean = line.split(";", 1)[0].strip()
            if not clean.startswith("object_event "):
                continue
            args = [arg.strip() for arg in clean[len("object_event "):].split(",")]
            if len(args) >= 8 and args[-2].startswith("OPP_") and re.match(r"^\$?[0-9A-Fa-f]+$", args[-1]):
                refs.append({
                    "map": path.stem,
                    "file": path.name,
                    "line": line_no,
                    "source": "object_event",
                    "class": args[-2][4:],
                    "index": int(args[-1].replace("$", "0x"), 0),
                    "x": args[0],
                    "y": args[1],
                    "script_label": args[5] if len(args) > 5 else "",
                })
    return refs


def parse_script_references(decomp_root):
    refs = []
    for path in (decomp_root / "scripts").glob("*.asm"):
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        for i, line in enumerate(lines):
            match = re.search(r"ld\s+a,\s+OPP_(\w+)", line.split(";", 1)[0])
            if not match:
                continue
            trainer_class = match.group(1)
            window = [candidate.split(";", 1)[0].strip() for candidate in lines[i + 1:i + 45]]
            explicit_indexes = []
            for pos, candidate in enumerate(window):
                if re.match(r"ld\s+\[wTrainerNo\],\s+a", candidate):
                    for prev in reversed(window[:pos]):
                        idx = re.match(r"ld\s+a,\s+(\$[0-9A-Fa-f]+|\d+)", prev)
                        if idx:
                            explicit_indexes.append(int(idx.group(1).replace("$", "0x"), 0))
                            break
                table = re.match(r"db\s+STARTER\d,\s+(\d+)", candidate)
                if table:
                    explicit_indexes.append(int(table.group(1)))
            for index in sorted(set(explicit_indexes)):
                refs.append({
                    "map": path.stem,
                    "file": path.name,
                    "line": i + 1,
                    "source": "script",
                    "class": trainer_class,
                    "index": index,
                    "x": "",
                    "y": "",
                    "script_label": "",
                })
    return refs


def write_csv(path, rows):
    path.parent.mkdir(exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(description="Build Gen I trainer preview CSVs from a pokered/pokeyellow decomp.")
    parser.add_argument("--decomp-root", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--version-group-id", type=int, required=True)
    parser.add_argument("--load-build", type=int, default=4)
    parser.add_argument("--source-label", required=True)
    args = parser.parse_args()

    decomp_root = Path(args.decomp_root)
    out_dir = Path(args.out_dir)
    event_rows, event_by_name = load_event_locations(args.version_group_id)
    classes = parse_trainer_classes(decomp_root)
    group_order = parse_party_group_order(decomp_root)
    group_to_class = {group: trainer_class for group, trainer_class in zip(group_order, classes)}
    pic_by_class = parse_pic_map(decomp_root, classes)
    parties, missing_groups = parse_parties(decomp_root, group_to_class)

    refs = parse_object_references(decomp_root) + parse_script_references(decomp_root)
    ref_details = defaultdict(list)
    by_encounter = {}
    for ref in refs:
        encounter_name = f"TRAINER_{ref['class']}_{ref['index']}"
        location, method = infer_location(ref["map"], event_by_name)
        detail = {**ref, "location_method": method}
        if location:
            detail.update({
                "canonical_location_id": int(location["canonical_location_id"]),
                "canonical_location_name": location["canonical_location_name"],
            })
        else:
            detail.update({"canonical_location_id": "", "canonical_location_name": ""})
        ref_details[encounter_name].append(detail)
        if encounter_name in parties and encounter_name not in by_encounter:
            by_encounter[encounter_name] = detail

    trainer_rows = []
    pokemon_rows = []
    non_displayable = []
    unmapped = []
    for encounter_name, party in parties.items():
        ref = by_encounter.get(encounter_name)
        location_method = ref["location_method"] if ref else "unreferenced"
        displayable_location = ref and location_method in {"manual", "direct", "route"}
        details = []
        if ref:
            details.append(f"{args.source_label}_map={ref['map']}")
            details.append(f"source={ref['source']}")
            details.append(f"map_line={ref['line']}")
            if ref.get("x") and ref.get("y"):
                details.append(f"object_xy={ref['x']},{ref['y']}")
            if ref.get("script_label"):
                details.append(f"script_label={ref['script_label']}")
            if location_method == "canon_not_in_event":
                details.append(
                    f"canonical candidate {ref['canonical_location_id']} {ref['canonical_location_name']} is not in Gen I event_locations"
                )
            elif location_method in {"manual_missing", "unmapped"}:
                details.append("no canonical event_location match in current Gen I script")
        else:
            details.append("party exists in decomp but no map object/script trainer reference was found")

        trainer_pic = pic_by_class.get(party["trainer_class_key"], "")
        trainer_name = ""
        if args.version_group_id == 2 and party["trainer_class_key"] == "ROCKET" and 42 <= party["trainer_index"] <= 45:
            trainer_pic = "TRAINER_PIC_JESSIE_JAMES"
            trainer_name = "JESSIE & JAMES"
            details.append("Yellow special battle uses JessieJamesPic instead of RocketPic")

        row = {
            "encounter_name": encounter_name,
            "trainer_name": trainer_name,
            "trainer_class": f"TRAINER_CLASS_{party['trainer_class_key']}",
            "canonical_location_id": ref["canonical_location_id"] if displayable_location else "",
            "canonical_location_name": ref["canonical_location_name"] if displayable_location else "",
            "is_rematch": "",
            "is_event": "True" if ref and ref["source"] == "script" else "",
            "trainer_items": "",
            "trainer_pic": trainer_pic,
            "trainer_double": "",
            "details": "; ".join(detail for detail in details if detail),
            "version_group_id": args.version_group_id,
            "load_build": args.load_build,
            "game_id": "",
            "gen1_class": party["trainer_class_key"],
            "gen1_index": party["trainer_index"],
            "map": ref["map"] if ref else "",
            "source": ref["source"] if ref else "",
            "map_line": ref["line"] if ref else "",
            "x": ref["x"] if ref else "",
            "y": ref["y"] if ref else "",
            "location_method": location_method,
        }
        trainer_rows.append(row)
        if not row["canonical_location_id"] and ref:
            unmapped.append(row)
        if not row["canonical_location_id"]:
            non_displayable.append(row)
        for slot, mon in enumerate(party["pokemon"], 1):
            pokemon_rows.append({
                "encounter_name": encounter_name,
                "species_name": mon["species_name"],
                "lvl": mon["lvl"],
                "moves": "",
                "held_item": "",
                "iv": 0,
                "version_group_id": args.version_group_id,
                "load_build": args.load_build,
                "slot": slot,
            })

    write_csv(out_dir / "trainer_pool_preview.csv", trainer_rows)
    write_csv(out_dir / "trainer_pool_displayable_preview.csv", [row for row in trainer_rows if row["canonical_location_id"]])
    write_csv(out_dir / "trainer_pool_non_displayable_preview.csv", non_displayable)
    write_csv(out_dir / "trainer_pokemon_preview.csv", pokemon_rows)
    write_csv(out_dir / "unmapped_referenced_trainers.csv", unmapped)
    write_csv(out_dir / "map_reference_details.csv", [item for values in ref_details.values() for item in values])

    summary = {
        "version_group_id": args.version_group_id,
        "load_build": args.load_build,
        "event_locations": len(event_rows),
        "trainer_classes": len(classes),
        "party_groups": len(group_order),
        "party_entries": len(parties),
        "pokemon_rows": len(pokemon_rows),
        "map_references": len(refs),
        "trainer_rows_with_location": sum(1 for row in trainer_rows if row["canonical_location_id"]),
        "trainer_rows_without_location": sum(1 for row in trainer_rows if not row["canonical_location_id"]),
        "displayable_non_rematch_trainers": sum(1 for row in trainer_rows if row["canonical_location_id"]),
        "referenced_trainers_unmapped": len(unmapped),
        "unreferenced_party_entries": sum(1 for row in trainer_rows if row["location_method"] == "unreferenced"),
        "missing_party_groups": missing_groups,
        "location_methods": dict(sorted({
            method: sum(1 for row in trainer_rows if row["location_method"] == method)
            for method in {row["location_method"] for row in trainer_rows}
        }.items())),
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
