-- WP7: the variant model.
--
-- A ROM hack is its own games row with its own version group (reserved id
-- range: 1000+), linked to the vanilla game it modifies via base_game_id.
-- version_group_id is already a hard equality in every trainer, boss, and
-- script query, so a hack's data is fully isolated with no read-path
-- changes; base_game_id exists for UI grouping and asset fallback.
--
-- event_bosses gains what hack data needs and vanilla display wanted:
--   battle_type   (single/double/rotation/triple, display-only)
--   is_level_cap  replaces the frontend's hardcoded event_type string list.
--     Backfill marks gym/Elite Four/Champion rows. Gen 5's rows have blank
--     event_type, so the old string match never showed caps for them --
--     badge_id and title patterns catch those.

BEGIN;

SELECT pg_advisory_xact_lock(hashtext('lockley:game_variants_v1'));

CREATE TABLE IF NOT EXISTS schema_migrations (
    migration_name text PRIMARY KEY,
    applied_at timestamp with time zone NOT NULL DEFAULT current_timestamp
);

ALTER TABLE games ADD COLUMN IF NOT EXISTS base_game_id integer;
ALTER TABLE games ADD COLUMN IF NOT EXISTS is_rom_hack boolean NOT NULL DEFAULT false;
ALTER TABLE event_bosses ADD COLUMN IF NOT EXISTS battle_type text;
ALTER TABLE event_bosses ADD COLUMN IF NOT EXISTS is_level_cap boolean;

DO $migration$
DECLARE
    caps integer;
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM schema_migrations WHERE migration_name = 'game_variants_v1'
    ) THEN
        UPDATE event_bosses
        SET is_level_cap = (
            lower(coalesce(event_type, '')) IN ('gym leader', 'elite four', 'champion')
            OR badge_id IS NOT NULL
            OR encounter_title ILIKE '%elite four%'
            OR encounter_title ILIKE '%champion%'
        )
        WHERE is_level_cap IS NULL;
        GET DIAGNOSTICS caps = ROW_COUNT;

        RAISE NOTICE 'game_variants_v1: is_level_cap backfilled on % boss rows (% cap rows)',
            caps, (SELECT count(*) FROM event_bosses WHERE is_level_cap);

        INSERT INTO schema_migrations (migration_name) VALUES ('game_variants_v1');
    END IF;
END
$migration$;

COMMIT;
