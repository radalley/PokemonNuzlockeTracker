-- Trim Nuvema Town and Accumula Town from the Blaze Black script.
--
-- In the hack's script (version group 1001) both towns are empty rows:
-- no wild pools, no placed trainers, no boss linkage -- pure scroll
-- noise on the run page. They stay in the vanilla BW script (vg 11),
-- where Nuvema hosts the post-game weekend rematches.
--
-- The DELETE sits OUTSIDE the run-once guard on purpose: it is
-- idempotent, and the production launch runbook re-runs this file AFTER
-- clone_version_group (the clone copies the vg-11 script wholesale,
-- which would resurrect the two rows).

BEGIN;

SELECT pg_advisory_xact_lock(hashtext('lockley:bb_trim_empty_towns_v1'));

CREATE TABLE IF NOT EXISTS schema_migrations (
    migration_name text PRIMARY KEY,
    applied_at timestamp with time zone NOT NULL DEFAULT current_timestamp
);

DELETE FROM event_locations
WHERE version_group_id = 1001
  AND canonical_location_id IN (496, 497)
  AND event_type = 'Location';

DO $migration$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM schema_migrations WHERE migration_name = 'bb_trim_empty_towns_v1'
    ) THEN
        INSERT INTO schema_migrations (migration_name) VALUES ('bb_trim_empty_towns_v1');
        RAISE NOTICE 'bb_trim_empty_towns_v1 applied';
    ELSE
        RAISE NOTICE 'bb_trim_empty_towns_v1 already applied; skipping';
    END IF;
END
$migration$;

COMMIT;
