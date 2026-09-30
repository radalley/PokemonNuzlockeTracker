-- Caught Pokemon remember their ability.
--
-- The ability picker on the encounter row saves the selected ability onto
-- the pokebank row. Text token as stored in species_abilities (display
-- formatting is client-side); NULL means never chosen.

BEGIN;

SELECT pg_advisory_xact_lock(hashtext('lockley:pokebank_ability_v1'));

CREATE TABLE IF NOT EXISTS schema_migrations (
    migration_name text PRIMARY KEY,
    applied_at timestamp with time zone NOT NULL DEFAULT current_timestamp
);

ALTER TABLE pokebank ADD COLUMN IF NOT EXISTS ability text;

DO $migration$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM schema_migrations WHERE migration_name = 'pokebank_ability_v1'
    ) THEN
        INSERT INTO schema_migrations (migration_name) VALUES ('pokebank_ability_v1');
        RAISE NOTICE 'pokebank_ability_v1 applied';
    ELSE
        RAISE NOTICE 'pokebank_ability_v1 already applied; skipping';
    END IF;
END
$migration$;

COMMIT;
