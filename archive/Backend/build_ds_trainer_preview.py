import argparse
import csv
import json
import re
import subprocess
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parent
PSQL = Path(r"C:\Program Files\PostgreSQL\18\bin\psql.exe")

CONFIG = {
    "diamondpearl": {
        "decomp_root": Path(r"C:\Users\radal\Lockley Game Decomps\pokediamond-master\pokediamond-master"),
        "trainer_json": Path("files/poketool/trainer/trdata.json"),
        "trainer_array_key": "trdata",
        "constants": Path("include/constants/trainers.h"),
        "version_group_id": 8,
        "load_build": 5,
        "out_dir": ROOT / "diamondpearl_build5_preview",
        "class_prefix": "TRAINER_CLASS_",
    },
    "heartgoldsoulsilver": {
        "decomp_root": Path(r"C:\Users\radal\Lockley Game Decomps\pokeheartgold-master\pokeheartgold-master"),
        "trainer_json": Path("files/poketool/trainer/trainers.json"),
        "trainer_array_key": "trainers",
        "constants": Path("include/constants/trainers.h"),
        "version_group_id": 10,
        "load_build": 5,
        "out_dir": ROOT / "heartgoldsoulsilver_build5_preview",
        "class_prefix": "TRAINERCLASS_",
    },
}

MANUAL_MAP_TO_CANON = {
    "diamondpearl": {
        "route_209_gate_to_hearthome_city": "Route 209",
        "pokemon_league_north_pokecenter_1f": "Pokemon League",
        "pokemon_league_aaron_room": "Pokemon League",
        "pokemon_league_bertha_room": "Pokemon League",
        "pokemon_league_flint_room": "Pokemon League",
        "pokemon_league_lucian_room": "Pokemon League",
        "pokemon_league_champion_room": "Pokemon League",
        "oreburgh_city_gym": "Oreburgh City",
        "eterna_city_gym": "Eterna City",
        "hearthome_city_gym_leader_room": "Hearthome City",
        "veilstone_city_gym": "Veilstone City",
        "pastoria_city_gym": "Pastoria City",
        "canalave_city_gym": "Canalave City",
        "snowpoint_city_gym": "Snowpoint City",
        "sunyshore_city_gym_room_3": "Sunyshore City",
        "galactic_hq_4f": "Veilstone City",
        "galactic_hq_control_room": "Veilstone City",
        "team_galactic_eterna_building_4f": "Eterna City",
        "valley_windworks_building": "Valley Windworks",
        "valor_cavern": "Valor Lakefront",
        "lake_verity": "Lake Verity",
        "spear_pillar": "Mt. Coronet",
    },
    "heartgoldsoulsilver": {
        "violet_gym": "Violet City",
        "azalea_gym": "Azalea Town",
        "goldenrod_gym": "Goldenrod City",
        "ecruteak_gym": "Ecruteak City",
        "cianwood_gym": "Cianwood City",
        "olivine_gym": "Olivine City",
        "mahogany_gym": "Mahogany Town",
        "blackthorn_gym": "Blackthorn City",
        "indigo_plateau_pokecenter_1f": "Victory Road",
        "wills_room": "Victory Road",
        "kogas_room": "Victory Road",
        "brunos_room": "Victory Road",
        "karens_room": "Victory Road",
        "lances_room": "Victory Road",
        "radio_tower": "Goldenrod City",
        "rocket_hideout": "Rocket Hideout",
        "team_rocket_base": "Rocket Hideout",
        "slowpoke_well": "Slowpoke Well",
        "burned_tower": "Burned Tower",
        "sprout_tower": "Sprout Tower",
        "ilex_forest": "Ilex Forest",
        "mt_moon": "Mt. Moon",
        "mount_moon": "Mt. Moon",
        "mt_silver": "Mt. Silver",
        "mount_silver": "Mt. Silver",
        "vermilion_gym": "Vermilion City",
        "saffron_gym": "Saffron City",
        "celadon_gym": "Celadon City",
        "cerulean_gym": "Cerulean City",
        "fuchsia_gym": "Fuchsia City",
        "pewter_gym": "Pewter City",
        "seafoam_gym": "Seafoam Islands",
        "viridian_gym": "Viridian City",
    },
}

PIC_ALIASES = {
    "PKMN_TRAINER_BARRY": "RIVAL",
    "RIVAL": "RIVAL",
    "CHAMPION": "CHAMPION_CYNTHIA",
    "GALACTIC": "GALACTIC_GRUNT_MALE",
    "GALACTIC_F": "GALACTIC_GRUNT_FEMALE",
    "PKMN_TRAINER_CHERYL": "TRAINER_CHERYL",
    "PKMN_TRAINER_RILEY": "TRAINER_RILEY",
    "PKMN_TRAINER_MARLEY": "TRAINER_MARLEY",
    "PKMN_TRAINER_BUCK": "TRAINER_BUCK",
    "PKMN_TRAINER_MIRA": "TRAINER_MIRA",
    "PKMN_TRAINER_LUCAS": "DP_PLAYER_MALE",
    "PKMN_TRAINER_DAWN": "DP_PLAYER_FEMALE",
    "PKMN_BREEDER_M": "BREEDER_MALE",
    "PKMN_BREEDER_F": "BREEDER_FEMALE",
    "PKMN_RANGER_M": "RANGER_MALE",
    "PKMN_RANGER_F": "RANGER_FEMALE",
    "ACE_TRAINER_M": "ACE_TRAINER_MALE",
    "ACE_TRAINER_F": "ACE_TRAINER_FEMALE",
    "ACE_TRAINER_SNOW_M": "ACE_TRAINER_SNOW_MALE",
    "ACE_TRAINER_SNOW_F": "ACE_TRAINER_SNOW_FEMALE",
    "CYCLIST_M": "CYCLIST_MALE",
    "CYCLIST_F": "CYCLIST_FEMALE",
    "POKEFAN_M": "POKEFAN_MALE",
    "POKEFAN": "POKEFAN_FEMALE",
    "POKEFAN_F": "POKEFAN_FEMALE",
    "PSYCHIC_M": "PSYCHIC_MALE",
    "PSYCHIC_F": "PSYCHIC_FEMALE",
    "SCHOOL_KID_M": "SCHOOL_KID_MALE",
    "SCHOOL_KID_F": "SCHOOL_KID_FEMALE",
    "SKIER_M": "SKIER_MALE",
    "SKIER_F": "SKIER_FEMALE",
    "SWIMMER_M": "SWIMMER_MALE",
    "SWIMMER_F": "SWIMMER_FEMALE",
    "TUBER_M": "TUBER_MALE",
    "TUBER_F": "TUBER_FEMALE",
    "BELLE__PA": "BELLE_AND_PA",
    "ELITE_FOUR_LUCIEN": "ELITE_FOUR_LUCIAN",
    "LEADER_WAKE": "LEADER_WAKE",
    "PKMN_TRAINER_ETHAN": "ETHAN",
    "PKMN_TRAINER_LYRA": "LYRA",
    "LEADER_FALKNER": "FALKNER",
    "LEADER_BUGSY": "BUGSY",
    "LEADER_WHITNEY": "WHITNEY",
    "LEADER_MORTY": "MORTY",
    "LEADER_PRYCE": "PRYCE",
    "LEADER_JASMINE": "JASMINE",
    "LEADER_CHUCK": "CHUCK",
    "LEADER_CLAIR": "CLAIR",
    "ELITE_FOUR_WILL": "WILL",
    "ELITE_FOUR_KAREN": "KAREN",
    "ELITE_FOUR_KOGA": "KOGA",
    "ELITE_FOUR_BRUNO": "BRUNO",
    "PKMN_TRAINER_RED": "RED",
    "PKMN_TRAINER_LANCE": "CHAMPION",
    "LEADER_BROCK": "BROCK",
    "LEADER_MISTY": "MISTY",
    "LEADER_LT_SURGE": "LT_SURGE",
    "LEADER_ERIKA": "ERIKA",
    "LEADER_JANINE": "JANINE",
    "LEADER_SABRINA": "SABRINA",
    "LEADER_BLAINE": "BLAINE",
    "LEADER_BLUE": "BLUE",
    "EXECUTIVE_ARIANA": "ARIANA",
    "EXECUTIVE_ARCHER": "ARCHER",
    "EXECUTIVE_PROTON": "PROTON",
    "EXECUTIVE_PETREL": "PETREL",
    "ROCKET_BOSS": "GIOVANNI",
    "TEAM_ROCKET_F": "ROCKET_GRUNT_F",
    "TEAM_ROCKET": "ROCKET_GRUNT_M",
}


def read_database_url():
    for line in (ROOT / ".env").read_text(encoding="utf-8", errors="replace").splitlines():
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


def normalize(value):
    return re.sub(r"[^a-z0-9]+", "", value.replace("é", "e").lower())


def load_event_locations(version_group_id):
    rows = psql_rows(
        f"""
        select el.canonical_location_id, cl.canonical_location_name, el.sort_order
        from event_locations el
        join canon_locations cl on cl.canonical_location_id = el.canonical_location_id
        where el.version_group_id = {version_group_id}
        order by el.sort_order, el.canonical_location_id
        """
    )
    return rows, {normalize(row["canonical_location_name"]): row for row in rows}


def map_constant_label(value):
    label = value.removeprefix("MAP_")
    label = re.sub(r"_(?:[0-9]+F|B[0-9]+F|[0-9]+)$", "", label)
    label = re.sub(r"_(?:NORTH|SOUTH|EAST|WEST|NORTHEAST|NORTHWEST|SOUTHEAST|SOUTHWEST)$", "", label)
    label = re.sub(r"_(?:GATEHOUSE|POKECENTER|POKECENTER_1F|POKECENTER_B1F|POKEMART|GYM|ENTRANCE)$", "", label)
    label = re.sub(r"_R[0-9].*$", "", label)
    return label.replace("_", " ").title()


def load_map_code_labels(decomp_root):
    maps_h = decomp_root / "include" / "constants" / "maps.h"
    if not maps_h.exists():
        return {}
    direct = {}
    base = {}
    for line in maps_h.read_text(encoding="utf-8", errors="replace").splitlines():
        match = re.search(r"#define\s+(MAP_[A-Z0-9_]+)\s+\d+\s*//\s*MAP_([A-Z0-9]+)", line)
        if not match:
            continue
        label = map_constant_label(match.group(1))
        code = match.group(2)
        direct[code] = label
        base_match = re.match(r"([A-Z]\d+)", code)
        if base_match and base_match.group(1) not in base:
            base[base_match.group(1)] = label
    direct.update({f"BASE:{key}": value for key, value in base.items()})
    return direct


def load_dp_map_references(decomp_root, trainer_constants):
    maps_h = decomp_root / "include" / "constants" / "maps.h"
    map_header = decomp_root / "arm9" / "src" / "map_header.c"
    zone_root = decomp_root / "files" / "fielddata" / "eventdata" / "zone_event_release"
    if not maps_h.exists() or not map_header.exists() or not zone_root.exists():
        return {}

    code_by_constant = {}
    for line in maps_h.read_text(encoding="utf-8", errors="replace").splitlines():
        match = re.search(r"#define\s+(MAP_[A-Z0-9_]+)\s+\d+\s*//\s*MAP_([A-Z0-9]+)", line)
        if match:
            code_by_constant[match.group(1)] = match.group(2)

    constant_by_index = {index: constant for index, constant in trainer_constants.items()}
    refs = defaultdict(set)
    for line in map_header.read_text(encoding="utf-8", errors="replace").splitlines():
        if "NARC_zone_event_release_narc_" not in line or "// MAP_" not in line:
            continue
        event_match = re.search(r"NARC_zone_event_release_narc_(\d+)_bin", line)
        map_match = re.search(r"//\s*(MAP_[A-Z0-9_]+)", line)
        if not event_match or not map_match:
            continue
        map_constant = map_match.group(1)
        map_code = code_by_constant.get(map_constant, map_constant)
        event_path = zone_root / f"narc_{int(event_match.group(1)):04d}.bin"
        if not event_path.exists():
            continue
        data = event_path.read_bytes()
        for index, constant in constant_by_index.items():
            normal_script = (0x0BB7 + index).to_bytes(2, "little", signed=False)
            double_script = (0x1387 + index).to_bytes(2, "little", signed=False)
            if normal_script in data or double_script in data:
                refs[constant].add(map_code)
    return refs


def read_constants(path):
    by_index = {}
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        clean = line.split("//", 1)[0].strip()
        match = re.match(r"#define\s+(TRAINER_[A-Z0-9_]+)\s+(\d+)\b", clean)
        if match:
            by_index[int(match.group(2))] = match.group(1)
    return by_index


def clean_name(value):
    return str(value or "").replace("{TRNAME}", "").strip().upper()


def class_to_trainer_class(value, class_prefix):
    label = str(value or "")
    if label.startswith("TRAINER_CLASS_"):
        return label
    if label.startswith("TRAINERCLASS_"):
        return "TRAINER_CLASS_" + label.removeprefix("TRAINERCLASS_")
    if label.startswith(class_prefix):
        return "TRAINER_CLASS_" + label.removeprefix(class_prefix)
    return label


def trainer_pic(game_key, class_constant):
    label = class_constant.removeprefix("TRAINER_CLASS_")
    if game_key == "heartgoldsoulsilver" and label == "RIVAL":
        return "TRAINER_PIC_SILVER"
    label = PIC_ALIASES.get(label, label)
    return f"TRAINER_PIC_{label}" if label else ""


def strip_prefix(value, prefix):
    value = value or ""
    return value.removeprefix(prefix)


def script_files(decomp_root):
    roots = [
        decomp_root / "res" / "field" / "scripts",
        decomp_root / "res" / "field" / "events",
        decomp_root / "files" / "fielddata" / "script",
        decomp_root / "files" / "fielddata" / "eventdata",
    ]
    for root in roots:
        if root.exists():
            for ext in ("*.s", "*.c", "*.h", "*.json"):
                yield from root.rglob(ext)


def load_map_references(decomp_root):
    refs = defaultdict(set)
    for path in script_files(decomp_root):
        text = path.read_text(encoding="utf-8", errors="replace")
        map_name = path.stem
        map_name = re.sub(r"^(scripts_|events_|scr_seq_|scr_|ev_)", "", map_name)
        for constant in sorted(set(re.findall(r"\bTRAINER_[A-Z0-9_]+\b", text))):
            if not constant.startswith("TRAINER_TYPE"):
                refs[constant].add(map_name)
    return refs


def map_name_code(map_name):
    return re.sub(r"^\d+_", "", map_name)


def choose_location(game_key, map_names, event_by_name, map_code_labels=None):
    manual = MANUAL_MAP_TO_CANON.get(game_key, {})
    candidates = []
    for map_name in map_names:
        manual_name = manual.get(map_name)
        if manual_name:
            row = event_by_name.get(normalize(manual_name))
            if row:
                candidates.append((1000, row, map_name))
                continue
        code = map_name_code(map_name)
        if map_code_labels:
            labels = []
            route_match = re.match(r"[RW](\d+)$", code)
            if route_match:
                route_number = int(route_match.group(1))
                route_row = event_by_name.get(normalize(f"Route {route_number}"))
                if route_row:
                    candidates.append((1200, route_row, map_name))
                labels.append(f"Route {route_number}")
            elif code in map_code_labels:
                labels.append(map_code_labels[code])
            base_match = re.match(r"([A-Z]\d+)", code)
            if not route_match and base_match and f"BASE:{base_match.group(1)}" in map_code_labels:
                labels.append(map_code_labels[f"BASE:{base_match.group(1)}"])
            for label in labels:
                label_norm = normalize(label)
                for key, row in event_by_name.items():
                    if key and (key in label_norm or label_norm in key):
                        candidates.append((900 + len(key), row, map_name))
        map_norm = normalize(map_name)
        for key, row in event_by_name.items():
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


def build_rows(game_key):
    cfg = CONFIG[game_key]
    decomp_root = cfg["decomp_root"]
    data = json.loads((decomp_root / cfg["trainer_json"]).read_text(encoding="utf-8", errors="replace"))
    trainers = data[cfg["trainer_array_key"]]
    constants = read_constants(decomp_root / cfg["constants"])
    event_rows, event_by_name = load_event_locations(cfg["version_group_id"])
    map_refs = load_map_references(decomp_root)
    if game_key == "diamondpearl":
        map_refs.update(load_dp_map_references(decomp_root, constants))
    map_code_labels = load_map_code_labels(decomp_root)

    trainer_rows = []
    pokemon_rows = []
    map_reference_rows = []
    missing_constants = []
    for fallback_index, trainer in enumerate(trainers):
        index = int(trainer.get("index", fallback_index))
        party = trainer.get("party") or []
        if not party:
            continue
        encounter_name = constants.get(index)
        if not encounter_name:
            missing_constants.append({"trainer_index": index, "trainer_name": clean_name(trainer.get("name")), "trainer_class": trainer.get("class", "")})
            encounter_name = f"TRAINER_INDEX_{index}"

        class_constant = class_to_trainer_class(trainer.get("class", ""), cfg["class_prefix"])
        map_names = sorted(map_refs.get(encounter_name, []))
        location, matched_map = choose_location(game_key, map_names, event_by_name, map_code_labels)
        is_rematch = "true" if re.search(r"_(REMATCH|2|3|4|5|6|7|8|9|10)$", encounter_name) else ""
        details = [
            f"{game_key}_trainer_index={index}",
            f"source={cfg['trainer_json'].as_posix()}",
        ]
        if map_names:
            details.append("map_refs=" + "|".join(map_names))
        if matched_map:
            details.append(f"matched_map={matched_map}")
        if not location:
            details.append("location_unpaired=true")

        trainer_rows.append(
            {
                "encounter_name": encounter_name,
                "trainer_name": clean_name(trainer.get("name")),
                "trainer_class": class_constant,
                "canonical_location_id": location["canonical_location_id"] if location else "",
                "is_rematch": is_rematch,
                "is_event": "",
                "trainer_items": ",".join(trainer.get("items") or []),
                "trainer_pic": trainer_pic(game_key, class_constant),
                "trainer_double": "True" if int(trainer.get("doubleBattle", trainer.get("double", 0)) or 0) else "",
                "details": "; ".join(details),
                "version_group_id": cfg["version_group_id"],
                "load_build": cfg["load_build"],
                "game_id": "",
            }
        )

        for slot, mon in enumerate(party, 1):
            pokemon_rows.append(
                {
                    "encounter_name": encounter_name,
                    "species_name": strip_prefix(mon.get("species", ""), "SPECIES_"),
                    "lvl": mon.get("level", ""),
                    "moves": ",".join(strip_prefix(move, "MOVE_") for move in (mon.get("moves") or [])),
                    "held_item": mon.get("item") or "",
                    "iv": mon.get("difficulty", ""),
                    "version_group_id": cfg["version_group_id"],
                    "load_build": cfg["load_build"],
                    "slot": slot,
                }
            )

        for map_name in map_names:
            map_reference_rows.append(
                {
                    "encounter_name": encounter_name,
                    "map_name": map_name,
                    "matched_canonical_location_id": location["canonical_location_id"] if location else "",
                    "matched_canonical_location_name": location["canonical_location_name"] if location else "",
                    "matched_map": matched_map,
                }
            )

    trainer_rows.sort(key=lambda row: int(re.search(r"trainer_index=(\d+)", row["details"]).group(1)))
    pokemon_rows.sort(key=lambda row: (row["encounter_name"], int(row["slot"])))
    return cfg, trainer_rows, pokemon_rows, map_reference_rows, missing_constants, event_rows


def main():
    parser = argparse.ArgumentParser(description="Build DS trainer preview CSVs for Diamond/Pearl or HGSS.")
    parser.add_argument("game", choices=sorted(CONFIG))
    args = parser.parse_args()

    cfg, trainer_rows, pokemon_rows, map_reference_rows, missing_constants, event_rows = build_rows(args.game)
    out_dir = cfg["out_dir"]
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
        [row for row in trainer_rows if row["canonical_location_id"] and row["is_rematch"].lower() != "true"],
        trainer_fields,
    )
    write_csv(out_dir / "trainer_pokemon_preview.csv", pokemon_rows, pokemon_fields)
    write_csv(out_dir / "map_reference_details.csv", map_reference_rows, ["encounter_name", "map_name", "matched_canonical_location_id", "matched_canonical_location_name", "matched_map"])
    write_csv(out_dir / "missing_trainer_constants.csv", missing_constants, ["trainer_index", "trainer_name", "trainer_class"])
    write_csv(out_dir / "event_locations_reference.csv", event_rows, ["canonical_location_id", "canonical_location_name", "sort_order"])

    located = sum(1 for row in trainer_rows if row["canonical_location_id"])
    displayable = sum(1 for row in trainer_rows if row["canonical_location_id"] and row["is_rematch"].lower() != "true")
    rematches = sum(1 for row in trainer_rows if row["is_rematch"].lower() == "true")
    print(f"game: {args.game}")
    print(f"version_group_id: {cfg['version_group_id']}")
    print(f"load_build: {cfg['load_build']}")
    print(f"trainer_pool_preview rows: {len(trainer_rows)}")
    print(f"trainer_pokemon_preview rows: {len(pokemon_rows)}")
    print(f"located trainer rows: {located}")
    print(f"displayable non-rematch rows: {displayable}")
    print(f"rematch rows: {rematches}")
    print(f"missing trainer constants: {len(missing_constants)}")
    print(f"wrote {out_dir}")


if __name__ == "__main__":
    main()
