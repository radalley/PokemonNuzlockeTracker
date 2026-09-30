import argparse
import csv
import re
import subprocess
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parent
PSQL = Path(r"C:\Program Files\PostgreSQL\18\bin\psql.exe")
VERSION_GROUP_ID = 3


BOSS_ROWS = [
    ("TRAINER_RIVAL1_RIVAL1_1_CHIKORITA", "4.1", "Cherrygrove City", "Water"),
    ("TRAINER_RIVAL1_RIVAL1_1_TOTODILE", "4.1", "Cherrygrove City", "Fire"),
    ("TRAINER_RIVAL1_RIVAL1_1_CYNDAQUIL", "4.1", "Cherrygrove City", "Grass"),
    ("TRAINER_FALKNER_FALKNER1", "8.1", "Violet City Gym", None),
    ("TRAINER_BUGSY_BUGSY1", "15.1", "Azalea Town Gym", None),
    ("TRAINER_RIVAL1_RIVAL1_2_CHIKORITA", "15.2", "Azalea Town", "Water"),
    ("TRAINER_RIVAL1_RIVAL1_2_TOTODILE", "15.2", "Azalea Town", "Fire"),
    ("TRAINER_RIVAL1_RIVAL1_2_CYNDAQUIL", "15.2", "Azalea Town", "Grass"),
    ("TRAINER_WHITNEY_WHITNEY1", "18.1", "Goldenrod City Gym", None),
    ("TRAINER_RIVAL1_RIVAL1_3_CHIKORITA", "24.1", "Burned Tower", "Water"),
    ("TRAINER_RIVAL1_RIVAL1_3_TOTODILE", "24.1", "Burned Tower", "Fire"),
    ("TRAINER_RIVAL1_RIVAL1_3_CYNDAQUIL", "24.1", "Burned Tower", "Grass"),
    ("TRAINER_MORTY_MORTY1", "25.1", "Ecruteak City Gym", None),
    ("TRAINER_CHUCK_CHUCK1", "32.1", "Cianwood City Gym", None),
    ("TRAINER_JASMINE_JASMINE1", "32.2", "Olivine City Gym", None),
    ("TRAINER_EXECUTIVEM_EXECUTIVEM_4", "37.1", "Rocket Hideout", None),
    ("TRAINER_EXECUTIVEF_EXECUTIVEF_2", "37.2", "Rocket Hideout", None),
    ("TRAINER_PRYCE_PRYCE1", "37.3", "Mahogany Town Gym", None),
    ("TRAINER_RIVAL1_RIVAL1_4_CHIKORITA", "37.4", "Goldenrod City", "Water"),
    ("TRAINER_RIVAL1_RIVAL1_4_TOTODILE", "37.4", "Goldenrod City", "Fire"),
    ("TRAINER_RIVAL1_RIVAL1_4_CYNDAQUIL", "37.4", "Goldenrod City", "Grass"),
    ("TRAINER_EXECUTIVEM_EXECUTIVEM_3", "37.5", "Radio Tower", None),
    ("TRAINER_EXECUTIVEM_EXECUTIVEM_2", "37.6", "Radio Tower", None),
    ("TRAINER_EXECUTIVEF_EXECUTIVEF_1", "37.7", "Radio Tower", None),
    ("TRAINER_EXECUTIVEM_EXECUTIVEM_1", "37.8", "Radio Tower", None),
    ("TRAINER_CLAIR_CLAIR1", "41.1", "Blackthorn City Gym", None),
    ("TRAINER_RIVAL1_RIVAL1_5_CHIKORITA", "46.1", "Victory Road", "Water"),
    ("TRAINER_RIVAL1_RIVAL1_5_CYNDAQUIL", "46.1", "Victory Road", "Grass"),
    ("TRAINER_RIVAL1_RIVAL1_5_TOTODILE", "46.1", "Victory Road", "Fire"),
    ("TRAINER_WILL_WILL1", "46.2", "Elite Four", None),
    ("TRAINER_KOGA_KOGA1", "46.3", "Elite Four", None),
    ("TRAINER_BRUNO_BRUNO1", "46.4", "Elite Four", None),
    ("TRAINER_KAREN_KAREN1", "46.5", "Elite Four", None),
    ("TRAINER_CHAMPION_LANCE", "46.6", "Champion", None),
    ("TRAINER_LT_SURGE_LT_SURGE1", "47.1", "Vermilion City Gym", None),
    ("TRAINER_SABRINA_SABRINA1", "48.1", "Saffron City Gym", None),
    ("TRAINER_ERIKA_ERIKA1", "50.1", "Celadon City Gym", None),
    ("TRAINER_MISTY_MISTY1", "55.1", "Cerulean City Gym", None),
    ("TRAINER_JANINE_JANINE1", "62.1", "Fuschia City Gym", None),
    ("TRAINER_BROCK_BROCK1", "70.1", "Pewter City Gym", None),
    ("TRAINER_RIVAL2_RIVAL2_1_CYNDAQUIL", "72.1", "Mt. Moon", "Grass"),
    ("TRAINER_RIVAL2_RIVAL2_1_TOTODILE", "72.1", "Mt. Moon", "Fire"),
    ("TRAINER_RIVAL2_RIVAL2_1_CHIKORITA", "72.1", "Mt. Moon", "Water"),
    ("TRAINER_BLAINE_BLAINE1", "77.1", "Cinnabar Island Gym", None),
    ("TRAINER_BLUE_BLUE1", "77.2", "Viridian City Gym", None),
    ("TRAINER_RED_RED1", "82.1", "Mt. Silver", None),
]


def read_database_url():
    env_path = ROOT / ".env"
    if not env_path.exists():
        raise RuntimeError("Backend/.env not found")
    for line in env_path.read_text(encoding="utf-8", errors="replace").splitlines():
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


def write_stage_csv(path, rows):
    fieldnames = ["row_num", "event_id", "trainer_id", "sort_order", "encounter_title", "starter", "version_group_id"]
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def build_stage_rows():
    trainer_rows = psql_rows(
        f"""
        select encounter_name, trainer_id
        from trainer_pool
        where version_group_id = {VERSION_GROUP_ID}
          and load_build = 4
        """
    )
    trainer_id_by_encounter = {row["encounter_name"]: int(row["trainer_id"]) for row in trainer_rows}
    missing = [encounter for encounter, *_ in BOSS_ROWS if encounter not in trainer_id_by_encounter]
    if missing:
        raise RuntimeError(f"Missing Gold/Silver trainer_pool rows: {', '.join(missing)}")

    blank_event_ids = [
        int(row["event_id"])
        for row in psql_rows(
            f"""
            select event_id
            from event_bosses
            where version_group_id = {VERSION_GROUP_ID}
              and trainer_id is null
              and nullif(sort_order, '') is null
              and nullif(encounter_title, '') is null
              and nullif(starter, '') is null
            order by event_id
            """
        )
    ]
    max_event_id_rows = psql_rows("select coalesce(max(event_id), 0) as max_event_id from event_bosses")
    next_event_id = int(max_event_id_rows[0]["max_event_id"]) + 1

    rows = []
    for index, (encounter_name, sort_order, encounter_title, starter) in enumerate(BOSS_ROWS, 1):
        if index <= len(blank_event_ids):
            event_id = blank_event_ids[index - 1]
        else:
            event_id = next_event_id
            next_event_id += 1
        rows.append({
            "row_num": index,
            "event_id": event_id,
            "trainer_id": trainer_id_by_encounter[encounter_name],
            "sort_order": sort_order,
            "encounter_title": encounter_title,
            "starter": starter or "",
            "version_group_id": VERSION_GROUP_ID,
        })
    return rows, len(blank_event_ids)


def build_sql(stage_csv, rollback):
    end_sql = "ROLLBACK;" if rollback else "COMMIT;"
    return f"""
BEGIN;

CREATE TEMP TABLE goldsilver_event_boss_stage (
  row_num integer,
  event_id integer,
  trainer_id integer,
  sort_order text,
  encounter_title text,
  starter text,
  version_group_id integer
) ON COMMIT DROP;

\\copy goldsilver_event_boss_stage FROM '{stage_csv.as_posix()}' WITH (FORMAT csv, HEADER true)

SELECT 'stage_rows' AS metric, count(*) AS value FROM goldsilver_event_boss_stage;
SELECT 'existing_blank_rows_to_update' AS metric, count(*) AS value
FROM goldsilver_event_boss_stage s
JOIN event_bosses eb ON eb.event_id = s.event_id
WHERE eb.version_group_id = 3
  AND eb.trainer_id IS NULL
  AND nullif(eb.sort_order, '') IS NULL
  AND nullif(eb.encounter_title, '') IS NULL
  AND nullif(eb.starter, '') IS NULL;
SELECT 'rows_to_insert' AS metric, count(*) AS value
FROM goldsilver_event_boss_stage s
LEFT JOIN event_bosses eb ON eb.event_id = s.event_id
WHERE eb.event_id IS NULL;

UPDATE event_bosses eb
SET trainer_id = s.trainer_id,
    sort_order = s.sort_order,
    encounter_title = s.encounter_title,
    starter = nullif(s.starter, ''),
    version_group_id = s.version_group_id
FROM goldsilver_event_boss_stage s
WHERE eb.event_id = s.event_id
  AND eb.version_group_id = 3
  AND eb.trainer_id IS NULL
  AND nullif(eb.sort_order, '') IS NULL
  AND nullif(eb.encounter_title, '') IS NULL
  AND nullif(eb.starter, '') IS NULL;

INSERT INTO event_bosses (
  event_id, trainer_id, sort_order, encounter_title, starter, version_group_id
)
SELECT
  s.event_id, s.trainer_id, s.sort_order, s.encounter_title,
  nullif(s.starter, ''), s.version_group_id
FROM goldsilver_event_boss_stage s
LEFT JOIN event_bosses eb ON eb.event_id = s.event_id
WHERE eb.event_id IS NULL
ORDER BY s.row_num;

SELECT 'vg3_event_bosses_after' AS metric, count(*) AS value
FROM event_bosses
WHERE version_group_id = 3
  AND trainer_id IS NOT NULL;

{end_sql}
"""


def main():
    parser = argparse.ArgumentParser(description="Populate Gold/Silver event_bosses from loaded trainer_pool rows.")
    parser.add_argument("--apply", action="store_true", help="Commit changes. Without this flag, rolls back.")
    args = parser.parse_args()

    rows, blank_count = build_stage_rows()
    print(f"Prepared {len(rows)} Gold/Silver boss rows; {blank_count} existing blank rows available.")
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        stage_csv = tmp_path / "goldsilver_event_boss_stage.csv"
        sql_file = tmp_path / "update_goldsilver_event_bosses.sql"
        write_stage_csv(stage_csv, rows)
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
