"""Load a data set's trainers and parties from its preview CSVs.

Works for every version group whose preview follows the standard shape
(trainer_pool_preview.csv + trainer_pokemon_preview.csv), which is all of
them from build 4 on:

    python -m etl.pipelines.load_trainers redblue             # dry run
    python -m etl.pipelines.load_trainers redblue --apply
    python -m etl.pipelines.load_trainers blackwhite --apply

The stage adapts to the columns the preview actually carries (older previews
predate the ability/nature columns; Gen 1/2 previews carry extra debug
columns that are ignored). Party rows are linked to trainer_pool by
trainer_id inside the transaction and the load aborts if any fail to link.
Curated placement decisions are re-applied at the end, so re-extraction
never loses curation.
"""
from .. import curation, manifests, preview, schemas
from ..loader import Guard, GuardedLoad, Metric, StageTable, loader_cli

# How each staged column is written into the real table.
POOL_INSERT_EXPRS = {
    "encounter_name": "nullif(encounter_name, '')",
    "trainer_name": "nullif(trainer_name, '')",
    "trainer_class": "nullif(trainer_class, '')",
    "canonical_location_id": "nullif(canonical_location_id, '')::integer",
    "is_rematch": "nullif(is_rematch, '')",
    "is_event": "nullif(is_event, '')",
    "trainer_items": "nullif(trainer_items, '')",
    "trainer_pic": "nullif(trainer_pic, '')",
    "trainer_double": "nullif(trainer_double, '')",
    "details": "nullif(details, '')",
    "version_group_id": "version_group_id",
    "load_build": "load_build",
    "game_id": "nullif(game_id, '')::integer",
}

POKEMON_INSERT_EXPRS = {
    "encounter_name": "nullif(encounter_name, '')",
    "species_name": "nullif(species_name, '')",
    "lvl": "lvl",
    "moves": "nullif(moves, '')",
    "held_item": "nullif(held_item, '')",
    "iv": "iv",
    "version_group_id": "version_group_id",
    "load_build": "load_build",
    "slot": "slot",
    "ability": "nullif(ability, '')",
    "ability_clean": "nullif(ability_clean, '')",
    "nature": "nullif(nature, '')",
}


def _insert_sql(table, columns, exprs, source, order_by):
    names = schemas.names(columns)
    select_list = ",\n  ".join(exprs[name] for name in names)
    return (
        f"INSERT INTO {table} (\n  {', '.join(names)}\n)\n"
        f"SELECT\n  {select_list}\nFROM {source}\nORDER BY {order_by}"
    )


def validate(manifest, trainers, pokemon):
    preview.expect_row_count(trainers, manifest.expected("trainers"), "trainer")
    preview.expect_row_count(pokemon, manifest.expected("trainer_pokemon"), "trainer Pokemon")
    for label, rows in (("trainer", trainers), ("trainer Pokemon", pokemon)):
        preview.expect_column_value(rows, "version_group_id", manifest.version_group_id, label)
        preview.expect_column_value(rows, "load_build", manifest.load_build, label)
    preview.expect_unique(trainers, "encounter_name", "trainer")
    preview.expect_references(
        pokemon, "encounter_name",
        {r["encounter_name"] for r in trainers},
        "trainer Pokemon", "trainers",
    )
    allowed_game_ids = {""} | {str(v) for v in manifest.game_ids.values()}
    preview.expect_column_in(trainers, "game_id", allowed_game_ids, "trainer")


def build_load(args):
    manifest = manifests.load(args.manifest)
    preview_dir = args.preview_dir or manifest.preview_dir()
    trainers = preview.read_csv(f"{preview_dir}/trainer_pool_preview.csv")
    pokemon = preview.read_csv(f"{preview_dir}/trainer_pokemon_preview.csv")
    validate(manifest, trainers, pokemon)

    vg = manifest.version_group_id
    build = manifest.load_build
    scope = f"version_group_id = {vg} AND load_build = {build}"
    pool_columns = schemas.subset(schemas.TRAINER_POOL_COLUMNS, trainers[0])
    pokemon_columns = schemas.subset(schemas.TRAINER_POKEMON_COLUMNS, pokemon[0])

    return GuardedLoad(
        title=f"{manifest.label} trainers (build {build})",
        stages=[
            StageTable("trainer_pool_stage", pool_columns, trainers),
            StageTable("trainer_pokemon_stage", pokemon_columns, pokemon),
        ],
        guards=[
            Guard(
                f"(SELECT count(*) FROM trainer_pool_stage) <> {len(trainers)}",
                "Unexpected trainer stage row count",
            ),
            Guard(
                f"(SELECT count(*) FROM trainer_pokemon_stage) <> {len(pokemon)}",
                "Unexpected trainer Pokemon stage row count",
            ),
            Guard(
                f"EXISTS (SELECT 1 FROM trainer_pool_stage WHERE version_group_id <> {vg} OR load_build <> {build}) "
                f"OR EXISTS (SELECT 1 FROM trainer_pokemon_stage WHERE version_group_id <> {vg} OR load_build <> {build})",
                "Stage contains the wrong version group or load build",
            ),
            # Version-group-wide, not (vg, build)-scoped: no read path ever
            # distinguishes load builds, so loading build N+1 over existing
            # rows (or over a --full clone carrying the base's build) would
            # silently double every trainer. Remove the old build first.
            Guard(
                f"EXISTS (SELECT 1 FROM trainer_pool WHERE version_group_id = {vg}) "
                f"OR EXISTS (SELECT 1 FROM trainer_pokemon WHERE version_group_id = {vg})",
                f"Version group {vg} already contains trainer data ({manifest.label}); "
                "delete the existing build before loading a new one",
            ),
        ],
        statements=[
            _insert_sql("trainer_pool", pool_columns, POOL_INSERT_EXPRS,
                        "trainer_pool_stage", "encounter_name"),
            _insert_sql("trainer_pokemon", pokemon_columns, POKEMON_INSERT_EXPRS,
                        "trainer_pokemon_stage", "encounter_name, slot"),
            # encounter_name is unique within this build, so this links every
            # party row to exactly one trainer.
            f"""
UPDATE trainer_pokemon t
SET trainer_id = tp.trainer_id
FROM trainer_pool tp
WHERE t.version_group_id = {vg}
  AND t.load_build = {build}
  AND t.trainer_id IS NULL
  AND tp.version_group_id = {vg}
  AND tp.load_build = {build}
  AND tp.encounter_name = t.encounter_name
""",
            f"""
DO $link$
BEGIN
  IF EXISTS (
    SELECT 1 FROM trainer_pokemon
    WHERE version_group_id = {vg} AND load_build = {build} AND trainer_id IS NULL
  ) THEN
    RAISE EXCEPTION 'Loaded trainer Pokemon rows are missing trainer_id links';
  END IF;
END $link$
""",
            # Human placement decisions outlive re-extraction.
            curation.apply_curated_placements_sql(vg, load_build=build),
        ],
        metrics=[
            Metric("trainer_pool_rows", f"SELECT count(*) FROM trainer_pool WHERE {scope}"),
            Metric("trainer_pokemon_rows", f"SELECT count(*) FROM trainer_pokemon WHERE {scope}"),
            Metric(
                "located_rows",
                f"SELECT count(*) FROM trainer_pool WHERE {scope} AND canonical_location_id IS NOT NULL",
            ),
            Metric(
                "rows_with_game_id",
                f"SELECT count(*) FROM trainer_pool WHERE {scope} AND game_id IS NOT NULL",
            ),
            Metric(
                "linked_party_rows",
                f"SELECT count(*) FROM trainer_pokemon WHERE {scope} AND trainer_id IS NOT NULL",
            ),
            Metric("curated_placements", curation.curated_metric_sql(vg)),
        ],
    )


def main():
    loader_cli(
        "Load a data set's trainers and parties from its preview CSVs.",
        build_load,
        extra_args=[(("manifest",), {"help": "Manifest key, e.g. redblue, crystal, blackwhite"})],
    )


if __name__ == "__main__":
    main()
