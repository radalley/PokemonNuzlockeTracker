"""Export/load curated trainer placements as a repo-committed CSV.

curated_trainer_placements is durable human data, but it lives in one
database. The CSV under etl/curation_data/ is its portable form: export
after curating on dev, commit, and load on any other database (production
launch, scratch rebuilds). Loading upserts by (version_group_id,
trainer_key), resolves area names to location_areas rows (creating them
like the admin surface does), and re-applies placements to trainer_pool.

    python -m etl.pipelines.sync_curated_placements export --version-group-id 11
    python -m etl.pipelines.sync_curated_placements load --version-group-id 11 --apply
"""
import argparse
import csv
import sys
from pathlib import Path

from .. import curation, db

DATA_DIR = Path(__file__).resolve().parent.parent / "curation_data"
COLUMNS = ["version_group_id", "trainer_key", "canonical_location_id", "area_name",
           "status", "is_rematch", "is_event", "game_id", "note"]


def csv_path(version_group_id):
    return DATA_DIR / f"vg{int(version_group_id)}.csv"


def export(version_group_id):
    sql = f"""
SELECT c.version_group_id, c.trainer_key, c.canonical_location_id,
       la.area_name, c.status, c.is_rematch, c.is_event, c.game_id, c.note
FROM curated_trainer_placements c
LEFT JOIN location_areas la ON la.area_id = c.area_id
WHERE c.version_group_id = {int(version_group_id)}
ORDER BY c.trainer_key
"""
    one_line = " ".join(sql.split())
    stdout, _ = db.run_sql(f"\\copy ({one_line}) to stdout with (format csv, header)")
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    path = csv_path(version_group_id)
    with path.open("w", encoding="utf-8", newline="") as handle:
        handle.write(stdout)
    rows = max(0, len(stdout.splitlines()) - 1)
    print(f"exported {rows} curated rows to {path}")


def _bool_literal(value):
    text = (value or "").strip().lower()
    if text in ("t", "true", "1", "yes"):
        return "true"
    if text in ("f", "false", "0", "no"):
        return "false"
    if text == "":
        return "NULL"
    raise ValueError(f"unrecognized boolean value {value!r} in curation CSV")


def _int_literal(value):
    text = (value or "").strip()
    return str(int(text)) if text else "NULL"


def _text_literal(value):
    if value is None or value == "":
        return "NULL"
    return "'" + str(value).replace("'", "''") + "'"


def load(version_group_id, apply_changes):
    path = csv_path(version_group_id)
    if not path.exists():
        print(f"no curation CSV at {path}", file=sys.stderr)
        raise SystemExit(1)
    with path.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        print(f"curation CSV at {path} has no rows", file=sys.stderr)
        raise SystemExit(1)
    bad = [r for r in rows if int(r["version_group_id"]) != int(version_group_id)]
    if bad:
        print(f"{len(bad)} rows carry a different version_group_id", file=sys.stderr)
        raise SystemExit(1)

    values = ",\n".join(
        "({vg}, {key}, {loc}, {area}, {status}, {rematch}, {event}, {game}, {note})".format(
            vg=int(r["version_group_id"]),
            key=_text_literal(r["trainer_key"]),
            loc=_int_literal(r["canonical_location_id"]),
            area=_text_literal(r.get("area_name")),
            status=_text_literal(r.get("status") or "placed"),
            rematch=_bool_literal(r.get("is_rematch")),
            event=_bool_literal(r.get("is_event")),
            game=_int_literal(r.get("game_id")),
            note=_text_literal(r.get("note")),
        )
        for r in rows
    )
    vg = int(version_group_id)
    finish = "COMMIT;" if apply_changes else "ROLLBACK;"
    sql = f"""
BEGIN;

CREATE TEMP TABLE curated_stage (
  version_group_id integer, trainer_key text, canonical_location_id integer,
  area_name text, status text, is_rematch boolean, is_event boolean,
  game_id integer, note text
) ON COMMIT DROP;

INSERT INTO curated_stage VALUES
{values};

DO $load$
BEGIN
  IF EXISTS (
    SELECT 1 FROM curated_stage s
    LEFT JOIN canon_locations cl ON cl.canonical_location_id = s.canonical_location_id
    WHERE s.canonical_location_id IS NOT NULL AND cl.canonical_location_id IS NULL
  ) THEN
    RAISE EXCEPTION 'curation CSV references unknown canonical locations';
  END IF;
  -- A placement targeting a location outside this version group's script
  -- would place the trainer somewhere no run page can ever show it.
  IF EXISTS (
    SELECT 1 FROM curated_stage s
    WHERE s.canonical_location_id IS NOT NULL
      AND NOT EXISTS (
        SELECT 1 FROM event_locations el
        WHERE el.canonical_location_id = s.canonical_location_id
          AND el.version_group_id = s.version_group_id)
  ) THEN
    RAISE EXCEPTION 'curation CSV places trainers at locations outside the version group script';
  END IF;
END
$load$;

INSERT INTO location_areas (canonical_location_id, version_group_id, area_name, area_kind)
SELECT DISTINCT s.canonical_location_id, s.version_group_id, s.area_name,
       CASE WHEN lower(s.area_name) LIKE '%gym%' THEN 'gym' ELSE 'interior' END
FROM curated_stage s
WHERE s.area_name IS NOT NULL AND s.canonical_location_id IS NOT NULL
  AND NOT EXISTS (
    SELECT 1 FROM location_areas la
    WHERE la.canonical_location_id = s.canonical_location_id
      AND coalesce(la.version_group_id, -1) = s.version_group_id
      AND la.area_name = s.area_name);

INSERT INTO curated_trainer_placements
  (version_group_id, trainer_key, canonical_location_id, area_id,
   status, is_rematch, is_event, game_id, note)
SELECT s.version_group_id, s.trainer_key, s.canonical_location_id, la.area_id,
       s.status, s.is_rematch, s.is_event, s.game_id, s.note
FROM curated_stage s
LEFT JOIN location_areas la
  ON s.area_name IS NOT NULL
  AND la.canonical_location_id = s.canonical_location_id
  AND coalesce(la.version_group_id, -1) = s.version_group_id
  AND la.area_name = s.area_name
ON CONFLICT (version_group_id, trainer_key) DO UPDATE SET
  canonical_location_id = excluded.canonical_location_id,
  area_id = excluded.area_id,
  status = excluded.status,
  is_rematch = excluded.is_rematch,
  is_event = excluded.is_event,
  game_id = excluded.game_id,
  note = excluded.note;

{curation.apply_curated_placements_sql(vg)};

SELECT 'curated_rows' AS metric, ({curation.curated_metric_sql(vg)}) AS value;
SELECT 'placed_trainers' AS metric,
       (SELECT count(*) FROM trainer_pool
        WHERE version_group_id = {vg} AND canonical_location_id IS NOT NULL) AS value;
-- Curated keys with no matching trainer are dead rows (typo or stale
-- extraction); nonzero deserves a look, though it is not fatal because
-- curation may legitimately predate a re-extraction.
SELECT 'curated_keys_without_trainer' AS metric,
       (SELECT count(*) FROM curated_trainer_placements c
        WHERE c.version_group_id = {vg}
          AND NOT EXISTS (SELECT 1 FROM trainer_pool tp
                          WHERE tp.version_group_id = c.version_group_id
                            AND tp.encounter_name = c.trainer_key)) AS value;

{finish}
"""
    try:
        stdout, stderr = db.run_sql(sql)
    except db.PsqlError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1)
    print(stdout.strip())
    if stderr.strip():
        print(stderr.strip())
    print("Committed." if apply_changes else "Dry run complete. Transaction rolled back.")


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("command", choices=["export", "load"])
    parser.add_argument("--version-group-id", type=int, required=True)
    parser.add_argument("--apply", action="store_true", help="load: commit; default is a dry run.")
    args = parser.parse_args()
    if args.command == "export":
        export(args.version_group_id)
    else:
        load(args.version_group_id, args.apply)


if __name__ == "__main__":
    main()
