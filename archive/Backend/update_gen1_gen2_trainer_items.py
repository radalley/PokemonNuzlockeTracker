import argparse
import csv
import re
import subprocess
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parent
PSQL = Path(r"C:\Program Files\PostgreSQL\18\bin\psql.exe")

GEN1_DECOMPS = {
    1: Path(r"C:\Users\radal\Lockley Game Decomps\pokered-master\pokered-master"),
    2: Path(r"C:\Users\radal\Lockley Game Decomps\pokeyellow-master\pokeyellow-master"),
}
GEN2_DECOMPS = {
    3: Path(r"C:\Users\radal\Lockley Game Decomps\pokegold-master\pokegold-master"),
    4: Path(r"C:\Users\radal\Lockley Game Decomps\pokecrystal-master\pokecrystal-master"),
}

AI_ITEM_MAP = {
    "AIUseFullRestore": "ITEM_FULL_RESTORE",
    "AIUsePotion": "ITEM_POTION",
    "AIUseSuperPotion": "ITEM_SUPER_POTION",
    "AIUseHyperPotion": "ITEM_HYPER_POTION",
    "AIUseFullHeal": "ITEM_FULL_HEAL",
    "AIUseXAccuracy": "ITEM_X_ACCURACY",
    "AIUseGuardSpec": "ITEM_GUARD_SPEC",
    "AIUseDireHit": "ITEM_DIRE_HIT",
    "AIUseXAttack": "ITEM_X_ATTACK",
    "AIUseXDefend": "ITEM_X_DEFEND",
    "AIUseXSpeed": "ITEM_X_SPEED",
    "AIUseXSpecial": "ITEM_X_SPECIAL",
}


def read_database_url():
    env_path = ROOT / ".env"
    if not env_path.exists():
        raise RuntimeError("Backend/.env not found")
    for line in env_path.read_text(encoding="utf-8", errors="replace").splitlines():
        match = re.match(r"\s*DATABASE_URL\s*=\s*(.+?)\s*$", line)
        if match:
            return match.group(1).strip().strip("\"'")
    raise RuntimeError("DATABASE_URL was not found in Backend/.env")


def camel_to_upper_snake(value):
    value = re.sub(r"([a-z])([A-Z])", r"\1_\2", value)
    value = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", value)
    return value.upper()


def item_key(value):
    if not value or value in {"NO_ITEM", "ITEM_NONE"}:
        return ""
    return value if value.startswith("ITEM_") else f"ITEM_{value}"


def parse_gen2_classes(decomp_root):
    classes = []
    for line in (decomp_root / "constants" / "trainer_constants.asm").read_text(encoding="utf-8", errors="replace").splitlines():
        clean = line.split(";", 1)[0].strip()
        match = re.match(r"trainerclass\s+(\w+)", clean)
        if match and match.group(1) != "TRAINER_NONE":
            classes.append(match.group(1))
    return classes


def parse_gen2_items(version_group_id, decomp_root, load_build):
    classes = parse_gen2_classes(decomp_root)
    rows = []
    class_index = 0
    for line in (decomp_root / "data" / "trainers" / "attributes.asm").read_text(encoding="utf-8", errors="replace").splitlines():
        clean = line.split(";", 1)[0].strip()
        match = re.match(r"db\s+([^,]+),\s*([^,]+)\s*$", clean)
        if not match or class_index >= len(classes):
            continue
        items = [item_key(match.group(1).strip()), item_key(match.group(2).strip())]
        items = [item for item in items if item]
        if items:
            rows.append({
                "version_group_id": version_group_id,
                "load_build": load_build,
                "trainer_class": f"TRAINER_CLASS_{classes[class_index]}",
                "trainer_items": ",".join(items),
            })
        class_index += 1
    return rows


def parse_gen1_classes(decomp_root):
    classes = []
    for line in (decomp_root / "constants" / "trainer_constants.asm").read_text(encoding="utf-8", errors="replace").splitlines():
        clean = line.split(";", 1)[0].strip()
        match = re.match(r"trainer_const\s+(\w+)", clean)
        if match and match.group(1) != "NOBODY":
            classes.append(match.group(1))
    return classes


def parse_gen1_ai_pointers(decomp_root, classes):
    rows = []
    pointer_lines = []
    for line in (decomp_root / "data" / "trainers" / "ai_pointers.asm").read_text(encoding="utf-8", errors="replace").splitlines():
        clean = line.split(";", 1)[0].strip()
        match = re.match(r"dbw\s+(\d+),\s*(\w+)", clean)
        if match:
            pointer_lines.append((int(match.group(1)), match.group(2)))
    for trainer_class, (ai_count, routine) in zip(classes, pointer_lines):
        rows.append({"trainer_class": trainer_class, "ai_count": ai_count, "routine": routine})
    return rows


def parse_ai_routine_items(decomp_root):
    lines = (decomp_root / "engine" / "battle" / "trainer_ai.asm").read_text(encoding="utf-8", errors="replace").splitlines()
    routines = {}
    current = None
    body = []
    for line in lines:
        if "end of individual trainer AI routines" in line:
            if current:
                routines[current] = body
            current = None
            body = []
            break
        clean = line.split(";", 1)[0].strip()
        match = re.match(r"^(\w+AI):$", clean)
        if match:
            if current:
                routines[current] = body
            current = match.group(1)
            body = []
            continue
        if current:
            body.append(clean)
    if current:
        routines[current] = body

    result = {}
    for routine, body_lines in routines.items():
        items = []
        for clean in body_lines:
            for ai_func, item in AI_ITEM_MAP.items():
                if re.search(rf"\b{ai_func}\b", clean) and item not in items:
                    items.append(item)
        result[routine] = items
    return result


def parse_gen1_items(version_group_id, decomp_root, load_build):
    classes = parse_gen1_classes(decomp_root)
    ai_rows = parse_gen1_ai_pointers(decomp_root, classes)
    routine_items = parse_ai_routine_items(decomp_root)
    rows = []
    for row in ai_rows:
        items = routine_items.get(row["routine"], [])
        if not items:
            continue
        if len(items) == 1:
            trainer_items = ",".join([items[0]] * row["ai_count"])
        else:
            trainer_items = ",".join(items)
        rows.append({
            "version_group_id": version_group_id,
            "load_build": load_build,
            "trainer_class": f"TRAINER_CLASS_{row['trainer_class']}",
            "trainer_items": trainer_items,
        })
    return rows


def write_csv(path, rows):
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=["version_group_id", "load_build", "trainer_class", "trainer_items"])
        writer.writeheader()
        writer.writerows(rows)


def build_sql(stage_csv, rollback):
    end_sql = "ROLLBACK;" if rollback else "COMMIT;"
    return f"""
BEGIN;

CREATE TEMP TABLE trainer_item_stage (
  version_group_id integer,
  load_build integer,
  trainer_class text,
  trainer_items text
) ON COMMIT DROP;

\\copy trainer_item_stage FROM '{stage_csv.as_posix()}' WITH (FORMAT csv, HEADER true)

SELECT version_group_id, count(*) AS class_item_rows
FROM trainer_item_stage
GROUP BY version_group_id
ORDER BY version_group_id;

SELECT tp.version_group_id, count(*) AS rows_to_fill
FROM trainer_pool tp
JOIN trainer_item_stage s
  ON s.version_group_id = tp.version_group_id
 AND s.load_build = tp.load_build
 AND s.trainer_class = tp.trainer_class
WHERE tp.version_group_id IN (1, 2, 3, 4)
  AND tp.load_build = 4
  AND nullif(tp.trainer_items, '') IS NULL
GROUP BY tp.version_group_id
ORDER BY tp.version_group_id;

UPDATE trainer_pool tp
SET trainer_items = s.trainer_items
FROM trainer_item_stage s
WHERE s.version_group_id = tp.version_group_id
  AND s.load_build = tp.load_build
  AND s.trainer_class = tp.trainer_class
  AND tp.version_group_id IN (1, 2, 3, 4)
  AND tp.load_build = 4
  AND nullif(tp.trainer_items, '') IS NULL;

SELECT version_group_id, count(*) AS rows_with_items_after
FROM trainer_pool
WHERE version_group_id IN (1, 2, 3, 4)
  AND load_build = 4
  AND nullif(trainer_items, '') IS NOT NULL
GROUP BY version_group_id
ORDER BY version_group_id;

{end_sql}
"""


def main():
    parser = argparse.ArgumentParser(description="Fill Gen I/II trainer_pool.trainer_items from decomp trainer AI/attributes.")
    parser.add_argument("--apply", action="store_true", help="Commit updates. Without this flag, rolls back.")
    parser.add_argument("--load-build", type=int, default=4)
    args = parser.parse_args()

    rows = []
    for version_group_id, decomp_root in GEN1_DECOMPS.items():
        rows.extend(parse_gen1_items(version_group_id, decomp_root, args.load_build))
    for version_group_id, decomp_root in GEN2_DECOMPS.items():
        rows.extend(parse_gen2_items(version_group_id, decomp_root, args.load_build))

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        stage_csv = tmp_path / "trainer_item_stage.csv"
        sql_file = tmp_path / "update_trainer_items.sql"
        write_csv(stage_csv, rows)
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
