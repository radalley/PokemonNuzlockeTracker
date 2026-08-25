"""Load Gen 5 trainers and their parties from a build preview.

Replaces load_blackwhite_build6_trainers.py and its Black 2/White 2 shim with
one manifest-driven loader:

    python -m etl.pipelines.gen5_trainers blackwhite            # dry run
    python -m etl.pipelines.gen5_trainers blackwhite --apply
    python -m etl.pipelines.gen5_trainers black2white2 --apply

Unlike the originals, trainer_pokemon rows are linked to trainer_pool by
trainer_id at load time (WP1) and carry their slot, so party order is
explicit rather than implied by insertion order.
"""
from .. import curation, manifests, preview, schemas
from ..loader import Guard, GuardedLoad, Metric, StageTable, loader_cli


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

    return GuardedLoad(
        title=f"{manifest.label} trainers (build {build})",
        stages=[
            StageTable(
                "trainer_pool_stage",
                schemas.subset(schemas.TRAINER_POOL_COLUMNS, trainers[0]),
                trainers,
            ),
            StageTable(
                "trainer_pokemon_stage",
                schemas.subset(schemas.TRAINER_POKEMON_COLUMNS, pokemon[0]),
                pokemon,
            ),
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
            Guard(
                f"EXISTS (SELECT 1 FROM trainer_pool WHERE {scope}) "
                f"OR EXISTS (SELECT 1 FROM trainer_pokemon WHERE {scope})",
                f"{manifest.label} build {build} trainer data is already loaded",
            ),
        ],
        statements=[
            f"""
INSERT INTO trainer_pool (
  encounter_name, trainer_name, trainer_class, canonical_location_id,
  is_rematch, is_event, trainer_items, trainer_pic, trainer_double,
  details, version_group_id, load_build, game_id
)
SELECT
  nullif(encounter_name, ''), nullif(trainer_name, ''), nullif(trainer_class, ''),
  nullif(canonical_location_id, '')::integer,
  nullif(is_rematch, ''), nullif(is_event, ''), nullif(trainer_items, ''),
  nullif(trainer_pic, ''), nullif(trainer_double, ''), nullif(details, ''),
  version_group_id, load_build, nullif(game_id, '')::integer
FROM trainer_pool_stage
ORDER BY encounter_name
""",
            f"""
INSERT INTO trainer_pokemon (
  encounter_name, species_name, lvl, moves, held_item, iv,
  version_group_id, load_build, slot
)
SELECT
  nullif(encounter_name, ''), nullif(species_name, ''), lvl,
  nullif(moves, ''), nullif(held_item, ''), iv,
  version_group_id, load_build, slot
FROM trainer_pokemon_stage
ORDER BY encounter_name, slot
""",
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
        "Load Gen 5 trainers and parties from a build preview.",
        build_load,
        extra_args=[(("manifest",), {"help": "Manifest key, e.g. blackwhite or black2white2"})],
    )


if __name__ == "__main__":
    main()
