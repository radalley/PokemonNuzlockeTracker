import argparse
import csv
import re
import subprocess
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parent
PREVIEW_DIR = ROOT / "blackwhite_build6_preview"
PSQL = Path(r"C:\Program Files\PostgreSQL\18\bin\psql.exe")
VERSION_GROUP_ID = 11
LOAD_BUILD = 6
EXPECTED_TRAINERS = 615
EXPECTED_POKEMON = 1304


def database_url():
    for line in (ROOT / ".env").read_text(encoding="utf-8", errors="replace").splitlines():
        match = re.match(r"\s*DATABASE_URL\s*=\s*(.+?)\s*$", line)
        if match:
            return match.group(1).strip().strip("\"'")
    raise RuntimeError("DATABASE_URL was not found in Backend/.env")


def read_csv(path):
    with path.open("r", newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(path, rows, fields):
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def validate_preview(trainers, pokemon):
    if len(trainers) != EXPECTED_TRAINERS:
        raise ValueError(f"Expected {EXPECTED_TRAINERS} trainers, found {len(trainers)}")
    if len(pokemon) != EXPECTED_POKEMON:
        raise ValueError(f"Expected {EXPECTED_POKEMON} trainer Pokemon, found {len(pokemon)}")
    for label, rows in (("trainer", trainers), ("Pokemon", pokemon)):
        if any(row["version_group_id"] != str(VERSION_GROUP_ID) for row in rows):
            raise ValueError(f"Unexpected version_group_id in {label} preview")
        if any(row["load_build"] != str(LOAD_BUILD) for row in rows):
            raise ValueError(f"Unexpected load_build in {label} preview")
    if any(row["game_id"] for row in trainers):
        raise ValueError("Black/White trainer preview must not assign game_id")
    encounter_names = [row["encounter_name"] for row in trainers]
    if len(encounter_names) != len(set(encounter_names)):
        raise ValueError("Duplicate encounter_name values found in trainer preview")
    known_encounters = set(encounter_names)
    missing = sorted({row["encounter_name"] for row in pokemon} - known_encounters)
    if missing:
        raise ValueError(f"Pokemon rows reference unknown encounters: {missing[:5]}")


def build_sql(trainer_csv, pokemon_csv, rollback):
    finish = "ROLLBACK;" if rollback else "COMMIT;"
    return rf"""
BEGIN;

CREATE TEMP TABLE blackwhite_trainer_pool_stage (
  encounter_name text,
  trainer_name text,
  trainer_class text,
  canonical_location_id text,
  is_rematch text,
  is_event text,
  trainer_items text,
  trainer_pic text,
  trainer_double text,
  details text,
  version_group_id integer,
  load_build integer,
  game_id text
) ON COMMIT DROP;

CREATE TEMP TABLE blackwhite_trainer_pokemon_stage (
  encounter_name text,
  species_name text,
  lvl integer,
  moves text,
  held_item text,
  iv integer,
  version_group_id integer,
  load_build integer,
  slot integer
) ON COMMIT DROP;

\copy blackwhite_trainer_pool_stage FROM '{trainer_csv.as_posix()}' WITH (FORMAT csv, HEADER true)
\copy blackwhite_trainer_pokemon_stage FROM '{pokemon_csv.as_posix()}' WITH (FORMAT csv, HEADER true)

DO $$
BEGIN
  IF (SELECT count(*) FROM blackwhite_trainer_pool_stage) <> {EXPECTED_TRAINERS} THEN
    RAISE EXCEPTION 'Unexpected trainer stage row count';
  END IF;
  IF (SELECT count(*) FROM blackwhite_trainer_pokemon_stage) <> {EXPECTED_POKEMON} THEN
    RAISE EXCEPTION 'Unexpected trainer Pokemon stage row count';
  END IF;
  IF EXISTS (
    SELECT 1 FROM blackwhite_trainer_pool_stage
    WHERE version_group_id <> {VERSION_GROUP_ID} OR load_build <> {LOAD_BUILD}
  ) OR EXISTS (
    SELECT 1 FROM blackwhite_trainer_pokemon_stage
    WHERE version_group_id <> {VERSION_GROUP_ID} OR load_build <> {LOAD_BUILD}
  ) THEN
    RAISE EXCEPTION 'Stage contains the wrong version group or load build';
  END IF;
  IF EXISTS (
    SELECT 1 FROM trainer_pool
    WHERE version_group_id = {VERSION_GROUP_ID} AND load_build = {LOAD_BUILD}
  ) OR EXISTS (
    SELECT 1 FROM trainer_pokemon
    WHERE version_group_id = {VERSION_GROUP_ID} AND load_build = {LOAD_BUILD}
  ) THEN
    RAISE EXCEPTION 'Black/White build 6 already contains trainer data';
  END IF;
END $$;

INSERT INTO trainer_pool (
  encounter_name, trainer_name, trainer_class, canonical_location_id,
  is_rematch, is_event, trainer_items, trainer_pic, trainer_double,
  details, version_group_id, load_build, game_id
)
SELECT
  nullif(encounter_name, ''),
  nullif(trainer_name, ''),
  nullif(trainer_class, ''),
  nullif(canonical_location_id, '')::integer,
  nullif(is_rematch, ''),
  nullif(is_event, ''),
  nullif(trainer_items, ''),
  nullif(trainer_pic, ''),
  nullif(trainer_double, ''),
  nullif(details, ''),
  version_group_id,
  load_build,
  nullif(game_id, '')::integer
FROM blackwhite_trainer_pool_stage
ORDER BY encounter_name;

INSERT INTO trainer_pokemon (
  encounter_name, species_name, lvl, moves, held_item, iv,
  version_group_id, load_build
)
SELECT
  nullif(encounter_name, ''),
  nullif(species_name, ''),
  lvl,
  nullif(moves, ''),
  nullif(held_item, ''),
  iv,
  version_group_id,
  load_build
FROM blackwhite_trainer_pokemon_stage
ORDER BY encounter_name, slot;

SELECT 'trainer_pool_rows' AS metric, count(*) AS value
FROM trainer_pool
WHERE version_group_id = {VERSION_GROUP_ID} AND load_build = {LOAD_BUILD};

SELECT 'trainer_pokemon_rows' AS metric, count(*) AS value
FROM trainer_pokemon
WHERE version_group_id = {VERSION_GROUP_ID} AND load_build = {LOAD_BUILD};

SELECT 'located_rows' AS metric, count(*) AS value
FROM trainer_pool
WHERE version_group_id = {VERSION_GROUP_ID}
  AND load_build = {LOAD_BUILD}
  AND canonical_location_id IS NOT NULL;

SELECT 'rows_with_game_id' AS metric, count(*) AS value
FROM trainer_pool
WHERE version_group_id = {VERSION_GROUP_ID}
  AND load_build = {LOAD_BUILD}
  AND game_id IS NOT NULL;

{finish}
"""


def main():
    parser = argparse.ArgumentParser(description="Load Black/White build-6 trainers into local Postgres.")
    parser.add_argument("--apply", action="store_true", help="Commit the transaction; default is rollback.")
    parser.add_argument("--preview-dir", default=str(PREVIEW_DIR))
    args = parser.parse_args()

    preview_dir = Path(args.preview_dir)
    trainers = read_csv(preview_dir / "trainer_pool_preview.csv")
    pokemon = read_csv(preview_dir / "trainer_pokemon_preview.csv")
    validate_preview(trainers, pokemon)

    trainer_fields = [
        "encounter_name", "trainer_name", "trainer_class", "canonical_location_id",
        "is_rematch", "is_event", "trainer_items", "trainer_pic", "trainer_double",
        "details", "version_group_id", "load_build", "game_id",
    ]
    pokemon_fields = [
        "encounter_name", "species_name", "lvl", "moves", "held_item", "iv",
        "version_group_id", "load_build", "slot",
    ]
    with tempfile.TemporaryDirectory() as temp_dir:
        temp = Path(temp_dir)
        trainer_csv = temp / "blackwhite_trainer_pool_stage.csv"
        pokemon_csv = temp / "blackwhite_trainer_pokemon_stage.csv"
        sql_file = temp / "load_blackwhite_build6.sql"
        write_csv(trainer_csv, trainers, trainer_fields)
        write_csv(pokemon_csv, pokemon, pokemon_fields)
        sql_file.write_text(
            build_sql(trainer_csv, pokemon_csv, rollback=not args.apply),
            encoding="utf-8",
        )
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
    print("Committed." if args.apply else "Dry run complete. Transaction rolled back.")


if __name__ == "__main__":
    main()
