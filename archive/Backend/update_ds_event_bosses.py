import argparse
import csv
import re
import subprocess
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parent
PSQL = Path(r"C:\Program Files\PostgreSQL\18\bin\psql.exe")


DP_STARTERS = {
    "TURTWIG": "Water",
    "CHIMCHAR": "Grass",
    "PIPLUP": "Fire",
}

HGSS_STARTERS = {
    "CHIKORITA": "Water",
    "CYNDAQUIL": "Grass",
    "TOTODILE": "Fire",
}


CONFIG = {
    "diamondpearl": {
        "version_group_id": 8,
        "load_build": 5,
        "out_file": ROOT / "diamondpearl_build5_preview" / "event_bosses_preview.csv",
        "rows": [
            ({"TURTWIG": "TRAINER_PKMN_TRAINER_BARRY_CEDRIC", "CHIMCHAR": "TRAINER_PKMN_TRAINER_BARRY_CEDRIC_2", "PIPLUP": "TRAINER_PKMN_TRAINER_BARRY_CEDRIC_3"}, "5.1", "Route 203", "Rival", DP_STARTERS),
            ("TRAINER_LEADER_ROARK_ROARK", "7.1", "Oreburgh City Gym", "", None),
            ("TRAINER_COMMANDER_MARS_MARS", "14.1", "Valley Windworks", "", None),
            ("TRAINER_LEADER_GARDENIA_GARDENIA", "17.1", "Eterna City Gym", "", None),
            ("TRAINER_COMMANDER_JUPITER_JUPITER", "17.2", "Team Galactic Eterna Building", "", None),
            ({"TURTWIG": "TRAINER_PKMN_TRAINER_BARRY_CEDRIC_4", "CHIMCHAR": "TRAINER_PKMN_TRAINER_BARRY_CEDRIC_5", "PIPLUP": "TRAINER_PKMN_TRAINER_BARRY_CEDRIC_6"}, "22.1", "Hearthome City", "Rival", DP_STARTERS),
            ("TRAINER_LEADER_MAYLENE_MAYLENE", "28.1", "Veilstone City Gym", "", None),
            ("TRAINER_LEADER_WAKE_WAKE", "30.1", "Pastoria City Gym", "", None),
            ({"TURTWIG": "TRAINER_PKMN_TRAINER_BARRY_CEDRIC_7", "CHIMCHAR": "TRAINER_PKMN_TRAINER_BARRY_CEDRIC_8", "PIPLUP": "TRAINER_PKMN_TRAINER_BARRY_CEDRIC_9"}, "30.2", "Pastoria City", "Rival", DP_STARTERS),
            ("TRAINER_LEADER_FANTINA_FANTINA", "30.3", "Hearthome City Gym", "", None),
            ("TRAINER_COMMANDER_SATURN_SATURN", "35.1", "Lake Valor", "", None),
            ({"TURTWIG": "TRAINER_PKMN_TRAINER_BARRY_CEDRIC_10", "CHIMCHAR": "TRAINER_PKMN_TRAINER_BARRY_CEDRIC_11", "PIPLUP": "TRAINER_PKMN_TRAINER_BARRY_CEDRIC_12"}, "46.1", "Canalave City", "Rival", DP_STARTERS),
            ("TRAINER_LEADER_BYRON_BYRON", "46.2", "Canalave City Gym", "", None),
            ("TRAINER_COMMANDER_MARS_MARS_2", "46.3", "Lake Verity", "", None),
            ("TRAINER_LEADER_CANDICE_CANDICE", "52.1", "Snowpoint City Gym", "", None),
            ("TRAINER_GALACTIC_BOSS_CYRUS", "52.2", "Galactic HQ", "", None),
            ("TRAINER_COMMANDER_SATURN_SATURN_2", "52.3", "Galactic HQ", "", None),
            ("TRAINER_COMMANDER_MARS_MARS_3", "52.4", "Spear Pillar", "", None),
            ("TRAINER_COMMANDER_JUPITER_JUPITER_2", "52.5", "Spear Pillar", "", None),
            ("TRAINER_GALACTIC_BOSS_CYRUS_2", "52.6", "Spear Pillar", "", None),
            ("TRAINER_LEADER_VOLKNER_VOLKNER", "55.1", "Sunyshore City Gym", "", None),
            ({"TURTWIG": "TRAINER_PKMN_TRAINER_BARRY_CEDRIC_13", "CHIMCHAR": "TRAINER_PKMN_TRAINER_BARRY_CEDRIC_14", "PIPLUP": "TRAINER_PKMN_TRAINER_BARRY_CEDRIC_15"}, "58.1", "Pokemon League", "Rival", DP_STARTERS),
            ("TRAINER_ELITE_FOUR_AARON_AARON", "58.2", "Elite Four", "", None),
            ("TRAINER_ELITE_FOUR_BERTHA_BERTHA", "58.3", "Elite Four", "", None),
            ("TRAINER_ELITE_FOUR_FLINT_FLINT", "58.4", "Elite Four", "", None),
            ("TRAINER_ELITE_FOUR_LUCIEN_LUCIAN", "58.5", "Elite Four", "", None),
            ("TRAINER_CHAMPION_CYNTHIA", "58.6", "Champion", "", None),
        ],
    },
    "heartgoldsoulsilver": {
        "version_group_id": 10,
        "load_build": 5,
        "out_file": ROOT / "heartgoldsoulsilver_build5_preview" / "event_bosses_preview.csv",
        "rows": [
            ({"CHIKORITA": "TRAINER_RIVAL_SILVER_6", "CYNDAQUIL": "TRAINER_RIVAL_SILVER_2", "TOTODILE": "TRAINER_RIVAL_SILVER_3"}, "4.1", "Cherrygrove City", "Rival", HGSS_STARTERS),
            ("TRAINER_LEADER_FALKNER_FALKNER", "8.1", "Violet City Gym", "", None),
            ("TRAINER_EXECUTIVE_PROTON_PROTON", "15.1", "Slowpoke Well", "", None),
            ("TRAINER_LEADER_BUGSY_BUGSY", "14.1", "Azalea Town Gym", "", None),
            ({"CHIKORITA": "TRAINER_RIVAL_SILVER", "CYNDAQUIL": "TRAINER_RIVAL_SILVER_7", "TOTODILE": "TRAINER_RIVAL_SILVER_10"}, "14.2", "Azalea Town", "Rival", HGSS_STARTERS),
            ("TRAINER_LEADER_WHITNEY", "18.1", "Goldenrod City Gym", "", None),
            ({"CHIKORITA": "TRAINER_RIVAL_SILVER_4", "CYNDAQUIL": "TRAINER_RIVAL_SILVER_8", "TOTODILE": "TRAINER_RIVAL_SILVER_11"}, "24.1", "Burned Tower", "Rival", HGSS_STARTERS),
            ("TRAINER_LEADER_MORTY_MORTY", "23.1", "Ecruteak City Gym", "", None),
            ("TRAINER_LEADER_CHUCK_CHUCK", "32.1", "Cianwood City Gym", "", None),
            ("TRAINER_LEADER_JASMINE_JASMINE", "32.2", "Olivine City Gym", "", None),
            ("TRAINER_EXECUTIVE_PETREL_PETREL_2", "41.1", "Rocket Hideout", "", None),
            ("TRAINER_EXECUTIVE_ARIANA_ARIANA_2", "41.2", "Rocket Hideout", "", None),
            ("TRAINER_LEADER_PRYCE_PRYCE", "41.3", "Mahogany Town Gym", "", None),
            ({"CHIKORITA": "TRAINER_RIVAL_SILVER_17", "CYNDAQUIL": "TRAINER_RIVAL_SILVER_18", "TOTODILE": "TRAINER_RIVAL_SILVER_12"}, "43.1", "Goldenrod City", "Rival", HGSS_STARTERS),
            ("TRAINER_EXECUTIVE_PETREL_PETREL", "43.2", "Radio Tower", "", None),
            ("TRAINER_EXECUTIVE_PROTON_PROTON_2", "43.3", "Radio Tower", "", None),
            ("TRAINER_EXECUTIVE_ARIANA_ARIANA", "43.4", "Radio Tower", "", None),
            ("TRAINER_EXECUTIVE_ARCHER_ARCHER", "43.5", "Radio Tower", "", None),
            ("TRAINER_LEADER_CLAIR_CLAIR", "46.1", "Blackthorn City Gym", "", None),
            ({"CHIKORITA": "TRAINER_RIVAL_SILVER_5", "CYNDAQUIL": "TRAINER_RIVAL_SILVER_9", "TOTODILE": "TRAINER_RIVAL_SILVER_13"}, "52.1", "Victory Road", "Rival", HGSS_STARTERS),
            ("TRAINER_ELITE_FOUR_WILL_WILL", "52.2", "Elite Four", "", None),
            ("TRAINER_ELITE_FOUR_KOGA_KOGA", "52.3", "Elite Four", "", None),
            ("TRAINER_ELITE_FOUR_BRUNO_BRUNO", "52.4", "Elite Four", "", None),
            ("TRAINER_ELITE_FOUR_KAREN_KAREN", "52.5", "Elite Four", "", None),
            ("TRAINER_CHAMPION_LANCE", "52.6", "Champion", "", None),
            ("TRAINER_LEADER_LT_SURGE_LT__SURGE", "53.1", "Vermilion City Gym", "", None),
            ("TRAINER_LEADER_SABRINA_SABRINA", "55.1", "Saffron City Gym", "", None),
            ("TRAINER_LEADER_ERIKA_ERIKA", "57.1", "Celadon City Gym", "", None),
            ("TRAINER_LEADER_JANINE_JANINE", "61.1", "Fuchsia City Gym", "", None),
            ("TRAINER_LEADER_MISTY_MISTY", "73.1", "Cerulean City Gym", "", None),
            ("TRAINER_LEADER_BROCK_BROCK", "78.1", "Pewter City Gym", "", None),
            ({"CHIKORITA": "TRAINER_RIVAL_SILVER_14", "CYNDAQUIL": "TRAINER_RIVAL_SILVER_15", "TOTODILE": "TRAINER_RIVAL_SILVER_16"}, "80.1", "Mt. Moon", "Rival", HGSS_STARTERS),
            ("TRAINER_LEADER_BLAINE_BLAINE", "87.1", "Cinnabar Island Gym", "", None),
            ("TRAINER_LEADER_BLUE_BLUE", "83.1", "Viridian City Gym", "", None),
            ("TRAINER_PKMN_TRAINER_RED_RED", "92.1", "Mt. Silver", "", None),
        ],
    },
}


def read_database_url():
    for line in (ROOT / ".env").read_text(encoding="utf-8", errors="replace").splitlines():
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


def expand_rows(config):
    rows = []
    for row in config["rows"]:
        encounter_spec, sort_order, title, event_type, starters = row
        if isinstance(encounter_spec, dict):
            for starter_key, encounter_name in encounter_spec.items():
                rows.append((encounter_name, sort_order, title, starters[starter_key], event_type))
        else:
            rows.append((encounter_spec, sort_order, title, "", event_type))
    return rows


def build_stage_rows(game_key):
    config = CONFIG[game_key]
    version_group_id = config["version_group_id"]
    load_build = config["load_build"]
    existing = psql_rows(f"select count(*) as count from event_bosses where version_group_id = {version_group_id}")
    if int(existing[0]["count"]) > 0:
        raise RuntimeError(f"event_bosses already exist for version_group_id {version_group_id}; refusing to add duplicates.")

    trainer_rows = psql_rows(
        f"""
        select encounter_name, trainer_id
        from trainer_pool
        where version_group_id = {version_group_id}
          and load_build = {load_build}
        """
    )
    trainer_id_by_encounter = {row["encounter_name"]: int(row["trainer_id"]) for row in trainer_rows}
    boss_rows = expand_rows(config)
    missing = [encounter for encounter, *_ in boss_rows if encounter not in trainer_id_by_encounter]
    if missing:
        raise RuntimeError(f"Missing trainer_pool rows: {', '.join(missing)}")

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
                "version_group_id": version_group_id,
            }
        )
    return rows


def write_csv(path, rows):
    fieldnames = ["row_num", "event_id", "trainer_id", "encounter_name", "sort_order", "encounter_title", "starter", "event_type", "version_group_id"]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def build_sql(stage_csv, version_group_id, rollback):
    end_sql = "ROLLBACK;" if rollback else "COMMIT;"
    return f"""
BEGIN;

CREATE TEMP TABLE ds_event_boss_stage (
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

\\copy ds_event_boss_stage FROM '{stage_csv.as_posix()}' WITH (FORMAT csv, HEADER true)

SELECT 'stage_rows' AS metric, count(*) AS value FROM ds_event_boss_stage;

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
FROM ds_event_boss_stage s
ORDER BY s.row_num;

SELECT 'event_bosses_after' AS metric, count(*) AS value
FROM event_bosses
WHERE version_group_id = {version_group_id};

{end_sql}
"""


def main():
    parser = argparse.ArgumentParser(description="Populate Diamond/Pearl or HGSS event_bosses.")
    parser.add_argument("game", choices=sorted(CONFIG))
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    rows = build_stage_rows(args.game)
    config = CONFIG[args.game]
    write_csv(config["out_file"], rows)
    print(f"Prepared {len(rows)} boss rows for {args.game}.")
    print(f"Wrote {config['out_file']}")

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        stage_csv = tmp_path / "ds_event_boss_stage.csv"
        sql_file = tmp_path / "update_ds_event_bosses.sql"
        write_csv(stage_csv, rows)
        sql_file.write_text(build_sql(stage_csv, config["version_group_id"], rollback=not args.apply), encoding="utf-8")
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
