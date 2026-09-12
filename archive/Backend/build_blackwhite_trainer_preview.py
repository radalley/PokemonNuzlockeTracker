import csv
import hashlib
import json
import re
import struct
import subprocess
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parent
OUT_DIR = ROOT / "blackwhite_build6_preview"
PSQL = Path(r"C:\Program Files\PostgreSQL\18\bin\psql.exe")
VERSION_GROUP_ID = 11
LOAD_BUILD = 6

ROMS = {
    "black": Path(
        r"C:\Users\radal\OneDrive\Pokemon\Roms\Pokemon - Black Version (DSi Enhanced)(USA) (E)"
        r"\5585 - Pokemon - Black Version (DSi Enhanced)(USA) (E)(SweeTnDs).nds"
    ),
    "white": Path(
        r"C:\Users\radal\OneDrive\Pokemon\Roms\Pokemon - White Version (USA, Europe) (NDSi Enhanced)"
        r"\Pokemon - White Version (USA, Europe) (NDSi Enhanced).nds"
    ),
}

ROM_FILE_IDS = {
    "system_text": 244,  # a/0/0/2
    "trainer_data": 334,  # a/0/9/2
    "trainer_pokemon": 335,  # a/0/9/3
    "zone_headers": 254,  # a/0/1/2
    "map_scripts": 299,  # a/0/5/7
    "zone_entities": 367,  # a/1/2/5
}

TEXT_BANKS = {
    "items": 54,
    "species": 70,
    "trainer_names": 190,
    "trainer_classes": 191,
    "moves": 203,
    "map_names": 89,
}

LOCATION_ALIASES = {
    "icirruscity": "icciruscity",
    "mooroficirrus": "mooroficarus",
}

SPECIAL_CHARACTERS = {
    0x2015: "-",
    0x246D: "M",
    0x246E: "F",
    0x2486: "PK",
    0x2487: "MN",
    0xFFFE: "\n",
    0xFFFF: "",
}

CLASS_ID_ALIASES = {
    4: "SCHOOL_KID_M",
    5: "SCHOOL_KID_F",
    14: "PRESCHOOLER_M",
    15: "PRESCHOOLER_F",
    17: "PKMN_BREEDER_M",
    18: "PKMN_BREEDER_F",
    24: "PKMN_RANGER_M",
    25: "PKMN_RANGER_F",
    27: "BACKPACKER_M",
    28: "BACKPACKER_F",
    35: "PSYCHIC_M",
    36: "PSYCHIC_F",
    49: "ACE_TRAINER_M",
    50: "ACE_TRAINER_F",
    59: "POKEFAN_M",
    60: "POKEFAN_F",
    70: "VETERAN_M",
    71: "VETERAN_F",
    84: "SWIMMER_M",
    85: "SWIMMER_F",
    90: "CYCLIST_M",
    91: "CYCLIST_F",
}

FORM_NAMES = {
    (412, 1): "BURMY_SANDY_CLOAK",
    (412, 2): "BURMY_TRASH_CLOAK",
    (413, 1): "WORMADAM_SANDY_CLOAK",
    (413, 2): "WORMADAM_TRASH_CLOAK",
    (422, 1): "SHELLOS_EAST_SEA",
    (423, 1): "GASTRODON_EAST_SEA",
    (479, 1): "ROTOM_HEAT",
    (479, 2): "ROTOM_WASH",
    (479, 3): "ROTOM_FROST",
    (479, 4): "ROTOM_FAN",
    (479, 5): "ROTOM_MOW",
    (487, 1): "GIRATINA_ORIGIN",
    (492, 1): "SHAYMIN_SKY",
    (550, 1): "BASCULIN_BLUE_STRIPED",
    (555, 1): "DARMANITAN_ZEN",
}


class NdsRom:
    def __init__(self, path):
        self.path = path
        self.handle = path.open("rb")
        self.header = self.handle.read(0x200)
        self.game_code = self.header[0x0C:0x10].decode("ascii")
        self.version = self.header[0x1E]
        fat_offset, fat_size = struct.unpack_from("<II", self.header, 0x48)
        self.handle.seek(fat_offset)
        self.fat = self.handle.read(fat_size)

    def close(self):
        self.handle.close()

    def read_file(self, file_id):
        start, end = struct.unpack_from("<II", self.fat, file_id * 8)
        self.handle.seek(start)
        return self.handle.read(end - start)


def narc_members(data):
    if data[:4] != b"NARC":
        raise ValueError("Expected a NARC archive")

    blocks = {}
    position = 0x10
    block_count = struct.unpack_from("<H", data, 0x0E)[0]
    for _ in range(block_count):
        tag = data[position:position + 4]
        size = struct.unpack_from("<I", data, position + 4)[0]
        blocks[tag] = position
        position += size

    btaf = blocks[b"BTAF"]
    gmif = blocks[b"GMIF"]
    member_count = struct.unpack_from("<H", data, btaf + 8)[0]
    data_start = gmif + 8
    members = []
    for index in range(member_count):
        start, end = struct.unpack_from("<II", data, btaf + 12 + index * 8)
        members.append(data[data_start + start:data_start + end])
    return members


def rotate_left_16(value, amount=3):
    return ((value << amount) | (value >> (16 - amount))) & 0xFFFF


def decrypt_string(values, step):
    key = (0x2983 * step) & 0xFFFF
    decrypted = []
    for value in values:
        decrypted.append(value ^ key)
        key = rotate_left_16(key)

    if not decrypted or decrypted[0] != 0xF100:
        return [value for value in decrypted if value != 0xFFFF]

    output = []
    buffer = 0
    buffered_bits = 0
    for value in decrypted[1:]:
        buffer |= value << buffered_bits
        buffered_bits += 16
        while buffered_bits >= 9:
            character = buffer & 0x1FF
            buffer >>= 9
            buffered_bits -= 9
            if character == 0x1FF:
                return output
            output.append(character)
    return output


def render_text(values):
    characters = []
    for value in values:
        if 0x14 < value < 0x100:
            characters.append(chr(value))
        else:
            characters.append(SPECIAL_CHARACTERS.get(value, f"<0x{value:04X}>"))
    return "".join(characters)


def decode_text_bank(data):
    _, entry_count, _, _, section_offset = struct.unpack_from("<HHIII", data, 0)
    strings = []
    for index in range(entry_count):
        offset, character_count, _ = struct.unpack_from(
            "<IHH", data, section_offset + 4 + index * 8
        )
        values = struct.unpack_from(
            f"<{character_count}H", data, section_offset + offset
        )
        strings.append(render_text(decrypt_string(values, 3 + index)))
    return strings


def identifier(value, fallback="UNKNOWN"):
    value = value.replace("Pokémon", "Pokemon").replace("POKÉMON", "POKEMON")
    value = re.sub(r"[^A-Za-z0-9]+", "_", value).strip("_").upper()
    return value or fallback


def normalize(value):
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def database_url():
    for line in (ROOT / ".env").read_text(encoding="utf-8", errors="replace").splitlines():
        match = re.match(r"\s*DATABASE_URL\s*=\s*(.+?)\s*$", line)
        if match:
            return match.group(1).strip().strip("\"'")
    raise RuntimeError("DATABASE_URL was not found in Backend/.env")


def load_event_locations():
    sql = f"""
        select el.canonical_location_id, cl.canonical_location_name
        from event_locations el
        join canon_locations cl on cl.canonical_location_id = el.canonical_location_id
        where el.version_group_id = {VERSION_GROUP_ID}
        order by el.sort_order, el.canonical_location_id
    """
    result = subprocess.run(
        [str(PSQL), database_url(), "-X", "-A", "-F", "\t", "-P", "pager=off", "-c", sql],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    rows = []
    for line in result.stdout.splitlines()[1:]:
        if not line or line.startswith("("):
            continue
        values = line.split("\t")
        if len(values) == 2:
            rows.append(
                {
                    "canonical_location_id": values[0],
                    "canonical_location_name": values[1],
                }
            )
    return rows


def load_trainer_map_references(rom, map_names):
    zone_header_data = narc_members(rom.read_file(ROM_FILE_IDS["zone_headers"]))[0]
    entity_members = narc_members(rom.read_file(ROM_FILE_IDS["zone_entities"]))
    references = defaultdict(list)
    map_rows = []

    zone_count = len(zone_header_data) // 0x30
    for zone_index in range(min(zone_count, len(entity_members))):
        header_offset = zone_index * 0x30
        script_index = struct.unpack_from("<H", zone_header_data, header_offset + 6)[0]
        raw_name_index = struct.unpack_from("<H", zone_header_data, header_offset + 26)[0]
        name_index = raw_name_index & 0x3FF
        map_name = map_names[name_index] if name_index < len(map_names) else f"Map {zone_index}"

        data = entity_members[zone_index]
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
            if npc_type != 1 or not 3001 <= script_id <= 3615:
                continue
            trainer_index = script_id - 3000
            reference = {
                "trainer_index": trainer_index,
                "map_name": map_name,
                "zone_index": zone_index,
                "map_script_index": script_index,
                "npc_index": npc_index,
                "npc_script_id": script_id,
            }
            references[trainer_index].append(reference)
            map_rows.append(reference)
    return references, map_rows


def species_identifier(species_id, form_id, names):
    if (species_id, form_id) in FORM_NAMES:
        return FORM_NAMES[(species_id, form_id)]
    name = identifier(names[species_id], f"SPECIES_{species_id}")
    return f"{name}_FORM_{form_id}" if form_id else name


def parse_trainer(data):
    if len(data) < 20:
        raise ValueError(f"Trainer record is only {len(data)} bytes")
    format_flags, trainer_class, battle_type, party_size = struct.unpack_from("<BBBB", data)
    return {
        "format_flags": format_flags,
        "trainer_class_id": trainer_class,
        "battle_type": battle_type,
        "party_size": party_size,
        "items": list(struct.unpack_from("<4H", data, 4)),
        "ai": struct.unpack_from("<I", data, 12)[0],
        "is_healer": bool(data[16]),
        "money": data[17],
        "prize": struct.unpack_from("<H", data, 18)[0],
    }


def parse_party(data, trainer):
    has_moves = bool(trainer["format_flags"] & 1)
    has_item = bool(trainer["format_flags"] & 2)
    record_size = 8 + (2 if has_item else 0) + (8 if has_moves else 0)
    expected_size = trainer["party_size"] * record_size
    if len(data) != expected_size:
        raise ValueError(f"Party is {len(data)} bytes; expected {expected_size}")

    party = []
    for slot in range(trainer["party_size"]):
        offset = slot * record_size
        iv, pid, level, species, form = struct.unpack_from("<BBHHH", data, offset)
        offset += 8
        held_item = struct.unpack_from("<H", data, offset)[0] if has_item else 0
        offset += 2 if has_item else 0
        moves = list(struct.unpack_from("<4H", data, offset)) if has_moves else []
        party.append(
            {
                "slot": slot + 1,
                "iv": iv,
                "pid": pid,
                "level": level,
                "species": species,
                "form": form,
                "held_item": held_item,
                "moves": moves,
            }
        )
    return party


def write_csv(path, rows, fields):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def file_sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_preview():
    roms = {name: NdsRom(path) for name, path in ROMS.items()}
    try:
        expected_codes = {"black": "IRBO", "white": "IRAO"}
        for name, rom in roms.items():
            if rom.game_code != expected_codes[name]:
                raise ValueError(f"{name} ROM has unexpected game code {rom.game_code}")

        archive_bytes = {
            name: {
                key: rom.read_file(file_id)
                for key, file_id in ROM_FILE_IDS.items()
            }
            for name, rom in roms.items()
        }
        for key in ("trainer_data", "trainer_pokemon"):
            if archive_bytes["black"][key] != archive_bytes["white"][key]:
                raise ValueError(f"Black and White {key} archives differ")

        system_banks = narc_members(archive_bytes["black"]["system_text"])
        text = {
            key: decode_text_bank(system_banks[index])
            for key, index in TEXT_BANKS.items()
        }
        event_locations = load_event_locations()
        event_by_name = {
            normalize(row["canonical_location_name"]): row for row in event_locations
        }
        trainer_map_refs, map_rows = load_trainer_map_references(
            roms["black"], text["map_names"]
        )
        trainer_members = narc_members(archive_bytes["black"]["trainer_data"])
        party_members = narc_members(archive_bytes["black"]["trainer_pokemon"])
        if len(trainer_members) != 616 or len(party_members) != 616:
            raise ValueError("Expected 616 trainer and party members")
        if len(text["trainer_names"]) != 616:
            raise ValueError("Trainer-name count does not match trainer data")

        pool_rows = []
        pokemon_rows = []
        encounter_counts = defaultdict(int)
        battle_types = Counter()
        nonzero_forms = Counter()

        for trainer_index in range(1, len(trainer_members)):
            trainer = parse_trainer(trainer_members[trainer_index])
            party = parse_party(party_members[trainer_index], trainer)
            trainer_name = text["trainer_names"][trainer_index]
            class_name = text["trainer_classes"][trainer["trainer_class_id"]]
            class_id = CLASS_ID_ALIASES.get(
                trainer["trainer_class_id"],
                identifier(class_name, f"CLASS_{trainer['trainer_class_id']}"),
            )
            name_id = identifier(trainer_name, f"TRAINER_{trainer_index}")
            encounter_base = f"TRAINER_{class_id}_{name_id}"
            encounter_counts[encounter_base] += 1
            occurrence = encounter_counts[encounter_base]
            encounter_name = encounter_base if occurrence == 1 else f"{encounter_base}_{occurrence}"

            trainer_items = [
                identifier(text["items"][item_id], f"ITEM_{item_id}")
                for item_id in trainer["items"]
                if item_id
            ]
            battle_types[trainer["battle_type"]] += 1
            map_refs = trainer_map_refs.get(trainer_index, [])
            matched_locations = {}
            for reference in map_refs:
                normalized_name = normalize(reference["map_name"])
                normalized_name = LOCATION_ALIASES.get(normalized_name, normalized_name)
                location = event_by_name.get(normalized_name)
                if location:
                    matched_locations[location["canonical_location_id"]] = location
            canonical_location_id = (
                next(iter(matched_locations)) if len(matched_locations) == 1 else ""
            )
            details = [
                f"blackwhite_trainer_index={trainer_index}",
                "source_rom_paths=a/0/9/2,a/0/9/3",
                f"battle_type={trainer['battle_type']}",
                f"trainer_class_id={trainer['trainer_class_id']}",
                f"ai={trainer['ai']}",
                f"healer={str(trainer['is_healer']).lower()}",
                f"money={trainer['money']}",
                f"prize={trainer['prize']}",
            ]
            if map_refs:
                details.append(
                    "map_refs=" + ",".join(
                        sorted({f"{ref['map_name']}[zone={ref['zone_index']}]" for ref in map_refs})
                    )
                )
            if canonical_location_id:
                details.append(
                    f"matched_location={matched_locations[canonical_location_id]['canonical_location_name']}"
                )
            elif map_refs:
                details.append("event_location_unmatched=true")
                details.append("location_unpaired=true")
            else:
                details.append("location_unpaired=true")
            pool_rows.append(
                {
                    "encounter_name": encounter_name,
                    "trainer_name": trainer_name.upper(),
                    "trainer_class": f"TRAINER_CLASS_{class_id}",
                    "canonical_location_id": canonical_location_id,
                    "is_rematch": "",
                    "is_event": "",
                    "trainer_items": ",".join(trainer_items),
                    "trainer_pic": "",
                    "trainer_double": "1" if trainer["battle_type"] == 1 else "",
                    "details": "; ".join(details),
                    "version_group_id": VERSION_GROUP_ID,
                    "load_build": LOAD_BUILD,
                    "game_id": "",
                }
            )

            for pokemon in party:
                move_names = [
                    identifier(text["moves"][move_id], f"MOVE_{move_id}")
                    for move_id in pokemon["moves"]
                    if move_id
                ]
                held_item = (
                    identifier(text["items"][pokemon["held_item"]], f"ITEM_{pokemon['held_item']}")
                    if pokemon["held_item"]
                    else ""
                )
                if pokemon["form"]:
                    nonzero_forms[(pokemon["species"], pokemon["form"])] += 1
                pokemon_rows.append(
                    {
                        "encounter_name": encounter_name,
                        "species_name": species_identifier(
                            pokemon["species"], pokemon["form"], text["species"]
                        ),
                        "lvl": pokemon["level"],
                        "moves": ",".join(move_names),
                        "held_item": held_item,
                        "iv": pokemon["iv"],
                        "version_group_id": VERSION_GROUP_ID,
                        "load_build": LOAD_BUILD,
                        "slot": pokemon["slot"],
                    }
                )

        pool_fields = [
            "encounter_name", "trainer_name", "trainer_class", "canonical_location_id",
            "is_rematch", "is_event", "trainer_items", "trainer_pic", "trainer_double",
            "details", "version_group_id", "load_build", "game_id",
        ]
        pokemon_fields = [
            "encounter_name", "species_name", "lvl", "moves", "held_item", "iv",
            "version_group_id", "load_build", "slot",
        ]
        write_csv(OUT_DIR / "trainer_pool_preview.csv", pool_rows, pool_fields)
        write_csv(OUT_DIR / "trainer_pokemon_preview.csv", pokemon_rows, pokemon_fields)
        write_csv(
            OUT_DIR / "trainer_pool_displayable_preview.csv",
            [row for row in pool_rows if row["canonical_location_id"]],
            pool_fields,
        )
        write_csv(
            OUT_DIR / "map_reference_details.csv",
            map_rows,
            [
                "trainer_index", "map_name", "zone_index", "map_script_index",
                "npc_index", "npc_script_id",
            ],
        )

        summary = {
            "version_group_id": VERSION_GROUP_ID,
            "load_build": LOAD_BUILD,
            "roms": {
                name: {
                    "path": str(rom.path),
                    "game_code": rom.game_code,
                    "rom_version": rom.version,
                    "sha256": file_sha256(rom.path),
                }
                for name, rom in roms.items()
            },
            "trainer_archives_identical": True,
            "trainer_rows": len(pool_rows),
            "trainer_pokemon_rows": len(pokemon_rows),
            "battle_type_counts": dict(sorted(battle_types.items())),
            "nonzero_form_counts": {
                f"species_{species}_form_{form}": count
                for (species, form), count in sorted(nonzero_forms.items())
            },
            "map_reference_rows": len(map_rows),
            "trainers_with_map_references": len(trainer_map_refs),
            "located_rows": sum(bool(row["canonical_location_id"]) for row in pool_rows),
            "database_modified": False,
        }
        (OUT_DIR / "validation_summary.json").write_text(
            json.dumps(summary, indent=2), encoding="utf-8"
        )
        print(f"trainer_pool_preview rows: {len(pool_rows)}")
        print(f"trainer_pokemon_preview rows: {len(pokemon_rows)}")
        print(f"output: {OUT_DIR}")
    finally:
        for rom in roms.values():
            rom.close()


if __name__ == "__main__":
    build_preview()
