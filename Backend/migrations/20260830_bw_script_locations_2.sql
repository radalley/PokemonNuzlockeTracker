-- WP8: five more Black/White script locations, surfaced by parsing the
-- Blaze Black docs against the vanilla script: Nuvema Town and Accumula Town
-- (trainer-only towns), Icirrus City (its gym had a badge but the city had
-- no script row), Moor of Icirrus, and Tubeline Bridge (both have wild
-- encounters in vanilla too -- they were simply missing).
--
-- Same pattern as 20260828: integer sort slots shared with the neighbor,
-- secondary_sort_order ordering within the slot.

BEGIN;

SELECT pg_advisory_xact_lock(hashtext('lockley:bw_script_locations_v2'));

CREATE TABLE IF NOT EXISTS schema_migrations (
    migration_name text PRIMARY KEY,
    applied_at timestamp with time zone NOT NULL DEFAULT current_timestamp
);

DO $migration$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM schema_migrations WHERE migration_name = 'bw_script_locations_v2'
    ) THEN
        IF EXISTS (
            SELECT 1 FROM canon_locations
            WHERE canonical_location_id IN (496, 497, 498, 499, 500)
        ) THEN
            RAISE EXCEPTION 'canonical_location_ids 496-500 are already taken';
        END IF;

        INSERT INTO canon_locations (canonical_location_id, canonical_location_name) VALUES
            (496, 'Nuvema Town'),
            (497, 'Accumula Town'),
            (498, 'Icirrus City'),
            (499, 'Moor of Icirrus'),
            (500, 'Tubeline Bridge');

        INSERT INTO event_locations
            (canonical_location_id, version_group_id, sort_order, secondary_sort_order, event_type)
        VALUES
            (496, 11, 0,  9, 'Location'),  -- after Starter (0,1), before the Nuvema rival fights (0.1)
            (497, 11, 1,  9, 'Location'),  -- after Route 1 (1,1)
            (498, 11, 26, 1, 'Location'),  -- before Icirrus City Gym (26.1)
            (499, 11, 26, 9, 'Location'),  -- after Icirrus City
            (500, 11, 28, 9, 'Location');  -- after Route 8 (28,1), before Route 9 (30,1)

        INSERT INTO schema_migrations (migration_name) VALUES ('bw_script_locations_v2');
    END IF;
END
$migration$;

COMMIT;
