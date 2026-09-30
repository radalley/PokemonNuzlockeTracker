"""Load a data set's wild encounter pool from its preview CSV.

    python -m etl.pipelines.load_encounters blazeblack           # dry run
    python -m etl.pipelines.load_encounters blazeblack --apply
    python -m etl.pipelines.load_encounters blazeblack --replace --apply

encounter_pool is keyed by game_id, so a manifest's games must not already
have pool rows unless --replace is given, which deletes those games' rows
inside the same transaction first (run fill_encounter_gaps again after a
replace: it removes the inherited rows too). Species references are checked
against the species table before anything is written, and every row must
carry a method from encounter_methods.py and a known slot kind.
"""
import encounter_methods

from .. import manifests, preview, schemas
from ..loader import Guard, GuardedLoad, Metric, StageTable, loader_cli


def sql_list(values):
    return ", ".join("'" + str(v).replace("'", "''") + "'" for v in values)


def build_load(args):
    manifest = manifests.load(args.manifest)
    preview_dir = args.preview_dir or manifest.preview_dir()
    rows = preview.read_csv(f"{preview_dir}/encounter_pool_preview.csv")
    preview.expect_row_count(rows, manifest.expected("encounters"), "encounter")
    game_ids = sorted(manifest.game_ids.values())
    preview.expect_column_in(rows, "game_id", [str(g) for g in game_ids], "encounter")
    game_id_list = ", ".join(str(g) for g in game_ids)
    replace = bool(getattr(args, "replace", False))
    # Insert in preview order: encounter_id then follows the doc, which is
    # the tiebreak the read path uses between equal-rate slots.
    for position, row in enumerate(rows):
        row["stage_order"] = position
    columns = schemas.subset(schemas.ENCOUNTER_POOL_COLUMNS, rows[0])
    staged = set(schemas.names(columns))

    def col(name, cast):
        """A staged column or its NULL when the preview predates it."""
        return cast(name) if name in staged else "NULL"

    guards = [
        Guard(
            f"(SELECT count(*) FROM encounter_pool_stage) <> {len(rows)}",
            "Unexpected encounter stage row count",
        ),
        Guard(
            "EXISTS (SELECT 1 FROM encounter_pool_stage s "
            "LEFT JOIN species sp ON sp.species_id = s.species_id "
            "WHERE sp.species_id IS NULL)",
            "Stage references an unknown species",
        ),
        Guard(
            "EXISTS (SELECT 1 FROM encounter_pool_stage s "
            "LEFT JOIN canon_locations cl ON cl.canonical_location_id = s.canonical_location_id "
            "WHERE cl.canonical_location_id IS NULL)",
            "Stage references an unknown canonical location",
        ),
        Guard(
            "EXISTS (SELECT 1 FROM encounter_pool_stage WHERE nullif(method, '') IS NULL "
            f"OR method NOT IN ({sql_list(encounter_methods.METHOD_KEYS)}))",
            "Stage contains an unknown encounter method",
        ),
    ]
    if "slot_kind" in staged:
        guards.append(Guard(
            "EXISTS (SELECT 1 FROM encounter_pool_stage WHERE nullif(slot_kind, '') IS NOT NULL "
            f"AND slot_kind NOT IN ({sql_list(encounter_methods.SLOT_KINDS)}))",
            "Stage contains an unknown slot kind",
        ))
    statements = []
    if replace:
        statements.append(
            "DELETE FROM encounter_pool "
            f"WHERE nullif(game_id::text, '')::integer IN ({game_id_list})"
        )
    else:
        guards.insert(1, Guard(
            "EXISTS (SELECT 1 FROM encounter_pool "
            f"WHERE nullif(game_id::text, '')::integer IN ({game_id_list}))",
            f"{manifest.label} encounter pool is already loaded (use --replace)",
        ))

    statements.append(f"""
INSERT INTO encounter_pool (
  game_id, location_id, canonical_location_id, species_id,
  min_level, max_level, method, enounter_rate,
  area, area_sort, condition, slot_kind, tag, note
)
SELECT
  game_id, nullif(location_id, '')::integer, canonical_location_id, species_id,
  nullif(min_level, '')::integer, nullif(max_level, '')::integer,
  nullif(method, ''), nullif(enounter_rate, '')::integer,
  {col('area', lambda c: f"nullif({c}, '')")},
  {col('area_sort', lambda c: f"nullif({c}, '')::integer")},
  {col('condition', lambda c: f"nullif({c}, '')")},
  {col('slot_kind', lambda c: f"coalesce(nullif({c}, ''), 'slot')") if 'slot_kind' in staged else "'slot'"},
  {col('tag', lambda c: f"nullif({c}, '')")},
  {col('note', lambda c: f"nullif({c}, '')")}
FROM encounter_pool_stage
ORDER BY stage_order
""")

    return GuardedLoad(
        title=f"{manifest.label} encounter pool",
        stages=[StageTable("encounter_pool_stage", columns, rows)],
        guards=guards,
        statements=statements,
        metrics=[
            Metric(
                "encounter_rows",
                f"SELECT count(*) FROM encounter_pool WHERE nullif(game_id::text, '')::integer IN ({game_id_list})",
            ),
            Metric(
                "locations_covered",
                "SELECT count(distinct canonical_location_id) FROM encounter_pool "
                f"WHERE nullif(game_id::text, '')::integer IN ({game_id_list})",
            ),
            Metric(
                "distinct_species",
                "SELECT count(distinct species_id) FROM encounter_pool "
                f"WHERE nullif(game_id::text, '')::integer IN ({game_id_list})",
            ),
            # Slot tables sum to 100 (99 where the doc rounds); anything
            # else is a table the parser merged or mis-attributed.
            Metric(
                "slot_tables_off_100",
                "SELECT count(*) FROM (SELECT sum(enounter_rate) AS total FROM encounter_pool "
                f"WHERE nullif(game_id::text, '')::integer IN ({game_id_list}) AND slot_kind = 'slot' "
                "GROUP BY game_id, canonical_location_id, coalesce(area, ''), coalesce(condition, ''), method) t "
                "WHERE total NOT BETWEEN 99 AND 100",
            ),
        ],
    )


def main():
    loader_cli(
        "Load a data set's wild encounter pool from its preview CSV.",
        build_load,
        extra_args=[
            (("manifest",), {"help": "Manifest key, e.g. blazeblack"}),
            (("--replace",), {"action": "store_true",
                              "help": "Delete the manifest's games' pool rows first (same transaction)."}),
        ],
    )


if __name__ == "__main__":
    main()
