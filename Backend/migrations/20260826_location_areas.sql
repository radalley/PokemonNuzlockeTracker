-- WP4: location areas.
-- A canonical location is as fine-grained as the script gets, but trainers
-- live in sub-places within it: a city's gym, a department store, a cave
-- floor. Without somewhere to put them, gym and interior trainers either sit
-- in one undifferentiated list under the city or -- more often -- are never
-- placed at all.
--
-- location_areas sits below canon_locations. trainer_pool.area_id is
-- nullable: a trainer standing in the location itself (a route) has no area
-- and renders in the default group.
--
-- Structure only. Areas are derived from ETL map references by
-- etl/pipelines/derive_location_areas.py, which is re-runnable.

BEGIN;

SELECT pg_advisory_xact_lock(hashtext('lockley:location_areas_v1'));

CREATE TABLE IF NOT EXISTS schema_migrations (
    migration_name text PRIMARY KEY,
    applied_at timestamp with time zone NOT NULL DEFAULT current_timestamp
);

CREATE TABLE IF NOT EXISTS location_areas (
    area_id serial PRIMARY KEY,
    canonical_location_id integer NOT NULL,
    version_group_id integer,
    area_name text NOT NULL,
    area_kind text NOT NULL DEFAULT 'interior',
    sort_order integer,
    source_key text
);

-- An area belongs to one location within one version group: the same city's
-- gym can hold different trainers in different games.
CREATE UNIQUE INDEX IF NOT EXISTS idx_location_areas_identity
    ON location_areas (canonical_location_id, coalesce(version_group_id, -1), area_name);

CREATE INDEX IF NOT EXISTS idx_location_areas_location
    ON location_areas (canonical_location_id);

ALTER TABLE trainer_pool ADD COLUMN IF NOT EXISTS area_id integer;

CREATE INDEX IF NOT EXISTS idx_trainer_pool_area_id
    ON trainer_pool (area_id);

DO $migration$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM schema_migrations WHERE migration_name = 'location_areas_v1'
    ) THEN
        INSERT INTO schema_migrations (migration_name) VALUES ('location_areas_v1');
    END IF;
END
$migration$;

COMMIT;
