-- WP5: placement curation.
--
-- curated_trainer_placements is the durable record of human placement
-- decisions, keyed by the stable ETL identity (encounter_name, unique within
-- a version group) rather than trainer_id, so re-extracting a generation
-- never loses curation: loaders re-apply this table after load.
--
-- trainer_placement_suggestions holds machine-derived candidates (map
-- references, Serebii cross-checks) that the admin surface offers for
-- one-click acceptance. Rebuilt by etl/pipelines/build_placement_suggestions;
-- rows are advisory and never applied without a human decision.

BEGIN;

SELECT pg_advisory_xact_lock(hashtext('lockley:placement_curation_v1'));

CREATE TABLE IF NOT EXISTS schema_migrations (
    migration_name text PRIMARY KEY,
    applied_at timestamp with time zone NOT NULL DEFAULT current_timestamp
);

CREATE TABLE IF NOT EXISTS curated_trainer_placements (
    version_group_id integer NOT NULL,
    trainer_key text NOT NULL,
    canonical_location_id integer,
    area_id integer,
    decided_at timestamp with time zone NOT NULL DEFAULT current_timestamp,
    PRIMARY KEY (version_group_id, trainer_key)
);

CREATE TABLE IF NOT EXISTS trainer_placement_suggestions (
    version_group_id integer NOT NULL,
    trainer_key text NOT NULL,
    canonical_location_id integer NOT NULL,
    area_name text,
    source text NOT NULL,
    detail text,
    PRIMARY KEY (version_group_id, trainer_key, canonical_location_id, source)
);

CREATE INDEX IF NOT EXISTS idx_placement_suggestions_key
    ON trainer_placement_suggestions (version_group_id, trainer_key);

DO $migration$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM schema_migrations WHERE migration_name = 'placement_curation_v1'
    ) THEN
        INSERT INTO schema_migrations (migration_name) VALUES ('placement_curation_v1');
    END IF;
END
$migration$;

COMMIT;
