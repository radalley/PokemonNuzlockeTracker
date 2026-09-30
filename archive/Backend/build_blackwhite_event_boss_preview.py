import csv
import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parent
OUT_DIR = ROOT / "blackwhite_build6_preview"
PSQL = Path(r"C:\Program Files\PostgreSQL\18\bin\psql.exe")
VERSION_GROUP_ID = 11
LOAD_BUILD = 6
BLACK_GAME_ID = 17
WHITE_GAME_ID = 18


def database_url():
    for line in (ROOT / ".env").read_text(encoding="utf-8", errors="replace").splitlines():
        match = re.match(r"\s*DATABASE_URL\s*=\s*(.+?)\s*$", line)
        if match:
            return match.group(1).strip().strip("\"'")
    raise RuntimeError("DATABASE_URL was not found in Backend/.env")


def psql_rows(sql):
    result = subprocess.run(
        [str(PSQL), database_url(), "-X", "-A", "-F", "\t", "-P", "pager=off", "-c", sql],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    lines = [line for line in result.stdout.splitlines() if line and not line.startswith("(")]
    if not lines:
        return []
    header = lines[0].split("\t")
    return [dict(zip(header, line.split("\t"))) for line in lines[1:] if "\t" in line]


def load_trainers():
    rows = psql_rows(
        f"""
        select trainer_id, encounter_name, trainer_name, trainer_class,
               substring(details from 'blackwhite_trainer_index=([0-9]+)') as trainer_index
        from trainer_pool
        where version_group_id = {VERSION_GROUP_ID}
          and load_build = {LOAD_BUILD}
        order by trainer_id
        """
    )
    trainers = {}
    for row in rows:
        if row["trainer_index"]:
            trainers[int(row["trainer_index"])] = row
    if len(trainers) != 615:
        raise ValueError(f"Expected 615 indexed Black/White trainers, found {len(trainers)}")
    return trainers


def boss(index, sort_order, title, starter="", game_id="", event_type=""):
    return {
        "trainer_index": index,
        "sort_order": sort_order,
        "encounter_title": title,
        "starter": starter,
        "type_focus": "",
        "version_group_id": VERSION_GROUP_ID,
        "event_type": event_type,
        "game_id": game_id,
        "badge_id": "",
    }


def starter_trio(indexes, sort_order, title, starters):
    return [boss(index, sort_order, title, starter) for index, starter in zip(indexes, starters)]


def build_rows():
    rows = []
    cheren_starters = ("Grass", "Fire", "Water")
    bianca_starters = ("Grass", "Fire", "Water")

    rows += starter_trio((53, 54, 55), "0.1", "Rival - Cheren", cheren_starters)
    rows += starter_trio((59, 60, 61), "0.2", "Rival - Bianca", bianca_starters)
    rows.append(boss(64, "1.1", "N - Accumula Town"))
    rows += starter_trio((498, 499, 500), "2.1", "Rival - Bianca", bianca_starters)
    rows += starter_trio((287, 288, 289), "2.2", "Rival - Cheren", cheren_starters)

    # The Striaton leader counters the user's starter.
    rows += starter_trio((11, 13, 12), "3.1", "Striaton City Gym", ("Grass", "Fire", "Water"))
    rows += starter_trio((56, 57, 58), "5.1", "Rival - Cheren", cheren_starters)
    rows.append(boss(65, "6.1", "N - Nacrene City"))
    rows.append(boss(21, "7.1", "Nacrene City Gym"))
    rows.append(boss(22, "9.1", "Castelia City Gym"))
    rows += starter_trio((507, 508, 509), "10.1", "Rival - Bianca", bianca_starters)
    rows += starter_trio((403, 404, 405), "10.2", "Rival - Cheren", cheren_starters)
    rows.append(boss(89, "10.3", "N - Nimbasa City"))
    rows.append(boss(23, "10.4", "Nimbasa City Gym"))
    rows += starter_trio((90, 91, 92), "13.1", "Rival - Cheren", cheren_starters)
    rows.append(boss(24, "16.1", "Driftveil City Gym"))
    rows += starter_trio((491, 492, 493), "16.2", "Rival - Bianca", bianca_starters)
    rows.append(boss(218, "19.1", "N - Chargestone Cave"))
    rows.append(boss(25, "24.1", "Mistralton City Gym"))
    rows += starter_trio((539, 540, 541), "25.1", "Rival - Cheren", cheren_starters)
    rows.append(boss(131, "26.1", "Icirrus City Gym"))
    rows += starter_trio((494, 495, 496), "28.1", "Rival - Bianca", bianca_starters)
    rows.append(boss(133, "30.1", "Opelucid City Gym", game_id=BLACK_GAME_ID))
    rows.append(boss(132, "30.1", "Opelucid City Gym", game_id=WHITE_GAME_ID))
    rows += starter_trio((588, 589, 590), "31.1", "Rival - Cheren", cheren_starters)
    rows.append(boss(228, "32.1", "Elite Four - Shauntal"))
    rows.append(boss(229, "32.2", "Elite Four - Marshal"))
    rows.append(boss(230, "32.3", "Elite Four - Grimsley"))
    rows.append(boss(231, "32.4", "Elite Four - Caitlin"))
    rows.append(boss(587, "32.5", "N's Castle", game_id=BLACK_GAME_ID))
    rows.append(boss(586, "32.5", "N's Castle", game_id=WHITE_GAME_ID))
    rows.append(boss(232, "32.6", "N's Castle - Ghetsis"))

    # Postgame bosses, ordered after the main event-location journey.
    rows.append(boss(567, "37.1", "Undella Town - Cynthia"))
    rows.append(boss(407, "46.1", "Champion - Alder"))
    rows.append(boss(542, "46.2", "Castelia City - Morimoto"))
    return rows


def main():
    trainers = load_trainers()
    rows = build_rows()
    output = []
    for row in rows:
        trainer = trainers.get(row["trainer_index"])
        if not trainer:
            raise ValueError(f"Trainer index {row['trainer_index']} was not loaded")
        output.append(
            {
                "trainer_id": trainer["trainer_id"],
                "trainer_index": row["trainer_index"],
                "encounter_name": trainer["encounter_name"],
                "trainer_name": trainer["trainer_name"],
                "sort_order": row["sort_order"],
                "encounter_title": row["encounter_title"],
                "starter": row["starter"],
                "type_focus": row["type_focus"],
                "version_group_id": row["version_group_id"],
                "event_type": row["event_type"],
                "game_id": row["game_id"],
                "badge_id": row["badge_id"],
            }
        )

    keys = [(row["trainer_id"], row["sort_order"], row["starter"], row["game_id"]) for row in output]
    if len(keys) != len(set(keys)):
        raise ValueError("Duplicate event-boss keys were generated")
    if any(row["version_group_id"] != VERSION_GROUP_ID for row in output):
        raise ValueError("Unexpected version group in event-boss preview")

    fields = [
        "trainer_id", "trainer_index", "encounter_name", "trainer_name", "sort_order",
        "encounter_title", "starter", "type_focus", "version_group_id", "event_type",
        "game_id", "badge_id",
    ]
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with (OUT_DIR / "event_bosses_preview.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(output)

    print(f"event_bosses_preview rows: {len(output)}")
    print(f"starter-specific rows: {sum(bool(row['starter']) for row in output)}")
    print(f"game-specific rows: {sum(bool(row['game_id']) for row in output)}")
    print(f"output: {OUT_DIR / 'event_bosses_preview.csv'}")


if __name__ == "__main__":
    main()
