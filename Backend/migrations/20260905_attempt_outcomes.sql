-- Attempt outcomes: declare an attempt dead and remember how it ended.
--
-- outcome NULL means the attempt is live; 'dead' ends it (a 'won' value
-- is reserved for the victory flow later). ended_by_trainer_id records
-- the killer when defeat was declared from a trainer battle; death_note
-- carries free text for wild/other deaths. started_at defaults for new
-- attempts (historical rows stay NULL -- their start time is unknown).
-- These columns also seed the future career screen.

BEGIN;

SELECT pg_advisory_xact_lock(hashtext('lockley:attempt_outcomes_v1'));

CREATE TABLE IF NOT EXISTS schema_migrations (
    migration_name text PRIMARY KEY,
    applied_at timestamp with time zone NOT NULL DEFAULT current_timestamp
);

-- Two steps on purpose: an inline DEFAULT on ADD COLUMN back-fills every
-- existing row with the migration timestamp; adding bare then setting the
-- default keeps historical rows honestly NULL while new inserts get one.
ALTER TABLE attempts ADD COLUMN IF NOT EXISTS started_at timestamp with time zone;
ALTER TABLE attempts ALTER COLUMN started_at SET DEFAULT current_timestamp;
ALTER TABLE attempts ADD COLUMN IF NOT EXISTS outcome text;
ALTER TABLE attempts ADD COLUMN IF NOT EXISTS ended_at timestamp with time zone;
ALTER TABLE attempts ADD COLUMN IF NOT EXISTS ended_by_trainer_id integer;
ALTER TABLE attempts ADD COLUMN IF NOT EXISTS death_note text;

DO $migration$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM schema_migrations WHERE migration_name = 'attempt_outcomes_v1'
    ) THEN
        INSERT INTO schema_migrations (migration_name) VALUES ('attempt_outcomes_v1');
        RAISE NOTICE 'attempt_outcomes_v1 applied';
    ELSE
        RAISE NOTICE 'attempt_outcomes_v1 already applied; skipping';
    END IF;
END
$migration$;

COMMIT;
