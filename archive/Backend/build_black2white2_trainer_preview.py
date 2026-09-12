import csv
import hashlib
import json
import re
import struct
import subprocess
from collections import Counter, defaultdict
from pathlib import Path

from build_blackwhite_trainer_preview import (
    NdsRom,
    decode_text_bank,
    identifier,
    narc_members,
    parse_party,
    parse_trainer,
    species_identifier,
)


ROOT = Path(__file__).resolve().parent
OUT_DIR = ROOT / "black2white2_build6_preview"
SPRITE_DIR = ROOT.parent / "Frontend" / "public" / "sprites" / "trainers" / "gen5"
PSQL = Path(r"C:\Program Files\PostgreSQL\18\bin\psql.exe")
VERSION_GROUP_ID = 14
LOAD_BUILD = 6
BLACK2_GAME_ID = 21
WHITE2_GAME_ID = 22

ROMS = {
    "black2": Path(
        r"C:\Users\radal\OneDrive\Pokemon\Roms\Pokemon - Black Version 2 (USA, Europe) (NDSi Enhanced)"
        r"\Pokemon - Black Version 2 (USA, Europe) (NDSi Enhanced).nds"
    ),
    "white2": Path(
        r"C:\Users\radal\OneDrive\Pokemon\Roms\Pokemon - White Version 2 (USA, Europe) (NDSi Enhanced)"
        r"\Pokemon - White Version 2 (USA, Europe) (NDSi Enhanced).nds"
    ),
}

FILE_IDS = {
    "system_text": 349,  # a/0/0/2
    "zone_headers": 359,  # a/0/1/2
    "map_scripts": 403,  # a/0/5/6
    "trainer_data": 438,  # a/0/9/1
    "trainer_pokemon": 439,  # a/0/9/2
    "zone_entities": 473,  # a/1/2/6
}

TEXT_BANKS = {
    "items": 64,
    "species": 90,
    "map_names": 109,
    "trainer_names": 382,
    "trainer_classes": 383,
    "moves": 403,
}

LOCATION_ALIASES = {
    "icirruscity": "icciruscity",
    "mooroficirrus": "mooroficarus",
}

NON_LOCATION_CLASS_NAMES = {
    "bosstrainer", "champion", "elitefour", "leader", "pkmntrainer", "subwayboss",
}
NON_LOCATION_TRAINER_NAMES = {"shadow", "zinzolin"}

# Gendered classes share display text in the ROM. These IDs preserve the sprite distinction.
CLASS_ID_ALIASES = {
    4: "SCHOOL_KID_M",
    5: "SCHOOL_KID_F",
    14: "PRESCHOOLER_F",
    15: "PRESCHOOLER_M",
    17: "PKMN_BREEDER_M",
    18: "PKMN_BREEDER_F",
    24: "PKMN_RANGER_M",
    25: "PKMN_RANGER_F",
    27: "BACKPACKER_M",
    28: "BACKPACKER_F",
    35: "PSYCHIC_M",
    36: "PSYCHIC_F",
    49: "ACE_TRAINER_F",
    50: "ACE_TRAINER_M",
    59: "POKEFAN_M",
    60: "POKEFAN_F",
    70: "VETERAN_M",
    71: "VETERAN_F",
    84: "SWIMMER_M",
    85: "SWIMMER_F",
    90: "CYCLIST_M",
    91: "CYCLIST_F",
}

CLASS_ID_SPRITES = {
    2: "YOUNGSTER", 3: "LASS", 4: "SCHOOL_KID_M", 5: "SCHOOL_KID_F",
    6: "SMASHER", 7: "LINEBACKER", 8: "WAITER", 9: "WAITRESS",
    13: "NURSERY_AIDE", 14: "PRESCHOOLER_F", 15: "PRESCHOOLER_M",
    16: "TWINS", 17: "POKEMON_BREEDER_M", 18: "POKEMON_BREEDER_F",
    24: "POKEMON_RANGER_M", 25: "POKEMON_RANGER_F", 26: "WORKER",
    27: "BACKPACKER_M", 28: "BACKPACKER_F", 29: "FISHERMAN",
    30: "MUSICIAN", 31: "DANCER", 32: "HARLEQUIN", 33: "ARTIST",
    34: "BAKER", 35: "PSYCHIC_M", 36: "PSYCHIC_F", 39: "PLASMA_GRUNT_M",
    41: "RICH_BOY", 42: "LADY", 43: "PILOT", 44: "WORKERICE",
    45: "HOOPSTER", 46: "SCIENTIST_F", 48: "CLERK_F",
    49: "ACE_TRAINER_F", 50: "ACE_TRAINER_M", 51: "BLACK_BELT",
    52: "SCIENTIST_M", 53: "STRIKER", 57: "ROUGHNECK", 58: "JANITOR",
    59: "POKEFAN_M", 60: "POKEFAN_F", 61: "DOCTOR", 62: "NURSE",
    63: "HOOLIGANS", 64: "BATTLE_GIRL", 65: "PARASOL_LADY",
    66: "CLERK_M_A", 67: "CLERK_M_B", 68: "BACKERS_M", 69: "BACKERS_F",
    70: "VETERAN_M", 71: "VETERAN_F", 72: "BIKER", 73: "INFIELDER",
    74: "HIKER", 75: "SOCIALITE", 76: "GENTLEMAN", 77: "PLASMA_GRUNT_F",
    83: "DEPOT_AGENT", 84: "SWIMMER_M", 85: "SWIMMER_F",
    86: "POLICEMAN", 87: "MAID", 90: "CYCLIST_M", 91: "CYCLIST_F",
    145: "HUGH", 187: "PLASMA_GRUNT_M", 188: "PLASMA_GRUNT_F",
    192: "SHADOW_TRIAD",
}


def normalize(value):
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def database_url():
    for line in (ROOT / ".env").read_text(encoding="utf-8", errors="replace").splitlines():
        match = re.match(r"\s*DATABASE_URL\s*=\s*(.+?)\s*$", line)
        if match:
            return match.group(1).strip().strip("\"'")
    raise RuntimeError("DATABASE_URL was not found in Backend/.env")


def load_event_locations():
    result = subprocess.run(
        [
            str(PSQL), database_url(), "-X", "-A", "-F", "\t", "-P", "pager=off",
            "-c",
            f"""select el.canonical_location_id, cl.canonical_location_name
                 from event_locations el
                 join canon_locations cl on cl.canonical_location_id=el.canonical_location_id
                where el.version_group_id={VERSION_GROUP_ID}
                order by el.sort_order,el.canonical_location_id""",
        ],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    rows = []
    for line in result.stdout.splitlines()[1:]:
        values = line.split("\t")
        if len(values) == 2:
            rows.append({"canonical_location_id": values[0], "canonical_location_name": values[1]})
    return rows


def load_location_reference():
    path = OUT_DIR / "serebii_location_matches.csv"
    if not path.exists():
        return {}
    with path.open(encoding="utf-8", newline="") as handle:
        return {row["encounter_name"]: row for row in csv.DictReader(handle)}


def is_location_trainer(trainer_name, class_name):
    if normalize(class_name) in NON_LOCATION_CLASS_NAMES:
        return False
    if normalize(trainer_name) in NON_LOCATION_TRAINER_NAMES:
        return False
    return True


def map_references(rom, map_names, trainer_count):
    headers = narc_members(rom.read_file(FILE_IDS["zone_headers"]))[0]
    entities = narc_members(rom.read_file(FILE_IDS["zone_entities"]))
    refs = defaultdict(list)
    rows = []
    for zone_index in range(min(len(headers) // 0x30, len(entities))):
        offset = zone_index * 0x30
        script_index = struct.unpack_from("<H", headers, offset + 6)[0]
        name_index = struct.unpack_from("<H", headers, offset + 26)[0] & 0x3FF
        map_name = map_names[name_index] if name_index < len(map_names) else f"Map {zone_index}"
        data = entities[zone_index]
        if len(data) < 8:
            continue
        interactable_count, npc_count, _, _ = data[4:8]
        npc_start = 8 + interactable_count * 0x14
        for npc_index in range(npc_count):
            npc_offset = npc_start + npc_index * 0x24
            if npc_offset + 0x24 > len(data):
                raise ValueError(f"Zone {zone_index} has a truncated NPC table")
            npc_type = struct.unpack_from("<H", data, npc_offset + 6)[0]
            script_id = struct.unpack_from("<H", data, npc_offset + 10)[0]
            trainer_index = script_id - 3000
            if npc_type != 1 or not 1 <= trainer_index < trainer_count:
                continue
            row = {
                "trainer_index": trainer_index,
                "map_name": map_name,
                "zone_index": zone_index,
                "map_script_index": script_index,
                "npc_index": npc_index,
                "npc_script_id": script_id,
            }
            refs[trainer_index].append(row)
            rows.append(row)
    return refs, rows


def file_sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sprite_for(trainer_name, class_id, class_name, available):
    candidates = []
    if trainer_name:
        candidates.append(identifier(trainer_name))
    if class_id in CLASS_ID_SPRITES:
        candidates.append(CLASS_ID_SPRITES[class_id])
    candidates.append(identifier(class_name))
    for candidate in candidates:
        stem = f"TRAINER_PIC_B2W2_{candidate}"
        if stem in available:
            return stem
    return ""


def write_csv(path, rows, fields):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main():
    roms = {name: NdsRom(path) for name, path in ROMS.items()}
    try:
        if roms["black2"].game_code != "IREO" or roms["white2"].game_code != "IRDO":
            raise ValueError("Unexpected Black 2/White 2 game code")
        archives = {
            name: {key: rom.read_file(FILE_IDS[key]) for key in ("system_text", "trainer_data", "trainer_pokemon")}
            for name, rom in roms.items()
        }
        for key in ("trainer_data", "trainer_pokemon"):
            if archives["black2"][key] != archives["white2"][key]:
                raise ValueError(f"Black 2 and White 2 {key} archives differ")

        banks = narc_members(archives["black2"]["system_text"])
        text = {key: decode_text_bank(banks[index]) for key, index in TEXT_BANKS.items()}
        trainers = narc_members(archives["black2"]["trainer_data"])
        parties = narc_members(archives["black2"]["trainer_pokemon"])
        if len(trainers) != 814 or len(parties) != 814 or len(text["trainer_names"]) != 814:
            raise ValueError("Expected 814 aligned B2W2 trainer records")

        event_locations = load_event_locations()
        event_by_name = {normalize(row["canonical_location_name"]): row for row in event_locations}
        location_reference = load_location_reference()
        available_sprites = {path.stem for path in SPRITE_DIR.glob("TRAINER_PIC_B2W2_*.png")}
        pool_rows = []
        pokemon_rows = []
        encounter_counts = defaultdict(int)
        battle_types = Counter()

        for trainer_index in range(1, len(trainers)):
            trainer = parse_trainer(trainers[trainer_index])
            party = parse_party(parties[trainer_index], trainer)
            trainer_name = text["trainer_names"][trainer_index]
            class_id_number = trainer["trainer_class_id"]
            class_name = text["trainer_classes"][class_id_number]
            class_id = CLASS_ID_ALIASES.get(class_id_number, identifier(class_name, f"CLASS_{class_id_number}"))
            name_id = identifier(trainer_name, f"TRAINER_{trainer_index}")
            base = f"TRAINER_{class_id}_{name_id}"
            encounter_counts[base] += 1
            encounter_name = base if encounter_counts[base] == 1 else f"{base}_{encounter_counts[base]}"

            all_refs = []
            game_id = ""
            matched = {}
            location_ref = location_reference.get(encounter_name)
            if location_ref and is_location_trainer(trainer_name, class_name):
                key = normalize(location_ref["location_name"])
                key = LOCATION_ALIASES.get(key, key)
                location = event_by_name.get(key)
                if location:
                    matched[location["canonical_location_id"]] = location
            canonical_location_id = next(iter(matched)) if len(matched) == 1 else ""
            trainer_items = [
                identifier(text["items"][item], f"ITEM_{item}") for item in trainer["items"] if item
            ]
            trainer_pic = sprite_for(trainer_name, class_id_number, class_name, available_sprites)
            battle_types[trainer["battle_type"]] += 1
            details = [
                f"black2white2_trainer_index={trainer_index}",
                "source_rom_paths=a/0/9/1,a/0/9/2",
                f"battle_type={trainer['battle_type']}",
                f"trainer_class_id={class_id_number}",
                f"ai={trainer['ai']}",
                f"healer={str(trainer['is_healer']).lower()}",
                f"money={trainer['money']}",
                f"prize={trainer['prize']}",
            ]
            if location_ref:
                details.append(f"location_reference={location_ref['source_url']}")
            if canonical_location_id:
                details.append(f"matched_location={matched[canonical_location_id]['canonical_location_name']}")
            else:
                details.append("location_unpaired=true")
            pool_rows.append({
                "encounter_name": encounter_name,
                "trainer_name": trainer_name.upper(),
                "trainer_class": f"TRAINER_CLASS_{class_id}",
                "canonical_location_id": canonical_location_id,
                "is_rematch": "",
                "is_event": "",
                "trainer_items": ",".join(trainer_items),
                "trainer_pic": trainer_pic,
                "trainer_double": "1" if trainer["battle_type"] == 1 else "",
                "details": "; ".join(details),
                "version_group_id": VERSION_GROUP_ID,
                "load_build": LOAD_BUILD,
                "game_id": game_id,
            })

            for pokemon in party:
                moves = [identifier(text["moves"][move], f"MOVE_{move}") for move in pokemon["moves"] if move]
                held_item = identifier(text["items"][pokemon["held_item"]], f"ITEM_{pokemon['held_item']}") if pokemon["held_item"] else ""
                pokemon_rows.append({
                    "encounter_name": encounter_name,
                    "species_name": species_identifier(pokemon["species"], pokemon["form"], text["species"]),
                    "lvl": pokemon["level"],
                    "moves": ",".join(moves),
                    "held_item": held_item,
                    "iv": pokemon["iv"],
                    "version_group_id": VERSION_GROUP_ID,
                    "load_build": LOAD_BUILD,
                    "slot": pokemon["slot"],
                })

        pool_fields = ["encounter_name", "trainer_name", "trainer_class", "canonical_location_id", "is_rematch", "is_event", "trainer_items", "trainer_pic", "trainer_double", "details", "version_group_id", "load_build", "game_id"]
        pokemon_fields = ["encounter_name", "species_name", "lvl", "moves", "held_item", "iv", "version_group_id", "load_build", "slot"]
        write_csv(OUT_DIR / "trainer_pool_preview.csv", pool_rows, pool_fields)
        write_csv(OUT_DIR / "trainer_pokemon_preview.csv", pokemon_rows, pokemon_fields)
        write_csv(OUT_DIR / "trainer_pool_displayable_preview.csv", [row for row in pool_rows if row["canonical_location_id"]], pool_fields)
        write_csv(OUT_DIR / "trainer_pic_unmatched.csv", [row for row in pool_rows if not row["trainer_pic"]], pool_fields)

        summary = {
            "version_group_id": VERSION_GROUP_ID,
            "load_build": LOAD_BUILD,
            "roms": {name: {"path": str(rom.path), "game_code": rom.game_code, "sha256": file_sha256(rom.path)} for name, rom in roms.items()},
            "trainer_archives_identical": True,
            "trainer_rows": len(pool_rows),
            "trainer_pokemon_rows": len(pokemon_rows),
            "located_rows": sum(bool(row["canonical_location_id"]) for row in pool_rows),
            "game_specific_rows": sum(bool(row["game_id"]) for row in pool_rows),
            "sprite_matched_rows": sum(bool(row["trainer_pic"]) for row in pool_rows),
            "sprite_unmatched_rows": sum(not row["trainer_pic"] for row in pool_rows),
            "battle_type_counts": dict(sorted(battle_types.items())),
            "database_modified": False,
        }
        (OUT_DIR / "validation_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
        print(f"trainer_pool_preview rows: {len(pool_rows)}")
        print(f"trainer_pokemon_preview rows: {len(pokemon_rows)}")
        print(f"located rows: {summary['located_rows']}")
        print(f"sprite matched rows: {summary['sprite_matched_rows']}")
        print(f"output: {OUT_DIR}")
    finally:
        for rom in roms.values():
            rom.close()


if __name__ == "__main__":
    main()
