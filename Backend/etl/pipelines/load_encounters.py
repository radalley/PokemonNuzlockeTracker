"""Load a data set's wild encounter pool from its preview CSV.

    python -m etl.pipelines.load_encounters blazeblack           # dry run
    python -m etl.pipelines.load_encounters blazeblack --apply

encounter_pool is keyed by game_id, so a manifest's games must not already
have pool rows; species references are checked against the species table
before anything is written.
"""
from .. import manifests, preview, schemas
from ..loader import Guard, GuardedLoad, Metric, StageTable, loader_cli


def build_load(args):
    manifest = manifests.load(args.manifest)
    preview_dir = args.preview_dir or manifest.preview_dir()
    rows = preview.read_csv(f"{preview_dir}/encounter_pool_preview.csv")
    preview.expect_row_count(rows, manifest.expected("encounters"), "encounter")
    game_ids = sorted(manifest.game_ids.values())
    preview.expect_column_in(rows, "game_id", [str(g) for g in game_ids], "encounter")
    game_id_list = ", ".join(str(g) for g in game_ids)

    return GuardedLoad(
        title=f"{manifest.label} encounter pool",
        stages=[
            StageTable(
                "encounter_pool_stage",
                schemas.subset(schemas.ENCOUNTER_POOL_COLUMNS, rows[0]),
                rows,
            )
        ],
        guards=[
            Guard(
                f"(SELECT count(*) FROM encounter_pool_stage) <> {len(rows)}",
                "Unexpected encounter stage row count",
            ),
            Guard(
                "EXISTS (SELECT 1 FROM encounter_pool "
                f"WHERE nullif(game_id::text, '')::integer IN ({game_id_list}))",
                f"{manifest.label} encounter pool is already loaded",
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
        ],
        statements=[
            """
INSERT INTO encounter_pool (
  game_id, location_id, canonical_location_id, species_id,
  min_level, max_level, method, enounter_rate
)
SELECT
  game_id, nullif(location_id, '')::integer, canonical_location_id, species_id,
  nullif(min_level, '')::integer, nullif(max_level, '')::integer,
  nullif(method, ''), enounter_rate
FROM encounter_pool_stage
ORDER BY game_id, canonical_location_id, species_id
""",
        ],
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
        ],
    )


def main():
    loader_cli(
        "Load a data set's wild encounter pool from its preview CSV.",
        build_load,
        extra_args=[(("manifest",), {"help": "Manifest key, e.g. blazeblack"})],
    )


if __name__ == "__main__":
    main()
