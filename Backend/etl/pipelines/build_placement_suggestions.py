"""Build machine-derived placement suggestions for unplaced trainers.

Rebuilds `trainer_placement_suggestions` from every evidence source the ETL
left behind, so the admin placement surface can offer one-click candidates
instead of a blank form:

  candidate_note  Gens 1-4: the extractor already matched a canonical
                  location but refused to auto-place ("canonical candidate
                  54 Pewter City is not in Gen I event_locations").
  map_reference   A source map name, either in the trainer's details blob
                  (Gens 1-4) or in the Gen 5 preview's
                  map_reference_details.csv, fuzzy-matched to canonical
                  locations.
  serebii         The B2W2 Serebii cross-check, keyed by encounter_name.

Suggestions are advisory: nothing is applied without an admin decision.
Rebuilding is destructive per version group and safe to re-run.

    python -m etl.pipelines.build_placement_suggestions            # dry run
    python -m etl.pipelines.build_placement_suggestions --apply
"""
import argparse
import re
import sys
from collections import defaultdict

from .. import config, db, normalize, preview
from ..loader import Guard, GuardedLoad, Metric, StageTable
from .derive_location_areas import extract_map_name

CANDIDATE_NOTE_PATTERN = re.compile(r"canonical candidate (\d+) ([^;]+?) is not in", re.IGNORECASE)
TRAINER_INDEX_PATTERN = re.compile(r"[a-z0-9]+_trainer_index=(\d+)")

# (version_group_id, preview dir name, serebii matches file or None)
GEN5_PREVIEWS = [
    (11, "blackwhite_build6_preview", None),
    (14, "black2white2_build6_preview", "serebii_location_matches.csv"),
]

LOCATION_SUFFIXES = ("city", "town", "island", "village")

STAGE_COLUMNS = [
    ("version_group_id", "integer"),
    ("trainer_key", "text"),
    ("canonical_location_id", "integer"),
    ("area_name", "text"),
    ("source", "text"),
    ("detail", "text"),
]


def location_stem(location_key):
    """`pewtercity` -> `pewter`; numbered locations keep their digits."""
    for suffix in LOCATION_SUFFIXES:
        if location_key.endswith(suffix) and len(location_key) > len(suffix):
            return location_key[: -len(suffix)]
    return location_key


def _boundary_ok(haystack, match_end):
    """A match that ends at a digit must not be followed by another digit,
    so `route1` never matches inside `route10`."""
    if match_end >= len(haystack):
        return True
    return not (haystack[match_end - 1].isdigit() and haystack[match_end].isdigit())


def suggest_locations(map_name, locations):
    """Match a source map name against [(location_id, location_name)].

    Returns [(location_id, location_name)], best matches only: full-key
    containment beats stem-prefix matching.
    """
    map_key = normalize.location_match_key(map_name)
    if not map_key:
        return []

    full, stem = [], []
    for location_id, location_name in locations:
        loc_key = normalize.location_match_key(location_name)
        if not loc_key:
            continue
        if loc_key == map_key:
            return [(location_id, location_name)]
        pos = map_key.find(loc_key)
        if pos >= 0 and _boundary_ok(map_key, pos + len(loc_key)):
            full.append((location_id, location_name))
            continue
        s = location_stem(loc_key)
        if s != loc_key and map_key.startswith(s) and _boundary_ok(map_key, len(s)):
            stem.append((location_id, location_name))
    return full or stem


def _fetch(sql):
    return db.query_rows(sql)


def script_locations_by_vg():
    """Locations that appear in each version group's script."""
    rows = _fetch(
        "select el.version_group_id, cl.canonical_location_id, cl.canonical_location_name "
        "from event_locations el join canon_locations cl "
        "on cl.canonical_location_id = el.canonical_location_id "
        "group by 1, 2, 3"
    )
    by_vg = defaultdict(list)
    for vg, location_id, name in rows:
        by_vg[int(vg)].append((int(location_id), name))
    return by_vg


def unplaced_trainers():
    rows = _fetch(
        "select version_group_id, encounter_name, coalesce(details, '') "
        "from trainer_pool where canonical_location_id is null order by trainer_id"
    )
    return [(int(vg), key, details) for vg, key, details in rows]


def collect_suggestions():
    locations = script_locations_by_vg()
    unplaced = unplaced_trainers()
    suggestions = {}

    def add(vg, key, location_id, source, detail, area_name=None):
        identity = (vg, key, location_id, source)
        if identity not in suggestions:
            suggestions[identity] = {
                "version_group_id": vg,
                "trainer_key": key,
                "canonical_location_id": location_id,
                "area_name": area_name,
                "source": source,
                "detail": detail,
            }

    # --- details-blob sources (Gens 1-4) --------------------------------
    for vg, key, details in unplaced:
        note = CANDIDATE_NOTE_PATTERN.search(details)
        if note:
            add(vg, key, int(note.group(1)), "candidate_note", note.group(0))
        map_name = extract_map_name(details)
        if map_name:
            area = normalize.area_display_name(map_name)
            for location_id, location_name in suggest_locations(map_name, locations.get(vg, [])):
                is_area = normalize.location_match_key(map_name) != normalize.location_match_key(location_name)
                add(vg, key, location_id, "map_reference", map_name,
                    area_name=area if is_area else None)

    # --- Gen 5 preview map references + Serebii -------------------------
    unplaced_by_vg = defaultdict(dict)
    for vg, key, details in unplaced:
        index = TRAINER_INDEX_PATTERN.search(details)
        unplaced_by_vg[vg][key] = index.group(1) if index else None

    for vg, preview_name, serebii_file in GEN5_PREVIEWS:
        preview_dir = config.preview_dir(preview_name)
        vg_locations = locations.get(vg, [])
        keys_by_index = {
            index: key for key, index in unplaced_by_vg.get(vg, {}).items() if index
        }

        refs_path = preview_dir / "map_reference_details.csv"
        if refs_path.exists():
            for row in preview.read_csv(refs_path):
                key = keys_by_index.get(row.get("trainer_index"))
                if not key:
                    continue
                map_name = (row.get("map_name") or "").strip()
                if not map_name:
                    continue
                for location_id, location_name in suggest_locations(map_name, vg_locations):
                    add(vg, key, location_id, "map_reference", map_name)

        if serebii_file:
            serebii_path = preview_dir / serebii_file
            if serebii_path.exists():
                unplaced_keys = set(unplaced_by_vg.get(vg, {}))
                for row in preview.read_csv(serebii_path):
                    key = (row.get("encounter_name") or "").strip()
                    if key not in unplaced_keys:
                        continue
                    location_name = (row.get("location_name") or "").strip()
                    for location_id, matched_name in suggest_locations(location_name, vg_locations):
                        add(vg, key, location_id, "serebii",
                            f"{row.get('trainer_label', '')} @ {location_name}".strip())

    return list(suggestions.values())


def build_load(rows):
    vgs = sorted({r["version_group_id"] for r in rows})
    vg_list = ", ".join(str(v) for v in vgs) or "NULL"
    return GuardedLoad(
        title="Rebuild trainer placement suggestions",
        stages=[StageTable("suggestion_stage", STAGE_COLUMNS, rows)],
        guards=[
            Guard(
                f"(SELECT count(*) FROM suggestion_stage) <> {len(rows)}",
                "Unexpected suggestion stage row count",
            ),
            Guard(
                "EXISTS (SELECT 1 FROM suggestion_stage s "
                "LEFT JOIN canon_locations cl ON cl.canonical_location_id = s.canonical_location_id "
                "WHERE cl.canonical_location_id IS NULL)",
                "A suggestion references an unknown canonical location",
            ),
        ],
        statements=[
            f"DELETE FROM trainer_placement_suggestions WHERE version_group_id IN ({vg_list})",
            """
INSERT INTO trainer_placement_suggestions
  (version_group_id, trainer_key, canonical_location_id, area_name, source, detail)
SELECT version_group_id, trainer_key, canonical_location_id,
       nullif(area_name, ''), source, nullif(detail, '')
FROM suggestion_stage
""",
        ],
        metrics=[
            Metric("suggestion_rows", "SELECT count(*) FROM trainer_placement_suggestions"),
            Metric(
                "unplaced_with_suggestions",
                "SELECT count(distinct (s.version_group_id, s.trainer_key)) "
                "FROM trainer_placement_suggestions s",
            ),
        ],
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--apply", action="store_true", help="Commit; default is a dry run.")
    args = parser.parse_args()

    rows = collect_suggestions()
    if not rows:
        print("No suggestions derived; nothing to do.")
        return
    by_source = defaultdict(int)
    for row in rows:
        by_source[row["source"]] += 1
    print(f"{len(rows)} suggestions: " + ", ".join(f"{s}={n}" for s, n in sorted(by_source.items())))

    try:
        result = build_load(rows).run(apply=args.apply)
    except db.PsqlError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1)
    result.report()


if __name__ == "__main__":
    main()
