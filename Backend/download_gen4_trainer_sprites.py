import csv
import shutil
import time
import urllib.parse
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "Frontend" / "public" / "sprites" / "trainers" / "gen4"
MANIFEST = OUT_DIR / "gen4_sprite_manifest.csv"

API_URL = "https://archives.bulbagarden.net/w/api.php"
CATEGORY = "Category:Generation IV Trainer sprites"
USER_AGENT = "Lockley local data loader/1.0 (trainer sprite import)"


SPECIAL_ALIASES = {
    "AARON": "ELITE_FOUR_AARON",
    "BARRY": "RIVAL",
    "BERTHA": "ELITE_FOUR_BERTHA",
    "BUCK": "TRAINER_BUCK",
    "BYRON": "LEADER_BYRON",
    "CANDICE": "LEADER_CANDICE",
    "CHERYL": "TRAINER_CHERYL",
    "CRASHER_WAKE": "LEADER_WAKE",
    "CYNTHIA": "CHAMPION_CYNTHIA",
    "CYRUS": "GALACTIC_BOSS",
    "DAWN": "DP_PLAYER_FEMALE",
    "FANTINA": "LEADER_FANTINA",
    "FLINT": "ELITE_FOUR_FLINT",
    "GARDENIA": "LEADER_GARDENIA",
    "LUCAS": "DP_PLAYER_MALE",
    "LUCIAN": "ELITE_FOUR_LUCIAN",
    "MARLEY": "TRAINER_MARLEY",
    "MARS": "COMMANDER_MARS",
    "MAYLENE": "LEADER_MAYLENE",
    "MIRA": "TRAINER_MIRA",
    "PALMER": "TOWER_TYCOON",
    "RILEY": "TRAINER_RILEY",
    "ROARK": "LEADER_ROARK",
    "SATURN": "COMMANDER_SATURN",
    "THORTON": "FACTORY_HEAD",
    "VOLKNER": "LEADER_VOLKNER",
}

GENERIC_ALIASES = {
    "ACE_TRAINER_F_1": "ACE_TRAINER_FEMALE",
    "ACE_TRAINER_F_2": "ACE_TRAINER_SNOW_FEMALE",
    "ACE_TRAINER_M_1": "ACE_TRAINER_MALE",
    "ACE_TRAINER_M_2": "ACE_TRAINER_SNOW_MALE",
    "ACE_TRAINER_F": "ACE_TRAINER_FEMALE",
    "ACE_TRAINER_M": "ACE_TRAINER_MALE",
    "ACE_TRAINER_SNOW_F": "ACE_TRAINER_SNOW_FEMALE",
    "ACE_TRAINER_SNOW_M": "ACE_TRAINER_SNOW_MALE",
    "BREEDER_F": "BREEDER_FEMALE",
    "BREEDER_M": "BREEDER_MALE",
    "CYCLIST_F": "CYCLIST_FEMALE",
    "CYCLIST_M": "CYCLIST_MALE",
    "GALACTIC_GRUNT_F": "GALACTIC_GRUNT_FEMALE",
    "GALACTIC_GRUNT_M": "GALACTIC_GRUNT_MALE",
    "POKEFAN_F": "POKEFAN_FEMALE",
    "POKEFAN_M": "POKEFAN_MALE",
    "POKÉFAN_F": "POKEFAN_FEMALE",
    "POKÉFAN_M": "POKEFAN_MALE",
    "POKÉ_KID": "POKE_KID",
    "POKEMON_BREEDER_F": "BREEDER_FEMALE",
    "POKEMON_BREEDER_M": "BREEDER_MALE",
    "POKÉMON_BREEDER_F": "BREEDER_FEMALE",
    "POKÉMON_BREEDER_M": "BREEDER_MALE",
    "POKEMON_RANGER_F": "RANGER_FEMALE",
    "POKEMON_RANGER_M": "RANGER_MALE",
    "POKÉMON_RANGER_F": "RANGER_FEMALE",
    "POKÉMON_RANGER_M": "RANGER_MALE",
    "PSYCHIC_F": "PSYCHIC_FEMALE",
    "PSYCHIC_M": "PSYCHIC_MALE",
    "RANGER_F": "RANGER_FEMALE",
    "RANGER_M": "RANGER_MALE",
    "SCHOOL_KID_F": "SCHOOL_KID_FEMALE",
    "SCHOOL_KID_M": "SCHOOL_KID_MALE",
    "SKIER_F": "SKIER_FEMALE",
    "SKIER_M": "SKIER_MALE",
    "SWIMMER_F": "SWIMMER_FEMALE",
    "SWIMMER_M": "SWIMMER_MALE",
    "TUBER_F": "TUBER_FEMALE",
    "TUBER_M": "TUBER_MALE",
    "OFFICER": "POLICEMAN",
    "JUPITER": "COMMANDER_JUPITER",
    "ARGENTA": "HALL_MATRON",
    "DAHLIA": "ARCADE_STAR",
    "DARACH_CAITLIN": "CASTLE_VALET",
    "SIS_AND_BRO_BETA": "SIS_AND_BRO",
}


def request_json(params):
    query = urllib.parse.urlencode(params)
    request = urllib.request.Request(f"{API_URL}?{query}", headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=30) as response:
        return __import__("json").loads(response.read().decode("utf-8"))


def category_files():
    files = []
    cont = {}
    while True:
        params = {
            "action": "query",
            "format": "json",
            "generator": "categorymembers",
            "gcmtitle": CATEGORY,
            "gcmtype": "file",
            "gcmlimit": "500",
            "prop": "imageinfo",
            "iiprop": "url",
        }
        params.update(cont)
        data = request_json(params)
        for page in data.get("query", {}).get("pages", {}).values():
            title = page.get("title", "")
            imageinfo = page.get("imageinfo") or []
            if title.startswith("File:") and imageinfo:
                files.append({"title": title.removeprefix("File:"), "url": imageinfo[0]["url"]})
        if "continue" not in data:
            break
        cont = data["continue"]
    return sorted(files, key=lambda row: row["title"])


def safe_file_name(title):
    return title.replace(" ", "_")


def normalized_stem(title):
    stem = Path(title).stem
    stem = stem.replace(" ", "_").replace("-", "_")
    return stem.upper()


def lockley_alias(title):
    stem = normalized_stem(title)
    if stem.startswith("SPR_PT_"):
        label = stem.removeprefix("SPR_PT_")
    elif stem.startswith("SPR_DP_"):
        label = stem.removeprefix("SPR_DP_")
    else:
        return None
    label = SPECIAL_ALIASES.get(label, GENERIC_ALIASES.get(label, label))
    return f"TRAINER_PIC_{label}.png"


def download_file(url, dest):
    if dest.exists() and dest.stat().st_size > 0:
        return False
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=30) as response:
        dest.write_bytes(response.read())
    time.sleep(0.05)
    return True


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    rows = []
    downloaded = 0
    aliases = 0
    for file_info in category_files():
        title = file_info["title"]
        original_name = safe_file_name(title)
        original_path = OUT_DIR / original_name
        if download_file(file_info["url"], original_path):
            downloaded += 1

        alias_name = lockley_alias(title)
        if alias_name:
            alias_path = OUT_DIR / alias_name
            if not alias_path.exists():
                shutil.copyfile(original_path, alias_path)
                aliases += 1

        rows.append(
            {
                "source_title": title,
                "source_url": file_info["url"],
                "stored_file": original_name,
                "platinum_alias": alias_name or "",
            }
        )

    with MANIFEST.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=["source_title", "source_url", "stored_file", "platinum_alias"])
        writer.writeheader()
        writer.writerows(rows)

    print(f"category files: {len(rows)}")
    print(f"downloaded originals: {downloaded}")
    print(f"created platinum aliases: {aliases}")
    print(f"wrote {OUT_DIR}")
    print(f"manifest {MANIFEST}")


if __name__ == "__main__":
    main()
