"""Load Gen 5 event bosses (gyms, rivals, N, Elite Four) from a build preview.

Replaces load_blackwhite_build6_event_bosses.py and its Black 2/White 2 shim:

    python -m etl.pipelines.gen5_event_bosses blackwhite            # dry run
    python -m etl.pipelines.gen5_event_bosses blackwhite --apply

Must run after the matching trainers pipeline: every staged boss row is
checked against a trainer_pool row from the same version group and build.
"""
from .. import manifests, preview, schemas
from ..loader import Guard, GuardedLoad, Metric, StageTable, loader_cli


def validate(manifest, rows):
    preview.expect_row_count(rows, manifest.expected("event_bosses"), "event boss")
    preview.expect_column_value(rows, "version_group_id", manifest.version_group_id, "event boss")
    allowed = manifest.get("allowed_boss_game_ids") or [""]
    preview.expect_column_in(rows, "game_id", allowed, "event boss")
    expected_game_rows = manifest.expected("game_specific_bosses")
    if expected_game_rows is not None:
        actual = sum(1 for r in rows if r.get("game_id"))
        if actual != expected_game_rows:
            raise preview.PreviewError(
                f"Expected exactly {expected_game_rows} version-specific boss rows, found {actual}"
            )


def build_load(args):
    manifest = manifests.load(args.manifest)
    preview_dir = args.preview_dir or manifest.preview_dir()
    rows = preview.read_csv(f"{preview_dir}/event_bosses_preview.csv")
    validate(manifest, rows)

    vg = manifest.version_group_id
    build = manifest.load_build
    expected_game_rows = manifest.expected("game_specific_bosses")

    guards = [
        Guard(
            f"(SELECT count(*) FROM event_boss_stage) <> {len(rows)}",
            "Unexpected event-boss stage row count",
        ),
        Guard(
            f"EXISTS (SELECT 1 FROM event_boss_stage WHERE version_group_id <> {vg})",
            "Stage contains the wrong version group",
        ),
        Guard(
            f"EXISTS (SELECT 1 FROM event_bosses WHERE version_group_id = {vg})",
            f"{manifest.label} event bosses already exist",
        ),
        # Bosses are bound to trainers by encounter_name, not by the
        # database-assigned trainer_id baked into the preview: those ids are
        # only valid in the database the trainers happened to be inserted
        # into, which made the old loader unusable on a fresh database.
        Guard(
            "EXISTS ("
            "SELECT 1 FROM event_boss_stage s "
            "WHERE (SELECT count(*) FROM trainer_pool tp "
            f"       WHERE tp.encounter_name = s.encounter_name "
            f"         AND tp.version_group_id = {vg} AND tp.load_build = {build}) <> 1"
            ")",
            f"A staged boss does not resolve to exactly one {manifest.label} build {build} trainer",
        ),
    ]
    if expected_game_rows is not None:
        guards.append(
            Guard(
                f"(SELECT count(*) FROM event_boss_stage WHERE nullif(game_id, '') IS NOT NULL) <> {expected_game_rows}",
                "Unexpected version-specific boss row count",
            )
        )

    return GuardedLoad(
        title=f"{manifest.label} event bosses (build {build})",
        stages=[
            StageTable(
                "event_boss_stage",
                schemas.subset(schemas.EVENT_BOSS_COLUMNS, rows[0]),
                rows,
            )
        ],
        guards=guards,
        statements=[
            f"""
WITH resolved AS (
  SELECT s.*, tp.trainer_id AS resolved_trainer_id
  FROM event_boss_stage s
  JOIN trainer_pool tp
    ON tp.encounter_name = s.encounter_name
   AND tp.version_group_id = {vg}
   AND tp.load_build = {build}
),
numbered AS (
  SELECT r.*,
         row_number() OVER (
           ORDER BY sort_order::numeric, encounter_title, starter, encounter_name
         ) AS row_number,
         (SELECT coalesce(max(event_id), 0) FROM event_bosses) AS current_max
  FROM resolved r
)
INSERT INTO event_bosses (
  event_id, trainer_id, sort_order, encounter_title, starter, type_focus,
  version_group_id, event_type, game_id, badge_id
)
SELECT
  current_max + row_number, resolved_trainer_id, sort_order, encounter_title,
  nullif(starter, ''), nullif(type_focus, ''), version_group_id,
  nullif(event_type, ''), nullif(game_id, '')::integer, nullif(badge_id, '')::integer
FROM numbered
ORDER BY sort_order::numeric, encounter_title, starter, encounter_name
""",
            """
SELECT setval(
  pg_get_serial_sequence('event_bosses', 'event_id'),
  (SELECT max(event_id) FROM event_bosses),
  true
)
""",
        ],
        metrics=[
            Metric("event_boss_rows", f"SELECT count(*) FROM event_bosses WHERE version_group_id = {vg}"),
            Metric(
                "starter_rows",
                f"SELECT count(*) FROM event_bosses WHERE version_group_id = {vg} AND starter IS NOT NULL",
            ),
            Metric(
                "game_specific_rows",
                f"SELECT count(*) FROM event_bosses WHERE version_group_id = {vg} AND game_id IS NOT NULL",
            ),
            Metric(
                "badge_rows",
                f"SELECT count(*) FROM event_bosses WHERE version_group_id = {vg} AND badge_id IS NOT NULL",
            ),
            Metric(
                "located_boss_trainers",
                "SELECT count(*) FROM event_bosses eb JOIN trainer_pool tp ON tp.trainer_id = eb.trainer_id "
                f"WHERE eb.version_group_id = {vg} AND tp.canonical_location_id IS NOT NULL",
            ),
        ],
    )


def main():
    loader_cli(
        "Load Gen 5 event bosses from a build preview.",
        build_load,
        extra_args=[(("manifest",), {"help": "Manifest key, e.g. blackwhite or black2white2"})],
    )


if __name__ == "__main__":
    main()
