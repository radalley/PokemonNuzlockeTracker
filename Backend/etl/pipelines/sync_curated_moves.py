"""Export/load the observed-moves overlay as a repo-committed CSV.

curated_trainer_moves records moves opponents were actually seen using
(ground truth over moveset inference), keyed by the stable ETL identity so
no loader ever touches it. The CSV under etl/curation_data/ is its
portable form AND the source of truth: loading mirrors the target database
to the CSV for that version group -- rows absent from the CSV are DELETED,
so removals made on dev propagate too. An empty CSV is refused (wiping a
version group's observations is a deliberate manual act, not a load).

    python -m etl.pipelines.sync_curated_moves export --version-group-id 1001
    python -m etl.pipelines.sync_curated_moves load --version-group-id 1001 --apply
"""
import argparse
import csv
import sys
from pathlib import Path

from .. import db

DATA_DIR = Path(__file__).resolve().parent.parent / "curation_data"


def csv_path(version_group_id):
    return DATA_DIR / f"vg{int(version_group_id)}_moves.csv"


def export(version_group_id):
    sql = f"""
SELECT version_group_id, trainer_key, slot, species_name, move_name, noted_at, note
FROM curated_trainer_moves
WHERE version_group_id = {int(version_group_id)}
ORDER BY trainer_key, slot, move_name
"""
    one_line = " ".join(sql.split())
    stdout, _ = db.run_sql(f"\\copy ({one_line}) to stdout with (format csv, header)")
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    path = csv_path(version_group_id)
    with path.open("w", encoding="utf-8", newline="") as handle:
        handle.write(stdout)
    rows = max(0, len(stdout.splitlines()) - 1)
    print(f"exported {rows} observed-move rows to {path}")


def _text_literal(value):
    if value is None or value == "":
        return "NULL"
    return "'" + str(value).replace("'", "''") + "'"


def load(version_group_id, apply_changes):
    path = csv_path(version_group_id)
    if not path.exists():
        print(f"no observed-moves CSV at {path}", file=sys.stderr)
        raise SystemExit(1)
    with path.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        print(f"observed-moves CSV at {path} has no rows", file=sys.stderr)
        raise SystemExit(1)

    value_rows = []
    for line_no, r in enumerate(rows, start=2):
        try:
            vg = int(r["version_group_id"])
            slot = int(r["slot"])
            key = (r["trainer_key"] or "").strip()
            species = (r["species_name"] or "").strip()
            move = (r["move_name"] or "").strip()
            if not key or not species or not move:
                raise ValueError("trainer_key, species_name and move_name are required")
            if vg != int(version_group_id):
                raise ValueError(f"row targets version group {vg}")
        except (TypeError, ValueError, KeyError) as exc:
            print(f"CSV line {line_no}: bad row ({exc}): {dict(r)}", file=sys.stderr)
            raise SystemExit(1)
        value_rows.append(
            "({vg}, {key}, {slot}, {species}, {move}, {noted}, {note})".format(
                vg=vg, key=_text_literal(key), slot=slot,
                species=_text_literal(species), move=_text_literal(move),
                noted=_text_literal((r.get("noted_at") or "").strip()) if (r.get("noted_at") or "").strip() else "current_timestamp",
                note=_text_literal(r.get("note")),
            )
        )
    values = ",\n".join(value_rows)
    vg = int(version_group_id)
    finish = "COMMIT;" if apply_changes else "ROLLBACK;"
    sql = f"""
BEGIN;

CREATE TEMP TABLE observed_moves_stage (
  version_group_id integer, trainer_key text, slot integer,
  species_name text, move_name text, noted_at timestamp with time zone, note text
) ON COMMIT DROP;

INSERT INTO observed_moves_stage VALUES
{values};

DO $load$
BEGIN
  -- Every move must exist in the move vocabulary. The comparison mirrors
  -- the read path's _normalize_move_constant: strip a MOVE_ prefix, map
  -- underscores and spaces to hyphens, lowercase.
  IF EXISTS (
    SELECT 1 FROM observed_moves_stage s
    WHERE NOT EXISTS (
      SELECT 1 FROM moves m
      WHERE lower(replace(m.move_name, ' ', '-')) =
            lower(replace(replace(regexp_replace(s.move_name, '^MOVE_', '', 'i'), '_', '-'), ' ', '-')))
  ) THEN
    RAISE EXCEPTION 'observed-moves CSV references unknown moves';
  END IF;
END
$load$;

INSERT INTO curated_trainer_moves
  (version_group_id, trainer_key, slot, species_name, move_name, noted_at, note)
SELECT version_group_id, trainer_key, slot, species_name, move_name,
       coalesce(noted_at, current_timestamp), note
FROM observed_moves_stage
ON CONFLICT (version_group_id, trainer_key, slot, move_name) DO UPDATE SET
  species_name = excluded.species_name,
  noted_at = excluded.noted_at,
  note = excluded.note;

-- The CSV is the source of truth for its version group: rows it no longer
-- carries were deleted at the origin and must be deleted here too.
DELETE FROM curated_trainer_moves c
WHERE c.version_group_id = {vg}
  AND NOT EXISTS (
    SELECT 1 FROM observed_moves_stage s
    WHERE s.trainer_key = c.trainer_key
      AND s.slot = c.slot
      AND s.move_name = c.move_name);

SELECT 'observed_move_rows' AS metric,
       (SELECT count(*) FROM curated_trainer_moves WHERE version_group_id = {vg}) AS value;
-- Rows whose trainer or slot no longer matches the extraction are inert
-- (the read path skips them); nonzero deserves a look, not a failure.
SELECT 'rows_without_matching_slot' AS metric,
       (SELECT count(*) FROM curated_trainer_moves c
        WHERE c.version_group_id = {vg}
          AND NOT EXISTS (
            SELECT 1 FROM trainer_pool tp
            JOIN trainer_pokemon tpk ON tpk.trainer_id = tp.trainer_id AND tpk.slot = c.slot
            WHERE tp.version_group_id = c.version_group_id
              AND tp.encounter_name = c.trainer_key
              AND upper(tpk.species_name) = upper(c.species_name))) AS value;

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
