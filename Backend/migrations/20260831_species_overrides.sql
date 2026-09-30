-- Species override layer for ROM hacks.
--
-- Blaze Black rewrites species data: every species' Regular-mode abilities,
-- ~130 stat spreads, 18 typings, per-species level-up learnsets, and ~45
-- move rebalances. The species_* patch tables gain a nullable
-- version_group_id: a row carrying one is an exact override for that
-- version group (a hack's), preferred over the generation-based pick; rows
-- with NULL keep their existing generation semantics untouched.
--
-- movesets and moves already carry version_group_id; hack learnsets load as
-- materialized rows at the hack's version group (vanilla copy + doc deltas)
-- and the resolvers prefer an exact version-group match before falling back
-- to the base game's chronology.

BEGIN;

SELECT pg_advisory_xact_lock(hashtext('lockley:species_overrides_v1'));

CREATE TABLE IF NOT EXISTS schema_migrations (
    migration_name text PRIMARY KEY,
    applied_at timestamp with time zone NOT NULL DEFAULT current_timestamp
);

ALTER TABLE species_abilities ADD COLUMN IF NOT EXISTS version_group_id integer;
ALTER TABLE species_stats ADD COLUMN IF NOT EXISTS version_group_id integer;
ALTER TABLE species_types ADD COLUMN IF NOT EXISTS version_group_id integer;

CREATE INDEX IF NOT EXISTS idx_species_abilities_vg
    ON species_abilities (version_group_id) WHERE version_group_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_species_stats_vg
    ON species_stats (version_group_id) WHERE version_group_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_species_types_vg
    ON species_types (version_group_id) WHERE version_group_id IS NOT NULL;

DO $migration$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM schema_migrations WHERE migration_name = 'species_overrides_v1'
    ) THEN
        INSERT INTO schema_migrations (migration_name) VALUES ('species_overrides_v1');
    END IF;
END
$migration$;

COMMIT;
