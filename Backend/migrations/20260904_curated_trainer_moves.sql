-- Observed-moves overlay: moves opponents were actually seen using.
--
-- Displayed trainer movesets are inference (level-up learnsets) except
-- where the ETL had doc-exact moves. This table records ground truth as
-- the admin observes it in play, keyed by the stable ETL identity
-- (version group + encounter name + party slot), so it survives every
-- re-extraction BY CONSTRUCTION -- no loader ever touches it. species_name
-- guards a slot whose occupant changed in a later extraction: the overlay
-- row simply stops matching instead of mislabeling the new species.
-- The portable form is a repo CSV (etl/pipelines/sync_curated_moves.py).

BEGIN;

SELECT pg_advisory_xact_lock(hashtext('lockley:curated_trainer_moves_v1'));

CREATE TABLE IF NOT EXISTS schema_migrations (
    migration_name text PRIMARY KEY,
    applied_at timestamp with time zone NOT NULL DEFAULT current_timestamp
);

CREATE TABLE IF NOT EXISTS curated_trainer_moves (
    version_group_id integer NOT NULL,
    trainer_key text NOT NULL,
    slot integer NOT NULL,
    species_name text NOT NULL,
    move_name text NOT NULL,
    noted_at timestamp with time zone NOT NULL DEFAULT current_timestamp,
    note text,
    PRIMARY KEY (version_group_id, trainer_key, slot, move_name)
);

DO $migration$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM schema_migrations WHERE migration_name = 'curated_trainer_moves_v1'
    ) THEN
        INSERT INTO schema_migrations (migration_name) VALUES ('curated_trainer_moves_v1');
        RAISE NOTICE 'curated_trainer_moves_v1 applied';
    ELSE
        RAISE NOTICE 'curated_trainer_moves_v1 already applied; skipping';
    END IF;
END
$migration$;

COMMIT;
