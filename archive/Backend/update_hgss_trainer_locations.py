import argparse
import csv
import re
import subprocess
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parent
PSQL = Path(r"C:\Program Files\PostgreSQL\18\bin\psql.exe")
PREVIEW_DIR = ROOT / "heartgoldsoulsilver_build5_preview"
VERSION_GROUP_ID = 10
LOAD_BUILD = 5


def read_database_url():
    for line in (ROOT / ".env").read_text(encoding="utf-8", errors="replace").splitlines():
        match = re.match(r"\s*DATABASE_URL\s*=\s*(.+?)\s*$", line)
        if match:
            return match.group(1).strip().strip("\"'")
    raise RuntimeError("DATABASE_URL was not found in Backend/.env")


def write_stage_csv(path, preview_dir):
    rows = []
    with (preview_dir / "trainer_pool_preview.csv").open("r", newline="", encoding="utf-8") as file:
        for row in csv.DictReader(file):
            rows.append(
                {
                    "encounter_name": row["encounter_name"],
                    "canonical_location_id": row["canonical_location_id"],
                    "details": row["details"],
                    "trainer_pic": row["trainer_pic"],
                }
            )
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=["encounter_name", "canonical_location_id", "details", "trainer_pic"])
        writer.writeheader()
        writer.writerows(rows)
    return len(rows)


def build_sql(stage_csv, rollback):
    end_sql = "ROLLBACK;" if rollback else "COMMIT;"
    return f"""
BEGIN;

CREATE TEMP TABLE hgss_trainer_location_stage (
  encounter_name text,
  canonical_location_id text,
  details text,
  trainer_pic text
) ON COMMIT DROP;

\\copy hgss_trainer_location_stage FROM '{stage_csv.as_posix()}' WITH (FORMAT csv, HEADER true)

SELECT 'stage_rows' AS metric, count(*) AS value FROM hgss_trainer_location_stage;
SELECT 'stage_located_rows' AS metric, count(*) AS value FROM hgss_trainer_location_stage WHERE nullif(canonical_location_id, '') IS NOT NULL;

UPDATE trainer_pool tp
SET canonical_location_id = nullif(s.canonical_location_id, '')::integer,
    details = nullif(s.details, ''),
    trainer_pic = nullif(s.trainer_pic, '')
FROM hgss_trainer_location_stage s
WHERE tp.encounter_name = s.encounter_name
  AND tp.version_group_id = {VERSION_GROUP_ID}
  AND tp.load_build = {LOAD_BUILD};

SELECT 'hgss_located_after' AS metric, count(*) AS value
FROM trainer_pool
WHERE version_group_id = {VERSION_GROUP_ID}
  AND load_build = {LOAD_BUILD}
  AND canonical_location_id IS NOT NULL;

SELECT 'hgss_displayable_non_rematch_after' AS metric, count(*) AS value
FROM trainer_pool tp
WHERE tp.version_group_id = {VERSION_GROUP_ID}
  AND tp.load_build = {LOAD_BUILD}
  AND tp.canonical_location_id IS NOT NULL
  AND lower(coalesce(tp.is_rematch, '')) NOT IN ('true', 't', '1', 'yes')
  AND NOT EXISTS (
    SELECT 1
    FROM event_bosses eb
    WHERE eb.trainer_id = tp.trainer_id
      AND eb.version_group_id = tp.version_group_id
  );

{end_sql}
"""


def main():
    parser = argparse.ArgumentParser(description="Update loaded HGSS trainer locations from the generated preview.")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--preview-dir", default=str(PREVIEW_DIR))
    args = parser.parse_args()

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        stage_csv = tmp_path / "hgss_trainer_location_stage.csv"
        sql_file = tmp_path / "update_hgss_trainer_locations.sql"
        count = write_stage_csv(stage_csv, Path(args.preview_dir))
        print(f"Prepared {count} HGSS trainer location stage rows.")
        sql_file.write_text(build_sql(stage_csv, rollback=not args.apply), encoding="utf-8")
        result = subprocess.run(
            [str(PSQL), read_database_url(), "-X", "-v", "ON_ERROR_STOP=1", "-P", "pager=off", "-f", str(sql_file)],
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
