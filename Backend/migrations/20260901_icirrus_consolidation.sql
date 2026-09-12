-- Consolidate the misspelled Icirrus canon rows onto their correct twins.
--
-- canon 248 "Iccirus City" and 250 "Moor of Icarus" predate the correctly
-- spelled 498 "Icirrus City" and 499 "Moor of Icirrus" (added for the
-- Blaze Black script build). Both pairs ended up in the vg 11 and vg 1001
-- scripts simultaneously -- two Icirrus City rows on the run page -- with
-- vanilla trainers on the old ids and hack data on the new ones. Every
-- reference moves old -> new, the duplicate script rows go away (the
-- surviving Moor row takes over the old row's walkthrough position after
-- Route 8), and the misspelled canon rows are retired. No player data
-- references either old id (verified: pokebank, bonus_locations,
-- locations all empty for 248/250).

BEGIN;

SELECT pg_advisory_xact_lock(hashtext('lockley:icirrus_consolidation_v1'));

CREATE TABLE IF NOT EXISTS schema_migrations (
    migration_name text PRIMARY KEY,
    applied_at timestamp with time zone NOT NULL DEFAULT current_timestamp
);

DO $migration$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM schema_migrations WHERE migration_name = 'icirrus_consolidation_v1'
    ) THEN

        -- The surviving Moor row inherits the retired row's script position
        -- (vanilla walks the Moor after Route 8, not beside Icirrus City).
        UPDATE event_locations el
        SET sort_order = old.sort_order,
            secondary_sort_order = old.secondary_sort_order
        FROM event_locations old
        WHERE el.canonical_location_id = 499
          AND old.canonical_location_id = 250
          AND old.version_group_id = el.version_group_id;

        -- Drop old script rows where the correct twin already exists...
        DELETE FROM event_locations el
        USING event_locations keep
        WHERE el.canonical_location_id = 248
          AND keep.canonical_location_id = 498
          AND keep.version_group_id = el.version_group_id;
        DELETE FROM event_locations el
        USING event_locations keep
        WHERE el.canonical_location_id = 250
          AND keep.canonical_location_id = 499
          AND keep.version_group_id = el.version_group_id;
        -- ...and repoint the rest (vg 14 has only the old rows).
        UPDATE event_locations SET canonical_location_id = 498 WHERE canonical_location_id = 248;
        UPDATE event_locations SET canonical_location_id = 499 WHERE canonical_location_id = 250;

        UPDATE trainer_pool SET canonical_location_id = 498 WHERE canonical_location_id = 248;
        UPDATE trainer_pool SET canonical_location_id = 499 WHERE canonical_location_id = 250;
        UPDATE encounter_pool SET canonical_location_id = 498 WHERE canonical_location_id = 248;
        UPDATE encounter_pool SET canonical_location_id = 499 WHERE canonical_location_id = 250;
        UPDATE location_areas SET canonical_location_id = 498 WHERE canonical_location_id = 248;
        UPDATE location_areas SET canonical_location_id = 499 WHERE canonical_location_id = 250;
        UPDATE trainer_placement_suggestions SET canonical_location_id = 498 WHERE canonical_location_id = 248;
        UPDATE trainer_placement_suggestions SET canonical_location_id = 499 WHERE canonical_location_id = 250;
        UPDATE curated_trainer_placements SET canonical_location_id = 498 WHERE canonical_location_id = 248;
        UPDATE curated_trainer_placements SET canonical_location_id = 499 WHERE canonical_location_id = 250;
        UPDATE pokebank SET canonical_location_id = 498 WHERE canonical_location_id = 248;
        UPDATE pokebank SET canonical_location_id = 499 WHERE canonical_location_id = 250;
        UPDATE bonus_locations SET canonical_location_id = 498 WHERE canonical_location_id = 248;
        UPDATE bonus_locations SET canonical_location_id = 499 WHERE canonical_location_id = 250;
        UPDATE locations SET canonical_location_id = 498 WHERE canonical_location_id = 248;
        UPDATE locations SET canonical_location_id = 499 WHERE canonical_location_id = 250;

        DELETE FROM canon_locations WHERE canonical_location_id IN (248, 250);

        INSERT INTO schema_migrations (migration_name) VALUES ('icirrus_consolidation_v1');

        RAISE NOTICE 'icirrus_consolidation_v1 applied';
    ELSE
        RAISE NOTICE 'icirrus_consolidation_v1 already applied; skipping';
    END IF;
END
$migration$;

COMMIT;
