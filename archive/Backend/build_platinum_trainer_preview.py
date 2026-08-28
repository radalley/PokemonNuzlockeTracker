import argparse
import csv
import json
import re
import subprocess
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parent
DECOMP_ROOT = Path(r"C:\Users\radal\Lockley Game Decomps\pokeplatinum-main\pokeplatinum-main")
OUT_DIR = ROOT / "platinum_build5_preview"
PSQL = Path(r"C:\Program Files\PostgreSQL\18\bin\psql.exe")

VERSION_GROUP_ID = 9
LOAD_BUILD = 5
SOURCE_LABEL = "platinum"


MANUAL_MAP_TO_CANON = {
    "canalave_city_gym": "Canalave City",
    "celestic_town_cave": "Celestic Town",
    "distortion_world_b7f": "Distortion World",
    "eterna_city_gym": "Eterna City",
    "floaroma_meadow": "Floaroma Meadow",
    "galactic_hq_4f": "Veilstone City",
    "galactic_hq_control_room": "Veilstone City",
    "hearthome_city_dp_gym_leader_room": "Hearthome City",
    "hearthome_city_gym_leader_room": "Hearthome City",
    "lake_verity": "Lake Verity",
    "oreburgh_city_gym": "Oreburgh City",
    "pastoria_city_gym": "Pastoria City",
    "pokemon_league_aaron_room": "Pokemon League",
    "pokemon_league_bertha_room": "Pokemon League",
    "pokemon_league_champion_room": "Pokemon League",
    "pokemon_league_flint_room": "Pokemon League",
    "pokemon_league_lucian_room": "Pokemon League",
    "pokemon_league_north_pokecenter_1f": "Pokemon League",
    "route_209_gate_to_hearthome_city": "Route 209",
    "snowpoint_city_gym": "Snowpoint City",
    "spear_pillar": "Mt. Coronet",
    "sunyshore_city_gym_room_3": "Sunyshore City",
    "team_galactic_eterna_building_4f": "Eterna City",
    "valley_windworks_building": "Valley Windworks",
    "valley_windworks_outside": "Valley Windworks",
    "valor_cavern": "Valor Lakefront",
    "veilstone_city_gym": "Veilstone City",
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


def normalize(value):
    value = value.replace("é", "e").replace("É", "E")
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def load_event_locations():
    rows = psql_rows(
        f"""
        select el.canonical_location_id, cl.canonical_location_name, el.sort_order
        from event_locations el
        join canon_locations cl on cl.canonical_location_id = el.canonical_location_id
        where el.version_group_id = {VERSION_GROUP_ID}
        order by el.sort_order, el.canonical_location_id
        """
    )
    by_name = {normalize(row["canonical_location_name"]): row for row in rows}
    return rows, by_name


def trainer_constant_to_file_name(constant):
    if not constant.startswith("TRAINER_"):
        return None
    return constant.removeprefix("TRAINER_").lower() + ".json"


def strip_prefix(value, prefix):
    if not value:
        return ""
    return value.removeprefix(prefix)


def read_trainer_constants():
    constants = []
    for idx, line in enumerate((DECOMP_ROOT / "generated" / "trainers.txt").read_text(encoding="utf-8").splitlines()):
        constant = line.strip()
        if constant and constant != "TRAINER_NONE":
            constants.append((idx, constant))
    return constants


def title_from_class(class_constant):
    label = strip_prefix(class_constant, "TRAINER_CLASS_")
    return label.replace("_", " ").title()


def infer_trainer_pic(class_constant):
    label = strip_prefix(class_constant, "TRAINER_CLASS_")
    return f"TRAINER_PIC_{label}" if label else ""


def load_map_references():
    refs = defaultdict(set)
    for folder, prefix, pattern in [
        (DECOMP_ROOT / "res" / "field" / "events", "events_", "*.json"),
        (DECOMP_ROOT / "res" / "field" / "scripts", "scripts_", "*.s"),
    ]:
        for path in folder.glob(pattern):
            map_name = path.stem.removeprefix(prefix)
            text = path.read_text(encoding="utf-8", errors="replace")
            for constant in sorted(set(re.findall(r"\bTRAINER_[A-Z0-9_]+\b", text))):
                if constant not in {"TRAINER_TYPE_NONE", "TRAINER_TYPE_NORMAL"}:
                    refs[constant].add(map_name)
    return refs


def choose_location(map_names, event_by_name):
    canon_names = {normalize(row["canonical_location_name"]): row for row in event_by_name.values()}
    candidates = []
    for map_name in map_names:
        manual = MANUAL_MAP_TO_CANON.get(map_name)
        if manual:
            row = canon_names.get(normalize(manual))
            if row:
                candidates.append((1000, row, map_name))
                continue
        map_norm = normalize(map_name)
        for key, row in canon_names.items():
            if key and key in map_norm:
                candidates.append((len(key), row, map_name))
    if not candidates:
        return None, ""
    candidates.sort(key=lambda item: (-item[0], item[2]))
    return candidates[0][1], candidates[0][2]


def write_csv(path, rows, fieldnames):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def build_rows():
    event_rows, event_by_name = load_event_locations()
    map_refs = load_map_references()
    trainer_rows = []
    pokemon_rows = []
    map_reference_rows = []
    missing_json = []

    for trainer_index, constant in read_trainer_constants():
        json_name = trainer_constant_to_file_name(constant)
        json_path = DECOMP_ROOT / "res" / "trainers" / "data" / json_name
        if not json_path.exists():
            missing_json.append({"trainer_index": trainer_index, "encounter_name": constant, "json_name": json_name})
            continue

        data = json.loads(json_path.read_text(encoding="utf-8"))
        party = data.get("party") or []
        if not party:
            continue

        map_names = sorted(map_refs.get(constant, []))
        location, matched_map = choose_location(map_names, event_by_name)
        class_constant = data.get("class", "")
        is_rematch = "true" if ("_REMATCH" in constant or "_REMATCH_" in constant) else ""
        details = [
            f"{SOURCE_LABEL}_trainer_index={trainer_index}",
            f"source=res/trainers/data/{json_name}",
        ]
        if map_names:
            details.append("map_refs=" + "|".join(map_names))
        if matched_map:
            details.append(f"matched_map={matched_map}")
        if not location:
            details.append("location_unpaired=true")

        trainer_rows.append(
            {
                "encounter_name": constant,
                "trainer_name": (data.get("name") or "").upper(),
                "trainer_class": class_constant,
                "canonical_location_id": location["canonical_location_id"] if location else "",
                "is_rematch": is_rematch,
                "is_event": "",
                "trainer_items": ",".join(data.get("items") or []),
                "trainer_pic": infer_trainer_pic(class_constant),
                "trainer_double": "True" if data.get("double_battle") else "",
                "details": "; ".join(details),
                "version_group_id": VERSION_GROUP_ID,
                "load_build": LOAD_BUILD,
                "game_id": "",
            }
        )

        for slot, mon in enumerate(party, 1):
            pokemon_rows.append(
                {
                    "encounter_name": constant,
                    "species_name": strip_prefix(mon.get("species", ""), "SPECIES_"),
                    "lvl": mon.get("level", ""),
                    "moves": ",".join(strip_prefix(move, "MOVE_") for move in (mon.get("moves") or [])),
                    "held_item": mon.get("item") or "",
                    "iv": mon.get("iv_scale", ""),
                    "version_group_id": VERSION_GROUP_ID,
                    "load_build": LOAD_BUILD,
                    "slot": slot,
                }
            )

        for map_name in map_names:
            map_reference_rows.append(
                {
                    "encounter_name": constant,
                    "map_name": map_name,
                    "matched_canonical_location_id": location["canonical_location_id"] if location else "",
                    "matched_canonical_location_name": location["canonical_location_name"] if location else "",
                    "matched_map": matched_map,
                }
            )

    trainer_rows.sort(key=lambda row: int(re.search(r"trainer_index=(\d+)", row["details"]).group(1)))
    pokemon_rows.sort(key=lambda row: (row["encounter_name"], int(row["slot"])))
    return trainer_rows, pokemon_rows, map_reference_rows, missing_json, event_rows


def main():
    parser = argparse.ArgumentParser(description="Build Pokemon Platinum trainer preview CSVs.")
    parser.add_argument("--out-dir", default=str(OUT_DIR))
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    trainer_rows, pokemon_rows, map_reference_rows, missing_json, event_rows = build_rows()

    trainer_fields = [
        "encounter_name",
        "trainer_name",
        "trainer_class",
        "canonical_location_id",
        "is_rematch",
        "is_event",
        "trainer_items",
        "trainer_pic",
        "trainer_double",
        "details",
        "version_group_id",
        "load_build",
        "game_id",
    ]
    pokemon_fields = [
        "encounter_name",
        "species_name",
        "lvl",
        "moves",
        "held_item",
        "iv",
        "version_group_id",
        "load_build",
        "slot",
    ]

    write_csv(out_dir / "trainer_pool_preview.csv", trainer_rows, trainer_fields)
    write_csv(
        out_dir / "trainer_pool_displayable_preview.csv",
        [
            row
            for row in trainer_rows
            if row["canonical_location_id"] and row["is_rematch"].lower() != "true"
        ],
        trainer_fields,
    )
    write_csv(out_dir / "trainer_pokemon_preview.csv", pokemon_rows, pokemon_fields)
    write_csv(
        out_dir / "map_reference_details.csv",
        map_reference_rows,
        ["encounter_name", "map_name", "matched_canonical_location_id", "matched_canonical_location_name", "matched_map"],
    )
    write_csv(out_dir / "missing_trainer_json.csv", missing_json, ["trainer_index", "encounter_name", "json_name"])
    write_csv(out_dir / "event_locations_reference.csv", event_rows, ["canonical_location_id", "canonical_location_name", "sort_order"])

    located = sum(1 for row in trainer_rows if row["canonical_location_id"])
    displayable = sum(1 for row in trainer_rows if row["canonical_location_id"] and row["is_rematch"].lower() != "true")
    rematches = sum(1 for row in trainer_rows if row["is_rematch"].lower() == "true")
    print(f"trainer_pool_preview rows: {len(trainer_rows)}")
    print(f"trainer_pokemon_preview rows: {len(pokemon_rows)}")
    print(f"located trainer rows: {located}")
    print(f"displayable non-rematch rows: {displayable}")
    print(f"rematch rows: {rematches}")
    print(f"missing trainer JSON rows: {len(missing_json)}")
    print(f"wrote {out_dir}")


if __name__ == "__main__":
    main()
