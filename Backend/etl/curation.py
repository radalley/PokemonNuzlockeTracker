"""Re-application of curated placement decisions.

Human placement decisions live in `curated_trainer_placements`, keyed by
(version_group_id, encounter_name). Any pipeline that (re)creates trainer
rows must re-apply them afterwards, so extraction stays reproducible while
curation accumulates. Loaders include `apply_curated_placements_sql` in their
transaction; `etl.pipelines.apply_curated_placements` runs it standalone.
"""


def apply_curated_placements_sql(version_group_id, load_build=None):
    """SQL that copies curated decisions onto trainer_pool rows.

    A curated location always wins (that is the point of curation); a curated
    area wins when present, otherwise any derived area assignment is kept.
    """
    build_filter = f"AND tp.load_build = {int(load_build)}" if load_build is not None else ""
    return f"""
UPDATE trainer_pool tp
SET canonical_location_id = coalesce(c.canonical_location_id, tp.canonical_location_id),
    area_id = coalesce(c.area_id, tp.area_id)
FROM curated_trainer_placements c
WHERE tp.version_group_id = {int(version_group_id)}
  {build_filter}
  AND c.version_group_id = tp.version_group_id
  AND c.trainer_key = tp.encounter_name
"""


def curated_metric_sql(version_group_id):
    return (
        "SELECT count(*) FROM curated_trainer_placements "
        f"WHERE version_group_id = {int(version_group_id)}"
    )
