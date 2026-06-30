BEGIN;

SELECT pg_advisory_xact_lock(hashtext('lockley:run_last_opened_backfill_v1'));

CREATE TABLE IF NOT EXISTS schema_migrations (
    migration_name text PRIMARY KEY,
    applied_at timestamp with time zone NOT NULL DEFAULT current_timestamp
);

ALTER TABLE runs ADD COLUMN IF NOT EXISTS last_opened_at timestamp with time zone;
ALTER TABLE runs ADD COLUMN IF NOT EXISTS last_opened_attempt_number integer;

DO $migration$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM schema_migrations
        WHERE migration_name = 'run_last_opened_backfill_v1'
    ) THEN
        UPDATE runs target
        SET
            last_opened_at = current_timestamp,
            last_opened_attempt_number = (
                SELECT max(attempt_number)
                FROM attempts
                WHERE attempts.run_id = target.run_id
            )
        WHERE target.run_id IN (
            SELECT candidate.run_id
            FROM runs candidate
            WHERE candidate.user_id IS NOT NULL
              AND NOT EXISTS (
                  SELECT 1
                  FROM runs marked
                  WHERE marked.user_id = candidate.user_id
                    AND marked.last_opened_at IS NOT NULL
              )
              AND candidate.run_id = (
                  SELECT newest.run_id
                  FROM runs newest
                  WHERE newest.user_id = candidate.user_id
                  ORDER BY newest.created_at DESC NULLS LAST, newest.run_id DESC
                  LIMIT 1
              )
        );

        INSERT INTO schema_migrations (migration_name)
        VALUES ('run_last_opened_backfill_v1');
    END IF;
END
$migration$;

COMMIT;
