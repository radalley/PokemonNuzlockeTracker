-- Extend curated placements with a status and durable trainer flags.
--
-- Full-fleet curation needs to record more than a location:
--   * status 'excluded' resolves a trainer that must never be placed
--     (unused ROM placeholder data -- nameless PATRAT L10 rows) so
--     placement metrics stop counting it as a gap; its
--     canonical_location_id stays NULL.
--   * is_rematch / is_event / game_id curate the flags the extractor
--     could not: progressive rematch tiers (Big Stadium & Small Court),
--     one-off event battles (Cynthia, Royal Unova passengers), and
--     version exclusives (White Forest / Black City residents).
--   * note preserves the curation rationale for audits.
-- The loaders' re-applied curation SQL (etl/curation.py) copies the new
-- fields onto trainer_pool, so re-extraction keeps them.

BEGIN;

SELECT pg_advisory_xact_lock(hashtext('lockley:placement_curation_status_v1'));

CREATE TABLE IF NOT EXISTS schema_migrations (
    migration_name text PRIMARY KEY,
    applied_at timestamp with time zone NOT NULL DEFAULT current_timestamp
);

ALTER TABLE curated_trainer_placements
    ADD COLUMN IF NOT EXISTS status text NOT NULL DEFAULT 'placed';
ALTER TABLE curated_trainer_placements
    ADD COLUMN IF NOT EXISTS is_rematch boolean;
ALTER TABLE curated_trainer_placements
    ADD COLUMN IF NOT EXISTS is_event boolean;
ALTER TABLE curated_trainer_placements
    ADD COLUMN IF NOT EXISTS game_id integer;
ALTER TABLE curated_trainer_placements
    ADD COLUMN IF NOT EXISTS note text;

DO $migration$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM schema_migrations WHERE migration_name = 'placement_curation_status_v1'
    ) THEN
        INSERT INTO schema_migrations (migration_name) VALUES ('placement_curation_status_v1');
        RAISE NOTICE 'placement_curation_status_v1 applied';
    ELSE
        RAISE NOTICE 'placement_curation_status_v1 already applied; skipping';
    END IF;
END
$migration$;

COMMIT;
