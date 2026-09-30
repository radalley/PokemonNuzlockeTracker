-- Blaze Black / Volt White: Pinwheel Forest becomes two script rows.
-- "Pinwheel Forest" (237) keeps the outer road, reachable before Lenora;
-- "Pinwheel Forest (Inside)" (504) opens in Burgh's split with its own
-- encounter, the interior tables (incl. Virizion's field) and the interior
-- trainers. Existing attempts' "Inner Pinwheel Forest" bonus slots (the
-- sheet import's extra column) become the new row's own encounter.
-- Guarded and idempotent; production untouched until applied there.
BEGIN;
SELECT pg_advisory_xact_lock(hashtext('lockley:bb_pinwheel_inside_v1'));
CREATE TABLE IF NOT EXISTS schema_migrations (
    migration_name text PRIMARY KEY,
    applied_at timestamptz NOT NULL DEFAULT current_timestamp
);

INSERT INTO canon_locations (canonical_location_id, canonical_location_name)
SELECT 504, 'Pinwheel Forest (Inside)'
WHERE NOT EXISTS (SELECT 1 FROM canon_locations WHERE canonical_location_id = 504);
DO $seq$
BEGIN
  IF to_regclass('event_locations_canon_id_seq') IS NOT NULL THEN
    PERFORM setval('event_locations_canon_id_seq',
                   greatest((SELECT max(canonical_location_id) FROM canon_locations), 504));
  END IF;
END
$seq$;

-- Same story slot as the outer forest; the name breaks the tie, so the
-- rows read "Pinwheel Forest" then "Pinwheel Forest (Inside)".
INSERT INTO event_locations (canonical_location_id, version_group_id, sort_order, secondary_sort_order, event_type)
SELECT 504, 1001, 8, 1, 'Location'
WHERE NOT EXISTS (SELECT 1 FROM event_locations WHERE canonical_location_id = 504 AND version_group_id = 1001);

-- Interior wild tables move to the new row; each row's remaining single
-- main area needs no tab, so its label is dropped (the field keeps its).
UPDATE encounter_pool SET canonical_location_id = 504, area = NULL, area_sort = 0
WHERE canonical_location_id = 237 AND game_id IN ('1001', '1002') AND area = 'Inside';
UPDATE encounter_pool SET canonical_location_id = 504
WHERE canonical_location_id = 237 AND game_id IN ('1001', '1002') AND area = 'Rumination Field';
UPDATE encounter_pool SET area = NULL, area_sort = 0
WHERE canonical_location_id = 237 AND game_id IN ('1001', '1002') AND area = 'Outside';

-- Interior trainers: the vanilla ROM's map zone 154 (Kentaro, Zachary,
-- Keita, Juliet, Homer, Shery) plus the story grunts; Lee, Irene and Miguel
-- are inside by the game's layout (no ROM placement in the extract).
-- Forrest, Audra, Sammy, Millie, Mayo & May, Nicholas and Eva stay on the
-- outer road (zone 155).
CREATE TEMP TABLE _bb_pinwheel_inside (trainer_key text) ON COMMIT DROP;
INSERT INTO _bb_pinwheel_inside VALUES
    ('TRAINER_BB_BLACK_BELT_KENTARO'), ('TRAINER_BB_YOUNGSTER_ZACHARY'), ('TRAINER_BB_YOUNGSTER_KEITA'),
    ('TRAINER_BB_PRESCHOOLER_JULIET'), ('TRAINER_BB_PRESCHOOLER_HOMER'), ('TRAINER_BB_NURSE_SHERY'),
    ('TRAINER_BB_BATTLE_GIRL_LEE'), ('TRAINER_BB_PKMN_RANGER_IRENE'), ('TRAINER_BB_PKMN_RANGER_MIGUEL'),
    ('TRAINER_BB_TEAM_PLASMA_GRUNT_TEAM_PLASMA_GRUNT'), ('TRAINER_BB_TEAM_PLASMA_GRUNT_TEAM_PLASMA_GRUNT_2'),
    ('TRAINER_BB_TEAM_PLASMA_GRUNT_TEAM_PLASMA_GRUNT_3'), ('TRAINER_BB_TEAM_PLASMA_GRUNT_TEAM_PLASMA_GRUNT_4');
UPDATE trainer_pool tp SET canonical_location_id = 504, area_id = NULL
FROM _bb_pinwheel_inside i
WHERE tp.version_group_id = 1001 AND tp.encounter_name = i.trainer_key AND tp.canonical_location_id = 237;
-- The durable decision, so a re-extraction lands them inside again.
INSERT INTO curated_trainer_placements (version_group_id, trainer_key, canonical_location_id, area_id, status, note)
SELECT 1001, i.trainer_key, 504, NULL, 'placed', 'Pinwheel Forest interior (split from the outer road 2026-09-25)'
FROM _bb_pinwheel_inside i
WHERE EXISTS (SELECT 1 FROM trainer_pool tp WHERE tp.version_group_id = 1001 AND tp.encounter_name = i.trainer_key)
ON CONFLICT (version_group_id, trainer_key) DO UPDATE SET
  canonical_location_id = 504, area_id = NULL, status = 'placed', decided_at = current_timestamp;

-- Availability: the area rules are moot; each row opens in its own split.
DO $rules$
BEGIN
  IF to_regclass('public.curated_availability') IS NOT NULL THEN
    DELETE FROM curated_availability WHERE version_group_id = 1001 AND subject_kind = 'area' AND subject_key IN ('237|Outside', '237|Inside');
    INSERT INTO curated_availability (version_group_id, subject_kind, subject_key, opens_in, gate_key, note, source) VALUES
      (1001, 'location', '237', 'badge:34', NULL, 'The outer road is reachable before Lenora.', 'docs/blaze-black-item-seed-analysis.md'),
      (1001, 'location', '504', 'badge:35', NULL, 'The interior opens after Lenora, in Burgh''s split.', 'user, 2026-09-25')
    ON CONFLICT (version_group_id, subject_kind, subject_key) DO NOTHING;
  END IF;
END
$rules$;

-- Existing attempts: an extra Pinwheel slot that holds an interior-only
-- family (or was named as the inner forest) becomes the new row's own
-- encounter; the bonus row is retired, never deleted.
DO $moves$
BEGIN
  IF to_regclass('public.bonus_locations') IS NOT NULL AND to_regclass('public.evolutions') IS NOT NULL THEN
    CREATE TEMP TABLE _bb_inside_family ON COMMIT DROP AS
      WITH inside AS (
        SELECT DISTINCT species_id FROM encounter_pool WHERE canonical_location_id = 504 AND game_id IN ('1001', '1002')
      ), once AS (
        SELECT e.to_species_id AS species_id FROM evolutions e JOIN inside i ON e.from_species_id = i.species_id
      )
      SELECT species_id FROM inside
      UNION SELECT species_id FROM once
      UNION SELECT e.to_species_id FROM evolutions e JOIN once o ON e.from_species_id = o.species_id;
    CREATE TEMP TABLE _bb_pinwheel_moves ON COMMIT DROP AS
      SELECT pb.pokemon_id, bl.bonus_location_id
      FROM pokebank pb
      JOIN bonus_locations bl
        ON bl.attempt_id = pb.attempt_id AND bl.canonical_location_id = 237
       AND bl.secondary_sort_order = pb.bonus_location AND bl.is_active = 1
      WHERE pb.canonical_location_id = 237 AND pb.bonus_location > 1
        AND (bl.canonical_name ILIKE '%inner%'
             OR pb.species_id IN (SELECT species_id FROM _bb_inside_family))
        AND NOT EXISTS (SELECT 1 FROM pokebank x WHERE x.attempt_id = pb.attempt_id AND x.canonical_location_id = 504 AND x.bonus_location = 1);
    UPDATE pokebank SET canonical_location_id = 504, bonus_location = 1
    WHERE pokemon_id IN (SELECT pokemon_id FROM _bb_pinwheel_moves);
    UPDATE bonus_locations SET is_active = 0
    WHERE bonus_location_id IN (SELECT bonus_location_id FROM _bb_pinwheel_moves);
  END IF;
END
$moves$;

INSERT INTO schema_migrations(migration_name) VALUES ('bb_pinwheel_inside_v1')
ON CONFLICT DO NOTHING;
COMMIT;
