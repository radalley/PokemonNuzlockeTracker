-- WP1: trainer identity hardening.
-- Gives trainer_pokemon a real link to trainer_pool (trainer_id) plus the
-- party-fidelity columns Blaze Black data needs (slot, ability, ability_clean,
-- nature). Backfills trainer_id from the (encounter_name, version_group_id)
-- join and codifies current insertion order into slot.

BEGIN;

SELECT pg_advisory_xact_lock(hashtext('lockley:trainer_identity_v1'));

CREATE TABLE IF NOT EXISTS schema_migrations (
    migration_name text PRIMARY KEY,
    applied_at timestamp with time zone NOT NULL DEFAULT current_timestamp
);

ALTER TABLE trainer_pokemon ADD COLUMN IF NOT EXISTS trainer_id integer;
ALTER TABLE trainer_pokemon ADD COLUMN IF NOT EXISTS slot integer;
ALTER TABLE trainer_pokemon ADD COLUMN IF NOT EXISTS ability text;
ALTER TABLE trainer_pokemon ADD COLUMN IF NOT EXISTS ability_clean text;
ALTER TABLE trainer_pokemon ADD COLUMN IF NOT EXISTS nature text;

CREATE INDEX IF NOT EXISTS idx_trainer_pokemon_trainer_id
    ON trainer_pokemon (trainer_id);

DO $migration$
DECLARE
    backfilled integer;
    slotted integer;
    orphaned integer;
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM schema_migrations WHERE migration_name = 'trainer_identity_v1'
    ) THEN
        -- (encounter_name, version_group_id) groups were verified unique in
        -- trainer_pool on 2026-08-24; the count(*) = 1 guard keeps a future
        -- duplicate from mis-assigning identity.
        UPDATE trainer_pokemon t
        SET trainer_id = m.trainer_id
        FROM (
            SELECT encounter_name, version_group_id, min(trainer_id) AS trainer_id
            FROM trainer_pool
            GROUP BY encounter_name, version_group_id
            HAVING count(*) = 1
        ) m
        WHERE t.trainer_id IS NULL
          AND t.encounter_name = m.encounter_name
          AND t.version_group_id IS NOT DISTINCT FROM m.version_group_id;
        GET DIAGNOSTICS backfilled = ROW_COUNT;

        -- Codify current insertion order (the pk_id identity sequence) into
        -- slot so party ordering is stable and explicit from here on.
        UPDATE trainer_pokemon t
        SET slot = ranked.rn
        FROM (
            SELECT pk_id,
                   row_number() OVER (
                       PARTITION BY encounter_name, version_group_id
                       ORDER BY pk_id
                   ) AS rn
            FROM trainer_pokemon
        ) ranked
        WHERE t.pk_id = ranked.pk_id
          AND t.slot IS NULL;
        GET DIAGNOSTICS slotted = ROW_COUNT;

        SELECT count(*) INTO orphaned FROM trainer_pokemon WHERE trainer_id IS NULL;
        RAISE NOTICE 'trainer_identity_v1: trainer_id backfilled on % rows, slot set on % rows, % rows left unmatched (no trainer_pool row)',
            backfilled, slotted, orphaned;

        INSERT INTO schema_migrations (migration_name) VALUES ('trainer_identity_v1');
    END IF;
END
$migration$;

COMMIT;
