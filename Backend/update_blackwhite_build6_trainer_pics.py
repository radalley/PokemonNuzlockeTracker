import argparse
import csv
import re
import subprocess
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SPRITE_DIR = ROOT.parent / "Frontend" / "public" / "sprites" / "trainers" / "gen5"
PREVIEW_DIR = ROOT / "blackwhite_build6_preview"
PSQL = Path(r"C:\Program Files\PostgreSQL\18\bin\psql.exe")
VERSION_GROUP_ID = 11
LOAD_BUILD = 6

NAMED_SPRITES = {
    "ALDER": "ALDER",
    "BIANCA": "BIANCA",
    "BRYCEN": "BRYCEN",
    "BURGH": "BURGH",
    "CAITLIN": "CAITLIN",
    "CHEREN": "CHEREN",
    "CHILI": "CHILI",
    "CILAN": "CILAN",
    "CLAY": "CLAY",
    "CRESS": "CRESS",
    "CYNTHIA": "CYNTHIA",
    "DRAYDEN": "DRAYDEN",
    "ELESA": "ELESA",
    "EMMET": "EMMET",
    "GHETSIS": "GHETSIS",
    "GRIMSLEY": "GRIMSLEY",
    "INGO": "INGO",
    "IRIS": "IRIS",
    "LENORA": "LENORA",
    "MARSHAL": "MARSHAL",
    "N": "N",
    "SHAUNTAL": "SHAUNTAL",
    "SKYLA": "SKYLA",
}

CLASS_ID_SPRITES = {
    2: "YOUNGSTER",
    3: "LASS",
    4: "SCHOOL_KID_M",
    5: "SCHOOL_KID_F",
    6: "SMASHER",
    7: "LINEBACKER",
    8: "WAITER",
    9: "WAITRESS",
    13: "NURSERY_AIDE",
    14: "PRESCHOOLER_F",
    15: "PRESCHOOLER_M",
    16: "TWINS",
    17: "POKEMON_BREEDER_M",
    18: "POKEMON_BREEDER_F",
    24: "POKEMON_RANGER_M",
    25: "POKEMON_RANGER_F",
    26: "WORKER",
    27: "BACKPACKER_M",
    28: "BACKPACKER_F",
    29: "FISHERMAN",
    30: "MUSICIAN",
    31: "DANCER",
    32: "HARLEQUIN",
    33: "ARTIST",
    34: "BAKER",
    35: "PSYCHIC_M",
    36: "PSYCHIC_F",
    37: "CHEREN",
    38: "BIANCA",
    39: "PLASMA_GRUNT_M",
    40: "N",
    41: "RICH_BOY",
    42: "LADY",
    43: "PILOT",
    44: "WORKERICE",
    45: "HOOPSTER",
    46: "SCIENTIST_F",
    47: "N",
    48: "CLERK_F",
    49: "ACE_TRAINER_F",
    50: "ACE_TRAINER_M",
    51: "BLACK_BELT",
    52: "SCIENTIST_M",
    53: "STRIKER",
    57: "ROUGHNECK",
    58: "JANITOR",
    59: "POKEFAN_M",
    60: "POKEFAN_F",
    61: "DOCTOR",
    62: "NURSE",
    63: "HOOLIGANS",
    64: "BATTLE_GIRL",
    65: "PARASOL_LADY",
    66: "CLERK_M_A",
    67: "CLERK_M_B",
    68: "BACKERS_M",
    69: "BACKERS_F",
    70: "VETERAN_M",
    71: "VETERAN_F",
    72: "BIKER",
    73: "INFIELDER",
    74: "HIKER",
    75: "SOCIALITE",
    76: "GENTLEMAN",
    77: "PLASMA_GRUNT_F",
    83: "DEPOT_AGENT",
    84: "SWIMMER_M",
    85: "SWIMMER_F",
    86: "POLICEMAN",
    87: "MAID",
    90: "CYCLIST_M",
    91: "CYCLIST_F",
    101: "N",
}


def database_url():
    for line in (ROOT / ".env").read_text(encoding="utf-8", errors="replace").splitlines():
        match = re.match(r"\s*DATABASE_URL\s*=\s*(.+?)\s*$", line)
        if match:
            return match.group(1).strip().strip("\"'")
    raise RuntimeError("DATABASE_URL was not found in Backend/.env")


def read_preview():
    with (PREVIEW_DIR / "trainer_pool_preview.csv").open("r", newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def available_stems():
    return {path.stem for path in SPRITE_DIR.glob("TRAINER_PIC_BW_*.png")}


def build_assignments():
    stems = available_stems()
    assignments = []
    unmatched = []
    for row in read_preview():
        class_match = re.search(r"trainer_class_id=(\d+)", row["details"])
        if not class_match:
            raise ValueError(f"Missing trainer_class_id for {row['encounter_name']}")
        class_id = int(class_match.group(1))
        label = NAMED_SPRITES.get(row["trainer_name"])
        source = "trainer_name" if label else "trainer_class_id"
        if not label:
            label = CLASS_ID_SPRITES.get(class_id)
        trainer_pic = f"TRAINER_PIC_BW_{label}" if label else ""
        if trainer_pic and trainer_pic not in stems:
            raise ValueError(f"Sprite alias does not exist: {trainer_pic}")
        assignment = {
            "encounter_name": row["encounter_name"],
            "trainer_name": row["trainer_name"],
            "trainer_class": row["trainer_class"],
            "trainer_class_id": class_id,
            "trainer_pic": trainer_pic,
            "match_source": source if trainer_pic else "",
        }
        assignments.append(assignment)
        if not trainer_pic:
            unmatched.append(assignment)
    return assignments, unmatched


def write_preview(assignments, unmatched):
    fields = [
        "encounter_name", "trainer_name", "trainer_class", "trainer_class_id",
        "trainer_pic", "match_source",
    ]
    for name, rows in (
        ("trainer_pic_assignments.csv", assignments),
        ("trainer_pic_unmatched.csv", unmatched),
    ):
        with (PREVIEW_DIR / name).open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)


def build_sql(stage_csv, rollback):
    finish = "ROLLBACK;" if rollback else "COMMIT;"
    return rf"""
BEGIN;

CREATE TEMP TABLE blackwhite_trainer_pic_stage (
  encounter_name text,
  trainer_pic text
) ON COMMIT DROP;

\copy blackwhite_trainer_pic_stage FROM '{stage_csv.as_posix()}' WITH (FORMAT csv, HEADER true)

DO $$
BEGIN
  IF EXISTS (
    SELECT 1
    FROM blackwhite_trainer_pic_stage s
    LEFT JOIN trainer_pool tp
      ON tp.encounter_name = s.encounter_name
     AND tp.version_group_id = {VERSION_GROUP_ID}
     AND tp.load_build = {LOAD_BUILD}
    WHERE tp.trainer_id IS NULL
  ) THEN
    RAISE EXCEPTION 'Sprite stage references an unknown Black/White trainer';
  END IF;
END $$;

UPDATE trainer_pool tp
SET trainer_pic = nullif(s.trainer_pic, '')
FROM blackwhite_trainer_pic_stage s
WHERE tp.encounter_name = s.encounter_name
  AND tp.version_group_id = {VERSION_GROUP_ID}
  AND tp.load_build = {LOAD_BUILD};

SELECT 'trainers_with_pics' AS metric, count(*) AS value
FROM trainer_pool
WHERE version_group_id = {VERSION_GROUP_ID}
  AND load_build = {LOAD_BUILD}
  AND trainer_pic IS NOT NULL;

SELECT 'bosses_with_pics' AS metric, count(*) AS value
FROM event_bosses eb
JOIN trainer_pool tp ON tp.trainer_id = eb.trainer_id
WHERE eb.version_group_id = {VERSION_GROUP_ID}
  AND tp.trainer_pic IS NOT NULL;

{finish}
"""


def main():
    parser = argparse.ArgumentParser(description="Assign Black/White trainer sprites in local Postgres.")
    parser.add_argument("--apply", action="store_true", help="Commit; default is rollback.")
    args = parser.parse_args()
    assignments, unmatched = build_assignments()
    write_preview(assignments, unmatched)

    with tempfile.TemporaryDirectory() as temp_dir:
        temp = Path(temp_dir)
        stage_csv = temp / "blackwhite_trainer_pic_stage.csv"
        sql_file = temp / "update_blackwhite_trainer_pics.sql"
        with stage_csv.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=["encounter_name", "trainer_pic"],
                extrasaction="ignore",
            )
            writer.writeheader()
            writer.writerows(assignments)
        sql_file.write_text(build_sql(stage_csv, rollback=not args.apply), encoding="utf-8")
        result = subprocess.run(
            [
                str(PSQL), database_url(), "-X", "-v", "ON_ERROR_STOP=1",
                "-P", "pager=off", "-f", str(sql_file),
            ],
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        print(result.stdout)
        if result.stderr:
            print(result.stderr)
    print(f"matched: {len(assignments) - len(unmatched)}")
    print(f"unmatched: {len(unmatched)}")
    print("Committed." if args.apply else "Dry run complete. Transaction rolled back.")


if __name__ == "__main__":
    main()
