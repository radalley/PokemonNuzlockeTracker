-- WP6: trainers-only script locations for Black/White.
--
-- 48 extracted BW trainers stand in places that never got canonical
-- locations because they have no wild encounters: Nimbasa City (the stadiums
-- and Musical Theater), Mistralton City, Opelucid City, and the post-League
-- Challenger's Cave. Without a script row, those trainers are structurally
-- invisible no matter how well placed they are.
--
-- This adds the locations and their BW (version group 11) script rows.
-- The frontend already renders locations that have trainers but no
-- encounter pool. event_locations.sort_order is an integer, so each city
-- shares its neighbor's slot and uses secondary_sort_order to come last in
-- it, which still lands before the gym's fractional boss row (Nimbasa Gym
-- 12.2, Mistralton Gym 20.1, Opelucid Gym 30.1); Challenger's Cave follows
-- the Champion (46.1).
--
-- The Shopping Mall Nine trainers are handled by curation instead: the mall
-- sits on Route 9, which is already in the script.

BEGIN;

SELECT pg_advisory_xact_lock(hashtext('lockley:bw_script_locations_v1'));

CREATE TABLE IF NOT EXISTS schema_migrations (
    migration_name text PRIMARY KEY,
    applied_at timestamp with time zone NOT NULL DEFAULT current_timestamp
);

DO $migration$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM schema_migrations WHERE migration_name = 'bw_script_locations_v1'
    ) THEN
        IF EXISTS (
            SELECT 1 FROM canon_locations
            WHERE canonical_location_id IN (492, 493, 494, 495)
        ) THEN
            RAISE EXCEPTION 'canonical_location_ids 492-495 are already taken';
        END IF;

        INSERT INTO canon_locations (canonical_location_id, canonical_location_name) VALUES
            (492, 'Nimbasa City'),
            (493, 'Mistralton City'),
            (494, 'Opelucid City'),
            (495, 'Challenger''s Cave');

        INSERT INTO event_locations
            (canonical_location_id, version_group_id, sort_order, secondary_sort_order, event_type)
        VALUES
            (492, 11, 12, 9, 'Location'),  -- after Relic Castle (12,1), before Nimbasa Gym (12.2)
            (493, 11, 20, 9, 'Location'),  -- after Route 7 (20,1), before Mistralton Gym (20.1)
            (494, 11, 30, 9, 'Location'),  -- after Route 9 (30,1), before Opelucid Gym (30.1)
            (495, 11, 47, 1, 'Location');  -- after the Champion (46.1)

        INSERT INTO schema_migrations (migration_name) VALUES ('bw_script_locations_v1');
    END IF;
END
$migration$;

COMMIT;
