import argparse
import csv
import re
import subprocess
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parent
PREVIEW_DIR = ROOT / "crystal_build4_preview"
PSQL = Path(r"C:\Program Files\PostgreSQL\18\bin\psql.exe")
VERSION_GROUP_ID = 4
LOAD_BUILD = 4


def read_database_url():
    env_path = ROOT / ".env"
    if not env_path.exists():
        raise RuntimeError("Backend/.env not found")
    for line in env_path.read_text(encoding="utf-8", errors="replace").splitlines():
        match = re.match(r"\s*DATABASE_URL\s*=\s*(.+?)\s*$", line)
        if match:
            return match.group(1).strip().strip("\"'")
    raise RuntimeError("DATABASE_URL was not found in Backend/.env")


def read_csv(path):
    with path.open("r", newline="", encoding="utf-8") as file:
        return list(csv.DictReader(file))


def write_csv(path, rows, fieldnames):
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def psql(database_url, sql_file):
    return subprocess.run(
        [str(PSQL), database_url, "-X", "-v", "ON_ERROR_STOP=1", "-P", "pager=off", "-f", str(sql_file)],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )


def build_sql(trainer_csv, pokemon_csv, rollback, version_group_id, load_build):
    rollback_sql = "ROLLBACK;" if rollback else "COMMIT;"
    return f"""
BEGIN;

CREATE TEMP TABLE crystal_trainer_pool_stage (
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

CREATE TEMP TABLE crystal_trainer_pokemon_stage (
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

\\copy crystal_trainer_pool_stage FROM '{trainer_csv.as_posix()}' WITH (FORMAT csv, HEADER true)
\\copy crystal_trainer_pokemon_stage FROM '{pokemon_csv.as_posix()}' WITH (FORMAT csv, HEADER true)

SELECT 'trainer_pool_stage_rows' AS metric, count(*) AS value FROM crystal_trainer_pool_stage;
SELECT 'trainer_pokemon_stage_rows' AS metric, count(*) AS value FROM crystal_trainer_pokemon_stage;
SELECT 'displayable_non_rematch_stage_rows' AS metric, count(*) AS value
FROM crystal_trainer_pool_stage
WHERE nullif(canonical_location_id, '') IS NOT NULL
  AND lower(coalesce(is_rematch, '')) NOT IN ('true', 't', '1', 'yes');

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
FROM crystal_trainer_pool_stage
ON CONFLICT DO NOTHING;

INSERT INTO trainer_pokemon (
  encounter_name, species_name, lvl, moves, held_item, iv, version_group_id, load_build
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
FROM crystal_trainer_pokemon_stage
ORDER BY encounter_name, slot
ON CONFLICT DO NOTHING;

SELECT 'trainer_pool_vg{version_group_id}_build{load_build}_after' AS metric, count(*) AS value
FROM trainer_pool
WHERE version_group_id = {version_group_id} AND load_build = {load_build};

SELECT 'trainer_pokemon_vg{version_group_id}_build{load_build}_after' AS metric, count(*) AS value
FROM trainer_pokemon
WHERE version_group_id = {version_group_id} AND load_build = {load_build};

{rollback_sql}
"""


def main():
    parser = argparse.ArgumentParser(description="Load Gen II trainer preview rows into Postgres.")
    parser.add_argument("--apply", action="store_true", help="Commit rows. Without this flag, the transaction rolls back.")
    parser.add_argument("--preview-dir", default=str(PREVIEW_DIR), help="Directory containing trainer preview CSVs.")
    parser.add_argument("--version-group-id", type=int, default=VERSION_GROUP_ID)
    parser.add_argument("--load-build", type=int, default=LOAD_BUILD)
    args = parser.parse_args()

    preview_dir = Path(args.preview_dir)
    trainer_rows = read_csv(preview_dir / "trainer_pool_preview.csv")
    pokemon_rows = read_csv(preview_dir / "trainer_pokemon_preview.csv")
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

    database_url = read_database_url()
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        trainer_csv = tmp_path / "trainer_pool_stage.csv"
        pokemon_csv = tmp_path / "trainer_pokemon_stage.csv"
        sql_file = tmp_path / "load_crystal_build4.sql"
        write_csv(trainer_csv, trainer_rows, trainer_fields)
        write_csv(pokemon_csv, pokemon_rows, pokemon_fields)
        sql_file.write_text(
            build_sql(
                trainer_csv,
                pokemon_csv,
                rollback=not args.apply,
                version_group_id=args.version_group_id,
                load_build=args.load_build,
            ),
            encoding="utf-8",
        )
        result = psql(database_url, sql_file)
        print(result.stdout)
        if result.stderr:
            print(result.stderr)
    print("Committed." if args.apply else "Dry run complete. Transaction rolled back.")


if __name__ == "__main__":
    main()
