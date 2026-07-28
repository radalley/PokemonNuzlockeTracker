import argparse
import csv
import re
import subprocess
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parent
PREVIEW = ROOT / "blackwhite_build6_preview" / "event_bosses_preview.csv"
PSQL = Path(r"C:\Program Files\PostgreSQL\18\bin\psql.exe")
VERSION_GROUP_ID = 11
LOAD_BUILD = 6
EXPECTED_ROWS = 61
EXPECTED_GAME_ROWS = 4
ALLOWED_GAME_IDS = {"", "17", "18"}


def database_url():
    for line in (ROOT / ".env").read_text(encoding="utf-8", errors="replace").splitlines():
        match = re.match(r"\s*DATABASE_URL\s*=\s*(.+?)\s*$", line)
        if match:
            return match.group(1).strip().strip("\"'")
    raise RuntimeError("DATABASE_URL was not found in Backend/.env")


def read_preview():
    with PREVIEW.open("r", newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) != EXPECTED_ROWS:
        raise ValueError(f"Expected {EXPECTED_ROWS} event bosses, found {len(rows)}")
    if any(row["version_group_id"] != str(VERSION_GROUP_ID) for row in rows):
        raise ValueError("Preview contains an unexpected version_group_id")
    if any(row["game_id"] not in ALLOWED_GAME_IDS for row in rows):
        raise ValueError("Preview contains an unexpected game_id")
    if sum(bool(row["game_id"]) for row in rows) != EXPECTED_GAME_ROWS:
        raise ValueError(f"Expected exactly {EXPECTED_GAME_ROWS} version-specific boss rows")
    return rows


def build_sql(stage_csv, rollback):
    finish = "ROLLBACK;" if rollback else "COMMIT;"
    sequence_sql = "" if rollback else """
SELECT setval(
  pg_get_serial_sequence('event_bosses', 'event_id'),
  (SELECT max(event_id) FROM event_bosses),
  true
);
"""
    return rf"""
BEGIN;

CREATE TEMP TABLE blackwhite_event_boss_stage (
  trainer_id integer,
  trainer_index integer,
  encounter_name text,
  trainer_name text,
  sort_order text,
  encounter_title text,
  starter text,
  type_focus text,
  version_group_id integer,
  event_type text,
  game_id text,
  badge_id text
) ON COMMIT DROP;

\copy blackwhite_event_boss_stage FROM '{stage_csv.as_posix()}' WITH (FORMAT csv, HEADER true)

DO $$
BEGIN
  IF (SELECT count(*) FROM blackwhite_event_boss_stage) <> {EXPECTED_ROWS} THEN
    RAISE EXCEPTION 'Unexpected event-boss stage row count';
  END IF;
  IF EXISTS (
    SELECT 1 FROM blackwhite_event_boss_stage WHERE version_group_id <> {VERSION_GROUP_ID}
  ) THEN
    RAISE EXCEPTION 'Stage contains the wrong version group';
  END IF;
  IF EXISTS (SELECT 1 FROM event_bosses WHERE version_group_id = {VERSION_GROUP_ID}) THEN
    RAISE EXCEPTION 'Black/White event bosses already exist';
  END IF;
  IF EXISTS (
    SELECT 1
    FROM blackwhite_event_boss_stage s
    LEFT JOIN trainer_pool tp ON tp.trainer_id = s.trainer_id
    WHERE tp.trainer_id IS NULL
       OR tp.version_group_id <> {VERSION_GROUP_ID}
       OR tp.load_build <> {LOAD_BUILD}
  ) THEN
    RAISE EXCEPTION 'Stage references a trainer outside Black/White build 6';
  END IF;
  IF (SELECT count(*) FROM blackwhite_event_boss_stage WHERE nullif(game_id, '') IS NOT NULL) <> {EXPECTED_GAME_ROWS} THEN
    RAISE EXCEPTION 'Unexpected version-specific boss row count';
  END IF;
END $$;

WITH numbered AS (
  SELECT s.*,
         row_number() OVER (
           ORDER BY sort_order::numeric, encounter_title, starter, trainer_id
         ) AS row_number,
         (SELECT coalesce(max(event_id), 0) FROM event_bosses) AS current_max
  FROM blackwhite_event_boss_stage s
)
INSERT INTO event_bosses (
  event_id, trainer_id, sort_order, encounter_title, starter, type_focus,
  version_group_id, event_type, game_id, badge_id
)
SELECT
  current_max + row_number,
  trainer_id,
  sort_order,
  encounter_title,
  nullif(starter, ''),
  nullif(type_focus, ''),
  version_group_id,
  nullif(event_type, ''),
  nullif(game_id, '')::integer,
  nullif(badge_id, '')::integer
FROM numbered
ORDER BY sort_order::numeric, encounter_title, starter, trainer_id;

{sequence_sql}

SELECT 'event_boss_rows' AS metric, count(*) AS value
FROM event_bosses WHERE version_group_id = {VERSION_GROUP_ID};

SELECT 'starter_rows' AS metric, count(*) AS value
FROM event_bosses WHERE version_group_id = {VERSION_GROUP_ID} AND starter IS NOT NULL;

SELECT 'game_specific_rows' AS metric, count(*) AS value
FROM event_bosses WHERE version_group_id = {VERSION_GROUP_ID} AND game_id IS NOT NULL;

SELECT 'located_boss_trainers' AS metric, count(*) AS value
FROM event_bosses eb
JOIN trainer_pool tp ON tp.trainer_id = eb.trainer_id
WHERE eb.version_group_id = {VERSION_GROUP_ID}
  AND tp.canonical_location_id IS NOT NULL;

{finish}
"""


def main():
    parser = argparse.ArgumentParser(description="Load Black/White event bosses into local Postgres.")
    parser.add_argument("--apply", action="store_true", help="Commit; default is rollback.")
    args = parser.parse_args()
    rows = read_preview()
    fields = list(rows[0])

    with tempfile.TemporaryDirectory() as temp_dir:
        temp = Path(temp_dir)
        stage_csv = temp / "blackwhite_event_boss_stage.csv"
        sql_file = temp / "load_blackwhite_event_bosses.sql"
        with stage_csv.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)
        sql_file.write_text(build_sql(stage_csv, rollback=not args.apply), encoding="utf-8")
        result = subprocess.run(
            [
                str(PSQL), database_url(), "-X", "-v", "ON_ERROR_STOP=1",
                "-P", "pager=off", "-f", str(sql_file),
            ],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        print(result.stdout)
        if result.stderr:
            print(result.stderr)
        if result.returncode:
            raise RuntimeError(f"psql failed with exit code {result.returncode}")
    print("Committed." if args.apply else "Dry run complete. Transaction rolled back.")


if __name__ == "__main__":
    main()
