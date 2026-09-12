"""Derive location areas from the map references the ETL already captured.

Every trainer row carries a `details` blob naming the source map it was
extracted from -- `redblue_map=CeladonGym`, `crystal_map=VioletGym`,
`matched_map=canalave_city_gym`. Where that map is something other than the
canonical location itself, it names a real sub-place: a gym, a department
store, a cave floor.

This pipeline turns those map names into `location_areas` rows and points
`trainer_pool.area_id` at them, so a city's trainer panel groups by where the
trainers actually stand instead of listing them in one flat list.

    python -m etl.pipelines.derive_location_areas            # dry run
    python -m etl.pipelines.derive_location_areas --apply
    python -m etl.pipelines.derive_location_areas --version-group-id 1

Only trainers that are already placed are touched; placing the unplaced
backlog is the separate curation problem (WP5). Re-running is safe: areas are
matched on identity and only empty `area_id`s are filled unless --reassign is
passed.
"""
import argparse
import re
import sys

from .. import db, normalize
from ..loader import Guard, GuardedLoad, Metric, StageTable

# Matches any generation's map key: redblue_map=, crystal_map=, matched_map=,
# goldsilver_map=, yellow_map=. The value runs to the next field separator.
MAP_KEY_PATTERN = re.compile(r"[a-z0-9_]+_map(?:_name)?=([^;]+)")

STAGE_COLUMNS = [
    ("trainer_id", "integer"),
    ("canonical_location_id", "integer"),
    ("version_group_id", "integer"),
    ("area_name", "text"),
    ("area_kind", "text"),
    ("source_key", "text"),
]


def extract_map_name(details):
    match = MAP_KEY_PATTERN.search(details or "")
    return match.group(1).strip() if match else None


def collect_candidates(version_group_id=None):
    """Placed trainers whose source map names a sub-place of their location."""
    vg_filter = f"and tp.version_group_id = {int(version_group_id)}" if version_group_id else ""
    rows = db.query_rows(
        "select tp.trainer_id, tp.canonical_location_id, tp.version_group_id, "
        "coalesce(cl.canonical_location_name, ''), coalesce(tp.details, '') "
        "from trainer_pool tp "
        "join canon_locations cl on cl.canonical_location_id = tp.canonical_location_id "
        f"where tp.canonical_location_id is not null {vg_filter} "
        "order by tp.trainer_id"
    )

    candidates = []
    for trainer_id, location_id, vg, location_name, details in rows:
        map_name = extract_map_name(details)
        if not map_name:
            continue
        # A route trainer's map is the route itself: that is not an area.
        if normalize.location_match_key(map_name) == normalize.location_match_key(location_name):
            continue
        area_name = normalize.area_display_name(map_name)
        if not area_name:
            continue
        candidates.append({
            "trainer_id": trainer_id,
            "canonical_location_id": location_id,
            "version_group_id": vg,
            "area_name": area_name,
            "area_kind": normalize.area_kind(area_name),
            "source_key": map_name,
        })
    return candidates


def build_load(candidates, reassign=False):
    assign_filter = "" if reassign else "AND tp.area_id IS NULL"
    identity = (
        "la.canonical_location_id = s.canonical_location_id "
        "AND coalesce(la.version_group_id, -1) = coalesce(s.version_group_id, -1) "
        "AND la.area_name = s.area_name"
    )

    return GuardedLoad(
        title="Derive location areas from ETL map references",
        stages=[StageTable("location_area_stage", STAGE_COLUMNS, candidates)],
        guards=[
            Guard(
                f"(SELECT count(*) FROM location_area_stage) <> {len(candidates)}",
                "Unexpected location-area stage row count",
            ),
            Guard(
                "EXISTS (SELECT 1 FROM location_area_stage s "
                "LEFT JOIN trainer_pool tp ON tp.trainer_id = s.trainer_id "
                "WHERE tp.trainer_id IS NULL)",
                "Stage references a trainer that does not exist",
            ),
            Guard(
                "EXISTS (SELECT 1 FROM location_area_stage WHERE coalesce(btrim(area_name), '') = '')",
                "Stage contains a blank area name",
            ),
        ],
        statements=[
            f"""
INSERT INTO location_areas (canonical_location_id, version_group_id, area_name, area_kind, source_key)
SELECT DISTINCT s.canonical_location_id, s.version_group_id, s.area_name, s.area_kind, s.source_key
FROM location_area_stage s
WHERE NOT EXISTS (SELECT 1 FROM location_areas la WHERE {identity})
""",
            f"""
UPDATE trainer_pool tp
SET area_id = la.area_id
FROM location_area_stage s
JOIN location_areas la ON {identity}
WHERE tp.trainer_id = s.trainer_id
  {assign_filter}
""",
            # Gyms first, then alphabetically, within each location.
            """
UPDATE location_areas la
SET sort_order = ranked.rn
FROM (
  SELECT area_id,
         row_number() OVER (
           PARTITION BY canonical_location_id, coalesce(version_group_id, -1)
           ORDER BY CASE WHEN area_kind = 'gym' THEN 0 ELSE 1 END, area_name
         ) AS rn
  FROM location_areas
) ranked
WHERE la.area_id = ranked.area_id
  AND la.sort_order IS DISTINCT FROM ranked.rn
""",
        ],
        metrics=[
            Metric("area_rows", "SELECT count(*) FROM location_areas"),
            Metric("gym_areas", "SELECT count(*) FROM location_areas WHERE area_kind = 'gym'"),
            Metric("trainers_with_area", "SELECT count(*) FROM trainer_pool WHERE area_id IS NOT NULL"),
            Metric("placed_trainers", "SELECT count(*) FROM trainer_pool WHERE canonical_location_id IS NOT NULL"),
        ],
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--apply", action="store_true", help="Commit; default is a dry run.")
    parser.add_argument("--version-group-id", type=int, default=None, help="Restrict to one version group.")
    parser.add_argument(
        "--reassign", action="store_true",
        help="Overwrite existing area assignments instead of only filling empty ones.",
    )
    args = parser.parse_args()

    candidates = collect_candidates(args.version_group_id)
    if not candidates:
        print("No area candidates found; nothing to do.")
        return

    areas = {(c["canonical_location_id"], c["version_group_id"], c["area_name"]) for c in candidates}
    print(f"{len(candidates)} trainers map to {len(areas)} distinct areas.")

    try:
        result = build_load(candidates, reassign=args.reassign).run(apply=args.apply)
    except db.PsqlError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1)
    result.report()


if __name__ == "__main__":
    main()
