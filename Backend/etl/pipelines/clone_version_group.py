"""Clone a version group's data into a new (hack) version group.

The variant model gives each ROM hack its own games rows and its own version
group in the reserved 1000+ range; version_group_id is a hard equality in
every read path, so the clone is fully isolated from its base. This pipeline
materializes the clone:

  always        games rows (valid_game per --valid-game, default 'hidden',
                base_game_id set, is_rom_hack true) and event_locations
                (the route script) and location_areas
  --full        also trainer_pool + trainer_pokemon + event_bosses +
                encounter_pool, remapped onto the new ids -- a playable
                copy of the base game

A real hack seeds with the structural clone and loads its own trainers and
encounters over it; --full exists for the rails smoke test and for hacks
that only change part of the game.

    python -m etl.pipelines.clone_version_group --base-vg 11 --new-vg 1001 \\
        --game "1001:17:Test Hack Black" --full --apply

Game mappings are new_game_id:base_game_id:name. Everything runs in one
guarded transaction; dry run is the default.
"""
import argparse
import sys

from .. import db


def _quote(text):
    return "'" + str(text).replace("'", "''") + "'"


def build_sql(base_vg, new_vg, games, full=False, valid_game="hidden", rollback=True):
    """games: list of (new_game_id, base_game_id, name)."""
    new_game_ids = [g[0] for g in games]
    games_values = ", ".join(
        f"({new_id}, {base_id}, {_quote(name)})" for new_id, base_id, name in games
    )
    game_id_cases = " ".join(
        f"WHEN {base_id} THEN {new_id}" for new_id, base_id, _ in games
    )
    base_id_list = ", ".join(str(base_id) for _, base_id, _ in games)

    parts = [f"""
BEGIN;

DO $guards$
BEGIN
  IF {new_vg} < 1000 THEN
    RAISE EXCEPTION 'Hack version groups use the reserved range 1000+';
  END IF;
  IF EXISTS (SELECT 1 FROM games WHERE version_group_id = {new_vg})
     OR EXISTS (SELECT 1 FROM games WHERE game_id IN ({', '.join(map(str, new_game_ids))}))
     OR EXISTS (SELECT 1 FROM event_locations WHERE version_group_id = {new_vg})
     OR EXISTS (SELECT 1 FROM trainer_pool WHERE version_group_id = {new_vg}) THEN
    RAISE EXCEPTION 'Version group {new_vg} or its game ids are already in use';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM event_locations WHERE version_group_id = {base_vg}) THEN
    RAISE EXCEPTION 'Base version group {base_vg} has no script to clone';
  END IF;
END $guards$;

INSERT INTO games (game_id, name, game_tag, generation, version_group_id, valid_game, base_game_id, is_rom_hack)
SELECT v.new_id, v.name, base.game_tag, base.generation, {new_vg}, {_quote(valid_game)}, v.base_id, true
FROM (VALUES {games_values}) AS v(new_id, base_id, name)
JOIN games base ON base.game_id = v.base_id;

INSERT INTO event_locations (canonical_location_id, version_group_id, sort_order, secondary_sort_order, event_type)
SELECT canonical_location_id, {new_vg}, sort_order, secondary_sort_order, event_type
FROM event_locations WHERE version_group_id = {base_vg};

INSERT INTO location_areas (canonical_location_id, version_group_id, area_name, area_kind, sort_order, source_key)
SELECT canonical_location_id, {new_vg}, area_name, area_kind, sort_order, source_key
FROM location_areas WHERE version_group_id = {base_vg};
"""]

    if full:
        parts.append(f"""
INSERT INTO trainer_pool (
  encounter_name, trainer_name, trainer_class, canonical_location_id,
  is_rematch, is_event, trainer_items, trainer_pic, trainer_double,
  details, version_group_id, load_build, game_id, area_id
)
SELECT
  tp.encounter_name, tp.trainer_name, tp.trainer_class, tp.canonical_location_id,
  tp.is_rematch, tp.is_event, tp.trainer_items, tp.trainer_pic, tp.trainer_double,
  tp.details, {new_vg}, tp.load_build,
  CASE tp.game_id {game_id_cases} ELSE NULL END,
  new_la.area_id
FROM trainer_pool tp
LEFT JOIN location_areas old_la ON old_la.area_id = tp.area_id
LEFT JOIN location_areas new_la
  ON new_la.version_group_id = {new_vg}
 AND new_la.canonical_location_id = old_la.canonical_location_id
 AND new_la.area_name = old_la.area_name
WHERE tp.version_group_id = {base_vg}
  -- A row exclusive to a base game that was not mapped (e.g. cloning only
  -- Black from the Black/White pair) is dropped, never turned shared.
  AND (tp.game_id IS NULL OR tp.game_id IN ({base_id_list}));

INSERT INTO trainer_pokemon (
  encounter_name, species_name, lvl, moves, held_item, iv,
  version_group_id, load_build, slot, ability, ability_clean, nature, trainer_id
)
SELECT
  t.encounter_name, t.species_name, t.lvl, t.moves, t.held_item, t.iv,
  {new_vg}, t.load_build, t.slot, t.ability, t.ability_clean, t.nature,
  new_tp.trainer_id
FROM trainer_pokemon t
JOIN trainer_pool base_tp ON base_tp.trainer_id = t.trainer_id
JOIN trainer_pool new_tp
  ON new_tp.version_group_id = {new_vg}
 AND new_tp.encounter_name = base_tp.encounter_name
WHERE t.version_group_id = {base_vg};

WITH numbered AS (
  SELECT eb.*, new_tp.trainer_id AS new_trainer_id,
         row_number() OVER (ORDER BY eb.event_id) AS rn,
         (SELECT coalesce(max(event_id), 0) FROM event_bosses) AS current_max
  FROM event_bosses eb
  JOIN trainer_pool base_tp ON base_tp.trainer_id = eb.trainer_id
  JOIN trainer_pool new_tp
    ON new_tp.version_group_id = {new_vg}
   AND new_tp.encounter_name = base_tp.encounter_name
  WHERE eb.version_group_id = {base_vg}
    AND (eb.game_id IS NULL OR eb.game_id IN ({base_id_list}))
)
INSERT INTO event_bosses (
  event_id, trainer_id, sort_order, encounter_title, starter, type_focus,
  version_group_id, event_type, game_id, badge_id, battle_type, is_level_cap
)
SELECT
  current_max + rn, new_trainer_id, sort_order, encounter_title, starter, type_focus,
  {new_vg}, event_type,
  CASE game_id {game_id_cases} ELSE NULL END,
  badge_id, battle_type, is_level_cap
FROM numbered;

SELECT setval(
  pg_get_serial_sequence('event_bosses', 'event_id'),
  (SELECT max(event_id) FROM event_bosses),
  true
);

INSERT INTO encounter_pool (game_id, location_id, canonical_location_id, species_id, min_level, max_level, method, enounter_rate)
SELECT v.new_id, ep.location_id, ep.canonical_location_id, ep.species_id, ep.min_level, ep.max_level, ep.method, ep.enounter_rate
FROM encounter_pool ep
JOIN (VALUES {games_values}) AS v(new_id, base_id, name)
  ON nullif(ep.game_id::text, '')::integer = v.base_id;

DO $verify$
BEGIN
  IF (SELECT count(*) FROM trainer_pool WHERE version_group_id = {new_vg})
     <> (SELECT count(*) FROM trainer_pool WHERE version_group_id = {base_vg}
         AND (game_id IS NULL OR game_id IN ({base_id_list}))) THEN
    RAISE EXCEPTION 'Cloned trainer count does not match the base';
  END IF;
  IF EXISTS (
    SELECT 1 FROM trainer_pokemon WHERE version_group_id = {new_vg} AND trainer_id IS NULL
  ) THEN
    RAISE EXCEPTION 'Cloned party rows are missing trainer links';
  END IF;
  IF (SELECT count(*) FROM event_bosses WHERE version_group_id = {new_vg})
     <> (SELECT count(*) FROM event_bosses WHERE version_group_id = {base_vg}
         AND (game_id IS NULL OR game_id IN ({base_id_list}))) THEN
    RAISE EXCEPTION 'Cloned boss count does not match the base';
  END IF;
END $verify$;
""")

    metrics = [
        ("games", f"SELECT count(*) FROM games WHERE version_group_id = {new_vg}"),
        ("script_locations", f"SELECT count(*) FROM event_locations WHERE version_group_id = {new_vg}"),
        ("areas", f"SELECT count(*) FROM location_areas WHERE version_group_id = {new_vg}"),
        ("trainers", f"SELECT count(*) FROM trainer_pool WHERE version_group_id = {new_vg}"),
        ("party_rows", f"SELECT count(*) FROM trainer_pokemon WHERE version_group_id = {new_vg}"),
        ("bosses", f"SELECT count(*) FROM event_bosses WHERE version_group_id = {new_vg}"),
        ("boss_badges", f"SELECT count(*) FROM event_bosses WHERE version_group_id = {new_vg} AND badge_id IS NOT NULL"),
    ]
    for name, sql in metrics:
        parts.append(f"SELECT '{name}' AS metric, ({sql}) AS value;")

    parts.append("ROLLBACK;" if rollback else "COMMIT;")
    return "\n".join(parts) + "\n"


def parse_game(value):
    bits = value.split(":", 2)
    if len(bits) != 3:
        raise argparse.ArgumentTypeError("Expected new_game_id:base_game_id:name")
    return int(bits[0]), int(bits[1]), bits[2]


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--base-vg", type=int, required=True)
    parser.add_argument("--new-vg", type=int, required=True)
    parser.add_argument("--game", action="append", type=parse_game, required=True,
                        metavar="NEW_ID:BASE_ID:NAME",
                        help="Game mapping; repeat for paired versions.")
    parser.add_argument("--full", action="store_true",
                        help="Also clone trainers, parties, bosses, and encounters (a playable copy).")
    parser.add_argument("--valid-game", default="hidden",
                        help="valid_game value for the new games rows (default: hidden).")
    parser.add_argument("--apply", action="store_true", help="Commit; default is a dry run.")
    args = parser.parse_args()

    sql = build_sql(args.base_vg, args.new_vg, args.game,
                    full=args.full, valid_game=args.valid_game, rollback=not args.apply)
    try:
        stdout, stderr = db.run_sql(sql)
    except db.PsqlError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1)
    print(stdout.strip())
    if stderr.strip():
        print(stderr.strip())
    print("Committed." if args.apply else "Dry run complete. Transaction rolled back.")


if __name__ == "__main__":
    main()
