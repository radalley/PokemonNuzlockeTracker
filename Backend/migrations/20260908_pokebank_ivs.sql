-- Caught Pokemon remember their IVs.
--
-- The encounter panel records one IV per stat so a run's Pokemon can later
-- be exported to a damage calculator. One integer column per stat (rather
-- than a JSON blob) keeps them queryable and exportable as plain columns.
-- NULL means not recorded. The check covers the physical 0-31 range; the
-- app enforces its own minimum.

BEGIN;

SELECT pg_advisory_xact_lock(hashtext('lockley:pokebank_ivs_v1'));

CREATE TABLE IF NOT EXISTS schema_migrations (
    migration_name text PRIMARY KEY,
    applied_at timestamp with time zone NOT NULL DEFAULT current_timestamp
);

ALTER TABLE pokebank ADD COLUMN IF NOT EXISTS iv_hp integer;
ALTER TABLE pokebank ADD COLUMN IF NOT EXISTS iv_atk integer;
ALTER TABLE pokebank ADD COLUMN IF NOT EXISTS iv_def integer;
ALTER TABLE pokebank ADD COLUMN IF NOT EXISTS iv_spa integer;
ALTER TABLE pokebank ADD COLUMN IF NOT EXISTS iv_spd integer;
ALTER TABLE pokebank ADD COLUMN IF NOT EXISTS iv_spe integer;

DO $migration$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'pokebank_ivs_range'
    ) THEN
        ALTER TABLE pokebank ADD CONSTRAINT pokebank_ivs_range CHECK (
            (iv_hp IS NULL OR iv_hp BETWEEN 0 AND 31) AND
            (iv_atk IS NULL OR iv_atk BETWEEN 0 AND 31) AND
            (iv_def IS NULL OR iv_def BETWEEN 0 AND 31) AND
            (iv_spa IS NULL OR iv_spa BETWEEN 0 AND 31) AND
            (iv_spd IS NULL OR iv_spd BETWEEN 0 AND 31) AND
            (iv_spe IS NULL OR iv_spe BETWEEN 0 AND 31)
        );
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM schema_migrations WHERE migration_name = 'pokebank_ivs_v1'
    ) THEN
        INSERT INTO schema_migrations (migration_name) VALUES ('pokebank_ivs_v1');
        RAISE NOTICE 'pokebank_ivs_v1 applied';
    ELSE
        RAISE NOTICE 'pokebank_ivs_v1 already applied; skipping';
    END IF;
END
$migration$;

COMMIT;
