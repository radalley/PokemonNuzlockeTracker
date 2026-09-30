import csv
import re
import subprocess
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parent
DECOMP_ROOT = Path(r"C:\Users\radal\Lockley Game Decomps\pokecrystal-master\pokecrystal-master")
PSQL = Path(r"C:\Program Files\PostgreSQL\18\bin\psql.exe")


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


def parse_trainer_classes():
    classes = []
    for line in (DECOMP_ROOT / "constants" / "trainer_constants.asm").read_text(encoding="utf-8", errors="replace").splitlines():
        match = re.search(r"trainerclass\s+(\w+)", line)
        if match and match.group(1) != "TRAINER_NONE":
            classes.append(match.group(1))
    return classes


def parse_trainer_pics():
    pics = []
    for line in (DECOMP_ROOT / "data" / "trainers" / "pic_pointers.asm").read_text(encoding="utf-8", errors="replace").splitlines():
        match = re.search(r"dba_pic\s+(\w+)Pic", line)
        if match:
            pics.append(match.group(1))
    return pics


def build_rows():
    classes = parse_trainer_classes()
    pics = parse_trainer_pics()
    if len(classes) != len(pics):
        raise RuntimeError(f"Trainer class/pic count mismatch: {len(classes)} classes, {len(pics)} pics")
    return [
        {
            "trainer_class": f"TRAINER_CLASS_{trainer_class}",
            "trainer_pic": f"TRAINER_PIC_{camel_to_upper_snake(pic)}",
        }
        for trainer_class, pic in zip(classes, pics)
    ]


def write_csv(path, rows):
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=["trainer_class", "trainer_pic"])
        writer.writeheader()
        writer.writerows(rows)


def build_sql(stage_csv):
    return f"""
BEGIN;

CREATE TEMP TABLE crystal_trainer_pic_stage (
  trainer_class text,
  trainer_pic text
) ON COMMIT DROP;

\\copy crystal_trainer_pic_stage FROM '{stage_csv.as_posix()}' WITH (FORMAT csv, HEADER true)

UPDATE trainer_pool tp
SET trainer_pic = s.trainer_pic
FROM crystal_trainer_pic_stage s
WHERE tp.trainer_class = s.trainer_class
  AND tp.version_group_id = 4
  AND tp.load_build = 4;

SELECT 'updated_crystal_trainer_pic_rows' AS metric, count(*) AS value
FROM trainer_pool
WHERE version_group_id = 4
  AND load_build = 4
  AND trainer_pic LIKE 'TRAINER_PIC_%';

COMMIT;
"""


def main():
    rows = build_rows()
    database_url = read_database_url()
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        stage_csv = tmp_path / "crystal_trainer_pic_stage.csv"
        sql_file = tmp_path / "update_crystal_gen2_trainer_pics.sql"
        write_csv(stage_csv, rows)
        sql_file.write_text(build_sql(stage_csv), encoding="utf-8")
        result = subprocess.run(
            [str(PSQL), database_url, "-X", "-v", "ON_ERROR_STOP=1", "-P", "pager=off", "-f", str(sql_file)],
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        print(result.stdout)
        if result.stderr:
            print(result.stderr)


if __name__ == "__main__":
    main()
