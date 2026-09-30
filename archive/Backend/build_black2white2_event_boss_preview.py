import csv
import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parent
OUT_DIR = ROOT / "black2white2_build6_preview"
PSQL = Path(r"C:\Program Files\PostgreSQL\18\bin\psql.exe")
VERSION_GROUP_ID = 14
LOAD_BUILD = 6
BLACK2_GAME_ID = 21
WHITE2_GAME_ID = 22


def database_url():
    for line in (ROOT / ".env").read_text(encoding="utf-8", errors="replace").splitlines():
        match = re.match(r"\s*DATABASE_URL\s*=\s*(.+?)\s*$", line)
        if match:
            return match.group(1).strip().strip("\"'")
    raise RuntimeError("DATABASE_URL was not found in Backend/.env")


def psql_rows(sql):
    result = subprocess.run(
        [str(PSQL), database_url(), "-X", "-A", "-F", "\t", "-P", "pager=off", "-c", sql],
        check=True, capture_output=True, text=True, encoding="utf-8",
    )
    lines = [line for line in result.stdout.splitlines() if line and not line.startswith("(")]
    if not lines:
        return []
    header = lines[0].split("\t")
    return [dict(zip(header, line.split("\t"))) for line in lines[1:] if "\t" in line]


def boss(index, sort_order, title, starter="", game_id="", event_type=""):
    return {
        "trainer_index": index, "sort_order": sort_order, "encounter_title": title,
        "starter": starter, "type_focus": "", "version_group_id": VERSION_GROUP_ID,
        "event_type": event_type, "game_id": game_id, "badge_id": "",
    }


def rival(indexes, sort_order, title):
    # Hugh always chooses the starter with a type advantage over the player.
    return [boss(index, sort_order, title, starter, event_type="Rival")
            for index, starter in zip(indexes, ("Grass", "Fire", "Water"))]


def build_rows():
    rows = []
    rows += rival((161, 162, 163), "1.1", "Aspertia City")
    rows += rival((166, 167, 168), "5.1", "Floccesy Ranch")
    rows.append(boss(156, "5.2", "Aspertia City Gym"))
    rows.append(boss(157, "6.1", "Virbank City Gym"))
    rows.append(boss(154, "9.1", "Castelia City Gym"))
    rows.append(boss(358, "11.1", "Route 4"))
    rows.append(boss(153, "13.1", "Nimbasa City Gym"))
    rows.append(boss(158, "18.1", "Driftveil City Gym"))
    rows += rival((368, 369, 370), "18.2", "Driftveil City")
    rows.append(boss(155, "21.1", "Mistralton City Gym"))
    rows += rival((378, 379, 380), "26.1", "Undella Town")
    rows.append(boss(704, "28.1", "Lacunosa Town"))
    rows.append(boss(159, "31.1", "Opelucid City Gym"))
    rows.append(boss(584, "31.2", "Opelucid City"))
    rows.append(boss(583, "31.3", "Opelucid City - Shadow Triad"))
    rows.append(boss(160, "35.1", "Humilau City Gym"))
    rows += rival((794, 795, 796), "36.1", "Route 22")
    rows.append(boss(347, "37.1", "Plasma Frigate"))
    rows.append(boss(348, "37.2", "Plasma Frigate - Shadow Triad"))
    rows.append(boss(344, "37.3", "Plasma Frigate"))
    rows.append(boss(345, "37.4", "Giant Chasm"))
    rows += rival((684, 685, 686), "39.1", "Victory Road")
    rows.append(boss(38, "39.2", "Elite Four - Shauntal"))
    rows.append(boss(39, "39.3", "Elite Four - Marshal"))
    rows.append(boss(40, "39.4", "Elite Four - Grimsley"))
    rows.append(boss(41, "39.5", "Elite Four - Caitlin"))
    rows.append(boss(341, "39.6", "Champion"))

    # Postgame encounters follow the complete event-location journey.
    rows.append(boss(5, "62.1", "Dragonspiral Tower", game_id=BLACK2_GAME_ID))
    rows.append(boss(6, "62.1", "Dragonspiral Tower", game_id=WHITE2_GAME_ID))
    rows += rival((693, 694, 695), "62.2", "Undella Town - Postgame")
    rows += rival((696, 697, 698), "62.3", "Driftveil City - Rematch")
    rows.append(boss(782, "62.4", "N's Castle - Spring"))
    rows.append(boss(783, "62.5", "N's Castle - Summer"))
    rows.append(boss(784, "62.6", "N's Castle - Autumn"))
    rows.append(boss(785, "62.7", "N's Castle - Winter"))
    rows.append(boss(456, "62.8", "Undella Town - Cynthia"))
    rows.append(boss(582, "62.9", "Floccesy Town - Alder"))
    rows.append(boss(140, "63.1", "Castelia City - Morimoto"))
    rows.append(boss(591, "63.2", "Castelia City - Nishino"))
    rows.append(boss(202, "63.3", "Black Tower", game_id=BLACK2_GAME_ID))
    rows.append(boss(201, "63.3", "White Treehollow", game_id=WHITE2_GAME_ID))
    return rows


def main():
    trainers = psql_rows(
        f"""select trainer_id, encounter_name, trainer_name,
                    substring(details from 'black2white2_trainer_index=([0-9]+)') as trainer_index
               from trainer_pool
              where version_group_id={VERSION_GROUP_ID} and load_build={LOAD_BUILD}"""
    )
    by_index = {int(row["trainer_index"]): row for row in trainers if row["trainer_index"]}
    output = []
    for row in build_rows():
        trainer = by_index.get(row["trainer_index"])
        if not trainer:
            raise ValueError(f"Trainer index {row['trainer_index']} was not loaded")
        output.append({
            "trainer_id": trainer["trainer_id"], "trainer_index": row["trainer_index"],
            "encounter_name": trainer["encounter_name"], "trainer_name": trainer["trainer_name"],
            "sort_order": row["sort_order"], "encounter_title": row["encounter_title"],
            "starter": row["starter"], "type_focus": row["type_focus"],
            "version_group_id": row["version_group_id"], "event_type": row["event_type"],
            "game_id": row["game_id"], "badge_id": row["badge_id"],
        })
    keys = [(row["trainer_id"], row["sort_order"], row["starter"], row["game_id"]) for row in output]
    if len(keys) != len(set(keys)):
        raise ValueError("Duplicate event-boss keys were generated")
    fields = list(output[0])
    with (OUT_DIR / "event_bosses_preview.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(output)
    print(f"event_bosses_preview rows: {len(output)}")
    print(f"starter-specific rows: {sum(bool(row['starter']) for row in output)}")
    print(f"game-specific rows: {sum(bool(row['game_id']) for row in output)}")


if __name__ == "__main__":
    main()
