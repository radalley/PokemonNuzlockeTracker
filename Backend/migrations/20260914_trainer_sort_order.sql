-- Trainers within a location area get a curated display order.
--
-- A route's trainer panel should read in the order the player meets them,
-- which extraction cannot know. Admins fix the order in the app; the
-- decision lives on curated_trainer_placements (durable, CSV round-trip)
-- and is copied onto trainer_pool by the loaders' re-apply step, the same
-- way placements are. NULL means unordered: such rows sort after ordered
-- ones and then by trainer_id, exactly as before.

BEGIN;

SELECT pg_advisory_xact_lock(hashtext('lockley:trainer_sort_order_v1'));

CREATE TABLE IF NOT EXISTS schema_migrations (
    migration_name text PRIMARY KEY,
    applied_at timestamp with time zone NOT NULL DEFAULT current_timestamp
);

ALTER TABLE curated_trainer_placements ADD COLUMN IF NOT EXISTS sort_order integer;
ALTER TABLE trainer_pool ADD COLUMN IF NOT EXISTS sort_order integer;

DO $migration$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM schema_migrations WHERE migration_name = 'trainer_sort_order_v1'
    ) THEN
        INSERT INTO schema_migrations (migration_name) VALUES ('trainer_sort_order_v1');
        RAISE NOTICE 'trainer_sort_order_v1 applied';
    ELSE
        RAISE NOTICE 'trainer_sort_order_v1 already applied; skipping';
    END IF;
END
$migration$;

COMMIT;
