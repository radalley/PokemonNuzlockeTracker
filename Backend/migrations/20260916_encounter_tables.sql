-- Wild encounter tables keep their shape.
--
-- Encounter docs list tables per floor/area and per season, and add rare
-- legendary slots on top of a table; the pool used to flatten all of that
-- onto the canonical location, so a cave's floors summed to 200-400%.
-- These additive columns let a row say which table it belongs to (area +
-- condition), what kind of entry it is (a normal slot, a 1% overlay on
-- top of a table, or a static encounter with no slot at all), and carry
-- the doc's badge and footnote. NULL area = the whole location; NULL
-- condition = always. `method` now holds a key from encounter_methods.py.

BEGIN;

SELECT pg_advisory_xact_lock(hashtext('lockley:encounter_tables_v1'));

CREATE TABLE IF NOT EXISTS schema_migrations (
    migration_name text PRIMARY KEY,
    applied_at timestamp with time zone NOT NULL DEFAULT current_timestamp
);

ALTER TABLE encounter_pool ADD COLUMN IF NOT EXISTS area text;
ALTER TABLE encounter_pool ADD COLUMN IF NOT EXISTS area_sort integer;
ALTER TABLE encounter_pool ADD COLUMN IF NOT EXISTS condition text;
ALTER TABLE encounter_pool ADD COLUMN IF NOT EXISTS slot_kind text NOT NULL DEFAULT 'slot';
ALTER TABLE encounter_pool ADD COLUMN IF NOT EXISTS tag text;
ALTER TABLE encounter_pool ADD COLUMN IF NOT EXISTS note text;

DO $migration$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM schema_migrations WHERE migration_name = 'encounter_tables_v1'
    ) THEN
        INSERT INTO schema_migrations (migration_name) VALUES ('encounter_tables_v1');
        RAISE NOTICE 'encounter_tables_v1 applied';
    ELSE
        RAISE NOTICE 'encounter_tables_v1 already applied; skipping';
    END IF;
END
$migration$;

COMMIT;
