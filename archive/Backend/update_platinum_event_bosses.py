import argparse
import csv
import re
import subprocess
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parent
PSQL = Path(r"C:\Program Files\PostgreSQL\18\bin\psql.exe")
VERSION_GROUP_ID = 9
LOAD_BUILD = 5


STARTERS = {
    "PIPLUP": "Water",
    "TURTWIG": "Grass",
    "CHIMCHAR": "Fire",
}


BOSS_ROWS = [
    ("TRAINER_RIVAL_ROUTE_201_{starter}", "2.1", "Route 201", "{starter_label}", "Rival"),
    ("TRAINER_RIVAL_ROUTE_203_{starter}", "5.1", "Route 203", "{starter_label}", "Rival"),
    ("TRAINER_LEADER_ROARK", "7.1", "Oreburgh City Gym", None, ""),
    ("TRAINER_COMMANDER_MARS_VALLEY_WINDWORKS", "14.1", "Valley Windworks", None, ""),
    ("TRAINER_LEADER_GARDENIA", "17.1", "Eterna City Gym", None, ""),
    ("TRAINER_COMMANDER_JUPITER_TEAM_GALACTIC_ETERNA_BUILDING", "17.2", "Team Galactic Eterna Building", None, ""),
    ("TRAINER_LEADER_FANTINA", "22.1", "Hearthome City Gym", None, ""),
    ("TRAINER_RIVAL_ROUTE_209_{starter}", "23.1", "Route 209", "{starter_label}", "Rival"),
    ("TRAINER_LEADER_MAYLENE", "28.1", "Veilstone City Gym", None, ""),
    ("TRAINER_LEADER_WAKE", "33.1", "Pastoria City Gym", None, ""),
    ("TRAINER_RIVAL_PASTORIA_CITY_{starter}", "33.2", "Pastoria City", "{starter_label}", "Rival"),
    ("TRAINER_COMMANDER_SATURN_VALOR_CAVERN", "33.3", "Valor Cavern", None, ""),
    ("TRAINER_GALACTIC_BOSS_CYRUS_CELESTIC_TOWN_RUINS", "37.1", "Celestic Town", None, ""),
    ("TRAINER_RIVAL_CANALAVE_CITY_{starter}", "43.1", "Canalave City", "{starter_label}", "Rival"),
    ("TRAINER_LEADER_BYRON", "43.2", "Canalave City Gym", None, ""),
    ("TRAINER_COMMANDER_MARS_LAKE_VERITY", "43.3", "Lake Verity", None, ""),
    ("TRAINER_LEADER_CANDICE", "49.1", "Snowpoint City Gym", None, ""),
    ("TRAINER_GALACTIC_BOSS_CYRUS_GALACTIC_HQ", "49.2", "Galactic HQ", None, ""),
    ("TRAINER_COMMANDER_SATURN_GALACTIC_HQ", "49.3", "Galactic HQ", None, ""),
    ("TRAINER_COMMANDER_MARS_SPEAR_PILLAR", "49.4", "Spear Pillar", None, ""),
    ("TRAINER_COMMANDER_JUPITER_SPEAR_PILLAR", "49.5", "Spear Pillar", None, ""),
    ("TRAINER_GALACTIC_BOSS_CYRUS_DISTORTION_WORLD", "50.1", "Distortion World", None, ""),
    ("TRAINER_LEADER_VOLKNER", "52.1", "Sunyshore City Gym", None, ""),
    ("TRAINER_RIVAL_POKEMON_LEAGUE_{starter}", "55.1", "Pokemon League", "{starter_label}", "Rival"),
    ("TRAINER_ELITE_FOUR_AARON", "55.2", "Elite Four", None, ""),
    ("TRAINER_ELITE_FOUR_BERTHA", "55.3", "Elite Four", None, ""),
    ("TRAINER_ELITE_FOUR_FLINT", "55.4", "Elite Four", None, ""),
    ("TRAINER_ELITE_FOUR_LUCIAN", "55.5", "Elite Four", None, ""),
    ("TRAINER_CHAMPION_CYNTHIA", "55.6", "Champion", None, ""),
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


def expanded_boss_rows():
    rows = []
    for encounter_template, sort_order, title, starter_template, event_type in BOSS_ROWS:
        if "{starter}" in encounter_template:
            for starter_key, starter_label in STARTERS.items():
                rows.append(
                    (
                        encounter_template.format(starter=starter_key),
                        sort_order,
                        title,
                        starter_template.format(starter_label=starter_label),
                        event_type,
                    )
                )
        else:
            rows.append((encounter_template, sort_order, title, starter_template or "", event_type))
    return rows


def build_stage_rows():
    existing = psql_rows(f"select count(*) as count from event_bosses where version_group_id = {VERSION_GROUP_ID}")
    if int(existing[0]["count"]) > 0:
        raise RuntimeError("Platinum event_bosses already exist; refusing to add duplicates.")

    trainer_rows = psql_rows(
        f"""
        select encounter_name, trainer_id
        from trainer_pool
        where version_group_id = {VERSION_GROUP_ID}
          and load_build = {LOAD_BUILD}
        """
    )
    trainer_id_by_encounter = {row["encounter_name"]: int(row["trainer_id"]) for row in trainer_rows}
    boss_rows = expanded_boss_rows()
    missing = [encounter for encounter, *_ in boss_rows if encounter not in trainer_id_by_encounter]
    if missing:
        raise RuntimeError(f"Missing Platinum trainer_pool rows: {', '.join(missing)}")

    max_event_id = int(psql_rows("select coalesce(max(event_id), 0) as max_event_id from event_bosses")[0]["max_event_id"])
    rows = []
    for index, (encounter_name, sort_order, encounter_title, starter, event_type) in enumerate(boss_rows, 1):
        rows.append(
            {
                "row_num": index,
                "event_id": max_event_id + index,
                "trainer_id": trainer_id_by_encounter[encounter_name],
                "encounter_name": encounter_name,
                "sort_order": sort_order,
                "encounter_title": encounter_title,
                "starter": starter,
                "event_type": event_type,
                "version_group_id": VERSION_GROUP_ID,
            }
        )
    return rows


def write_stage_csv(path, rows):
    fieldnames = [
        "row_num",
        "event_id",
        "trainer_id",
        "encounter_name",
        "sort_order",
        "encounter_title",
        "starter",
        "event_type",
        "version_group_id",
    ]
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def build_sql(stage_csv, rollback):
    end_sql = "ROLLBACK;" if rollback else "COMMIT;"
    return f"""
BEGIN;

CREATE TEMP TABLE platinum_event_boss_stage (
  row_num integer,
  event_id integer,
  trainer_id integer,
  encounter_name text,
  sort_order text,
  encounter_title text,
  starter text,
  event_type text,
  version_group_id integer
) ON COMMIT DROP;

\\copy platinum_event_boss_stage FROM '{stage_csv.as_posix()}' WITH (FORMAT csv, HEADER true)

SELECT 'stage_rows' AS metric, count(*) AS value FROM platinum_event_boss_stage;

INSERT INTO event_bosses (
  event_id, trainer_id, sort_order, encounter_title, starter, version_group_id, event_type
)
SELECT
  s.event_id,
  s.trainer_id,
  s.sort_order,
  s.encounter_title,
  nullif(s.starter, ''),
  s.version_group_id,
  nullif(s.event_type, '')
FROM platinum_event_boss_stage s
WHERE NOT EXISTS (
  SELECT 1
  FROM event_bosses eb
  WHERE eb.version_group_id = s.version_group_id
    AND eb.trainer_id = s.trainer_id
    AND eb.sort_order = s.sort_order
    AND coalesce(eb.starter, '') = coalesce(nullif(s.starter, ''), '')
)
ORDER BY s.row_num;

SELECT 'vg9_event_bosses_after' AS metric, count(*) AS value
FROM event_bosses
WHERE version_group_id = {VERSION_GROUP_ID};

{end_sql}
"""


def write_preview(path, rows):
    fieldnames = [
        "row_num",
        "event_id",
        "trainer_id",
        "encounter_name",
        "sort_order",
        "encounter_title",
        "starter",
        "event_type",
        "version_group_id",
    ]
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(description="Populate Platinum event_bosses from loaded trainer_pool rows.")
    parser.add_argument("--apply", action="store_true", help="Commit changes. Without this flag, rolls back.")
    args = parser.parse_args()

    rows = build_stage_rows()
    preview_path = ROOT / "platinum_build5_preview" / "event_bosses_preview.csv"
    preview_path.parent.mkdir(parents=True, exist_ok=True)
    write_preview(preview_path, rows)
    print(f"Prepared {len(rows)} Platinum boss rows.")
    print(f"Wrote {preview_path}")

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        stage_csv = tmp_path / "platinum_event_boss_stage.csv"
        sql_file = tmp_path / "update_platinum_event_bosses.sql"
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
