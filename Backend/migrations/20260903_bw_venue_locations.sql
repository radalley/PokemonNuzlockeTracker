-- Script locations for BW trainer venues the walkthrough grain missed.
--
-- Full-fleet placement needs somewhere to put real, battleable trainers
-- whose venues were never script rows:
--   * Big Stadium & Small Court (new canon 502) -- Nimbasa's sports
--     venues; rotating daily trainers with progressive rematch tiers.
--   * Black City (new canon 503) -- Black-exclusive residents
--     (White Forest, its White twin, is already canon 254 in the script).
--   * Royal Unova (new canon 501) -- the post-game Castelia cruise and
--     its nightly passenger battles.
--   * Pokemon League (existing canon 226) -- hosts the Elite Four
--     rematch panel; the first-round fights stay boss events.
-- All are vg 11 Location rows; their trainers arrive via curation flagged
-- is_rematch/is_event so they never count toward run progress.

BEGIN;

SELECT pg_advisory_xact_lock(hashtext('lockley:bw_venue_locations_v1'));

CREATE TABLE IF NOT EXISTS schema_migrations (
    migration_name text PRIMARY KEY,
    applied_at timestamp with time zone NOT NULL DEFAULT current_timestamp
);

DO $migration$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM schema_migrations WHERE migration_name = 'bw_venue_locations_v1'
    ) THEN

        INSERT INTO canon_locations (canonical_location_id, canonical_location_name)
        VALUES
            (501, 'Royal Unova'),
            (502, 'Big Stadium & Small Court'),
            (503, 'Black City')
        ON CONFLICT (canonical_location_id) DO NOTHING;

        -- Positions: stadiums beside Nimbasa (12/10 follows Nimbasa's 12/9),
        -- the League after Victory Road, Black City beside White Forest,
        -- Royal Unova at the post-game tail after Challenger's Cave.
        INSERT INTO event_locations
            (canonical_location_id, sort_order, secondary_sort_order, is_active, version_group_id, event_type)
        VALUES
            (502, 12, 10, 1, 11, 'Location'),
            (226, 32,  2, 1, 11, 'Location'),
            (503, 41,  2, 1, 11, 'Location'),
            (501, 48,  1, 1, 11, 'Location');

        PERFORM setval('event_locations_canon_id_seq',
                       (SELECT max(canonical_location_id) FROM canon_locations));

        INSERT INTO schema_migrations (migration_name) VALUES ('bw_venue_locations_v1');

        RAISE NOTICE 'bw_venue_locations_v1 applied';
    ELSE
        RAISE NOTICE 'bw_venue_locations_v1 already applied; skipping';
    END IF;
END
$migration$;

COMMIT;
