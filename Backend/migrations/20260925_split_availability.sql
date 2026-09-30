-- Split availability: which split (gym-to-gym segment) a location, an
-- encounter area, one wild table, or a trainer becomes reachable in.
-- Nothing in the ETL sources carries this, so it is curated data layered
-- over story-order defaults (Backend/split_availability.py resolves it).
-- Subjects are keyed by stable text, never by encounter_id, which an ETL
-- --replace renumbers. Seeds insert with DO NOTHING so admin edits survive
-- a re-application.
BEGIN;
SELECT pg_advisory_xact_lock(hashtext('lockley:split_availability_v1'));
CREATE TABLE IF NOT EXISTS schema_migrations (
    migration_name text PRIMARY KEY,
    applied_at timestamptz NOT NULL DEFAULT current_timestamp
);

-- A named requirement (Surf, the rod, shaking grass) and the split it
-- opens in. opens_in NULL means "not decided yet": the resolver reports it
-- as unknown rather than guessing.
CREATE TABLE IF NOT EXISTS split_gates (
    version_group_id integer NOT NULL,
    gate_key text NOT NULL CHECK (length(gate_key) BETWEEN 1 AND 60),
    label text NOT NULL CHECK (length(trim(label)) BETWEEN 1 AND 80),
    opens_in text CHECK (opens_in IS NULL OR length(opens_in) BETWEEN 1 AND 240),
    default_methods text[] NOT NULL DEFAULT '{}',
    sort_order integer NOT NULL DEFAULT 0,
    note text,
    source text,
    PRIMARY KEY (version_group_id, gate_key)
);

-- Exceptions to the derived defaults. Exactly one of opens_in / gate_key.
CREATE TABLE IF NOT EXISTS curated_availability (
    version_group_id integer NOT NULL,
    subject_kind text NOT NULL CHECK (subject_kind IN ('location', 'area', 'table', 'trainer')),
    subject_key text NOT NULL CHECK (length(subject_key) BETWEEN 1 AND 240),
    opens_in text CHECK (opens_in IS NULL OR length(opens_in) BETWEEN 1 AND 240),
    gate_key text,
    note text,
    source text,
    decided_at timestamptz NOT NULL DEFAULT current_timestamp,
    PRIMARY KEY (version_group_id, subject_kind, subject_key),
    CHECK ((opens_in IS NOT NULL) <> (gate_key IS NOT NULL))
);

-- The Flask API owns access checks; never expose through PostgREST roles.
ALTER TABLE split_gates ENABLE ROW LEVEL SECURITY;
ALTER TABLE curated_availability ENABLE ROW LEVEL SECURITY;

-- Blaze Black / Volt White (version group 1001). Only facts already
-- recorded in the repo plus the user's stated examples; everything else
-- inherits the story-order default until curated in admin edit mode.
INSERT INTO split_gates (version_group_id, gate_key, label, opens_in, default_methods, sort_order, note, source) VALUES
    (1001, 'shaking-grass', 'Shaking grass', 'badge:34', '{grass-spots,cave-spots}', 10,
     'Rustling grass and dust clouds appear after the first badge.',
     'Drayano 3.1 Wild Pokemon.txt preamble; encounter_methods.py'),
    (1001, 'fishing', 'Super Rod', 'badge:34', '{fish,fish-spots}', 20,
     'Blaze Black moves the Super Rod to Route 3, reached in Lenora''s split.',
     'docs/blaze-black-item-seed-analysis.md'),
    (1001, 'surf', 'Surf', NULL, '{surf,surf-spots}', 30,
     'Which split Surf opens in is not decided yet; set it from Game flags.',
     'docs/blaze-black-item-seed-analysis.md (unavailable through Burgh)')
ON CONFLICT (version_group_id, gate_key) DO NOTHING;

INSERT INTO curated_availability (version_group_id, subject_kind, subject_key, opens_in, gate_key, note, source) VALUES
    (1001, 'table', '3||dark-grass|', NULL, 'surf', 'Route 1 dark grass is behind water.', 'docs/blaze-black-item-seed-analysis.md'),
    (1001, 'area', '235|B1F', NULL, 'surf', 'Wellspring Cave B1F needs Surf.', 'docs/blaze-black-item-seed-analysis.md'),
    (1001, 'area', '237|Outside', 'badge:34', NULL, 'Pinwheel Forest Outside is reachable before Lenora.', 'docs/blaze-black-item-seed-analysis.md'),
    (1001, 'area', '237|Inside', 'badge:35', NULL, 'Pinwheel Forest Inside opens after Lenora.', 'docs/blaze-black-item-seed-analysis.md'),
    (1001, 'location', '234', 'badge:33', NULL, 'Dreamyard (gift monkey, first trainers) is open before the Striaton Gym.', 'user, 2026-09-24'),
    (1001, 'trainer', 'TRAINER_BB_PLASMA_GRUNT_PLASMA_GRUNT', 'badge:34', NULL, 'Dreamyard Plasma Grunts arrive after the first gym.', 'user, 2026-09-24'),
    (1001, 'trainer', 'TRAINER_BB_PLASMA_GRUNT_PLASMA_GRUNT_2', 'badge:34', NULL, 'Dreamyard Plasma Grunts arrive after the first gym.', 'user, 2026-09-24'),
    (1001, 'location', '9', 'badge:35', NULL, 'Route 4 can be done before Burgh.', 'user, 2026-09-24')
ON CONFLICT (version_group_id, subject_kind, subject_key) DO NOTHING;

INSERT INTO schema_migrations(migration_name) VALUES ('split_availability_v1')
ON CONFLICT DO NOTHING;
COMMIT;
