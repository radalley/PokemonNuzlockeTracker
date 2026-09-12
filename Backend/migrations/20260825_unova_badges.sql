-- WP2: Unova badges.
-- BADGE_DEFINITIONS / EVENT_BADGE_MAPPINGS in backend.py stopped at Sinnoh,
-- so BW and B2W2 gym victories awarded nothing. The Python constants now
-- include Unova, but their seeding runs under the already-applied
-- badge_architecture_v1 guard -- this migration performs the same seeding on
-- existing databases. Badge sprites 33-42 already ship in
-- Frontend/public/sprites/Badges/.

BEGIN;

SELECT pg_advisory_xact_lock(hashtext('lockley:unova_badges_v1'));

CREATE TABLE IF NOT EXISTS schema_migrations (
    migration_name text PRIMARY KEY,
    applied_at timestamp with time zone NOT NULL DEFAULT current_timestamp
);

DO $migration$
DECLARE
    mapped integer;
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM schema_migrations WHERE migration_name = 'unova_badges_v1'
    ) THEN
        INSERT INTO badges (badge_id, badge_name, region, sprite_key)
        VALUES
            (33, 'Trio Badge',   'Unova', '33'),
            (34, 'Basic Badge',  'Unova', '34'),
            (35, 'Insect Badge', 'Unova', '35'),
            (36, 'Bolt Badge',   'Unova', '36'),
            (37, 'Quake Badge',  'Unova', '37'),
            (38, 'Jet Badge',    'Unova', '38'),
            (39, 'Freeze Badge', 'Unova', '39'),
            (40, 'Legend Badge', 'Unova', '40'),
            (41, 'Toxic Badge',  'Unova', '41'),
            (42, 'Wave Badge',   'Unova', '42')
        ON CONFLICT (badge_id) DO UPDATE SET
            badge_name = excluded.badge_name,
            region = excluded.region,
            sprite_key = excluded.sprite_key;

        -- Same title normalization as _ensure_badge_schema in backend.py.
        WITH mapping (version_group_id, title_fragment, badge_id) AS (
            VALUES
                (11, 'striaton city gym',   33),
                (11, 'nacrene city gym',    34),
                (11, 'castelia city gym',   35),
                (14, 'castelia city gym',   35),
                (11, 'nimbasa city gym',    36),
                (14, 'nimbasa city gym',    36),
                (11, 'driftveil city gym',  37),
                (14, 'driftveil city gym',  37),
                (11, 'mistralton city gym', 38),
                (14, 'mistralton city gym', 38),
                (11, 'icirrus city gym',    39),
                (11, 'opelucid city gym',   40),
                (14, 'opelucid city gym',   40),
                (14, 'aspertia city gym',   34),
                (14, 'virbank city gym',    41),
                (14, 'humilau city gym',    42)
        )
        UPDATE event_bosses eb
        SET badge_id = m.badge_id
        FROM mapping m
        WHERE eb.badge_id IS NULL
          AND eb.version_group_id = m.version_group_id
          AND regexp_replace(lower(coalesce(eb.encounter_title, '')), '\s+', ' ', 'g') = m.title_fragment;
        GET DIAGNOSTICS mapped = ROW_COUNT;

        RAISE NOTICE 'unova_badges_v1: badge_id set on % Unova gym event rows', mapped;

        INSERT INTO schema_migrations (migration_name) VALUES ('unova_badges_v1');
    END IF;
END
$migration$;

COMMIT;
