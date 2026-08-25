"""Inherit base-game encounter pools for locations a hack's docs omit.

A ROM hack's documentation only lists what changed; per its own preamble,
anything unlisted stays vanilla. After load_encounters, any canonical
location that has base-game pool rows but no hack rows (the Starter pool,
for one) inherits the base game's rows verbatim. The base game comes from
games.base_game_id, so this works for any manifest's games.

    python -m etl.pipelines.fill_encounter_gaps blazeblack           # dry run
    python -m etl.pipelines.fill_encounter_gaps blazeblack --apply
"""
import argparse
import sys

from .. import db, manifests


def fill_sql(game_ids):
    game_id_list = ", ".join(str(g) for g in game_ids)
    return f"""
CREATE TEMP TABLE encounter_gap_fill ON COMMIT DROP AS
SELECT
  g.game_id::text AS game_id, ep.location_id, ep.canonical_location_id,
  ep.species_id, ep.min_level, ep.max_level, ep.method, ep.enounter_rate
FROM games g
JOIN encounter_pool ep
  ON nullif(ep.game_id::text, '')::integer = g.base_game_id
WHERE g.game_id IN ({game_id_list})
  AND g.base_game_id IS NOT NULL
  AND ep.canonical_location_id IS NOT NULL
  AND NOT EXISTS (
    SELECT 1 FROM encounter_pool e2
    WHERE nullif(e2.game_id::text, '')::integer = g.game_id
      AND e2.canonical_location_id = ep.canonical_location_id);

SELECT cl.canonical_location_name AS inherited_location,
       f.game_id, count(*) AS rows
FROM encounter_gap_fill f
JOIN canon_locations cl USING (canonical_location_id)
GROUP BY 1, 2 ORDER BY 1, 2;

INSERT INTO encounter_pool (
  game_id, location_id, canonical_location_id, species_id,
  min_level, max_level, method, enounter_rate
)
SELECT game_id, location_id, canonical_location_id, species_id,
       min_level, max_level, method, enounter_rate
FROM encounter_gap_fill
ORDER BY game_id, canonical_location_id, species_id;

SELECT 'inherited_rows' AS metric, count(*) AS value FROM encounter_gap_fill
"""


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("manifest", help="Manifest key, e.g. blazeblack")
    parser.add_argument("--apply", action="store_true", help="Commit; default is a dry run.")
    args = parser.parse_args()

    manifest = manifests.load(args.manifest)
    game_ids = sorted(manifest.game_ids.values())
    finish = "COMMIT;" if args.apply else "ROLLBACK;"
    sql = "BEGIN;\n" + fill_sql(game_ids) + ";\n" + f"{finish}\n"
    try:
        stdout, stderr = db.run_sql(sql)
    except db.PsqlError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1)
    print(stdout.strip())
    if stderr.strip():
        print(stderr.strip())
    print("Committed." if args.apply else "Dry run complete. Transaction rolled back.")


if __name__ == "__main__":
    main()
