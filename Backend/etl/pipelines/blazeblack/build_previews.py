"""Build the Blaze Black preview CSVs from the converted documentation.

    python -m etl.pipelines.blazeblack.build_previews

Reads LOCKLEY_ETL_SOURCE_DIR/blazeblack/*.txt, resolves everything against
the live database, and writes blazeblack_build7_preview/:

    trainer_pool_preview.csv / trainer_pokemon_preview.csv
    event_bosses_preview.csv
    encounter_pool_preview.csv
    validation_summary.json

Fails loud: any unresolved species, unmatched base fight, or unsplittable
ability lands in the summary's problems list, and unresolved species are
fatal. Location headers that do not resolve leave those trainers unplaced
for the curation queue rather than blocking the build.
"""
import json
import re
import sys
from collections import defaultdict

from ... import config, db, preview
from . import parse_bosses, parse_trainers, parse_wild, reference

PREVIEW_DIR_NAME = "blazeblack_build7_preview"
STARTER_TO_LINE = {"Grass": "grass", "Fire": "fire", "Water": "water"}


def source_dir():
    return config.source_dir() / "blazeblack"


def read_doc(name):
    path = source_dir() / name
    if not path.exists():
        raise SystemExit(
            f"Missing source document: {path}\n"
            "Convert the Drayano RTF docs to UTF-8 .txt and set LOCKLEY_ETL_SOURCE_DIR."
        )
    return path.read_text(encoding="utf-8")


def species_ids():
    return {name: int(sid) for sid, name in db.query_rows("select species_id, name from species")}


def mon_row(encounter_name, slot, mon):
    return {
        "encounter_name": encounter_name,
        "species_name": mon["species"],
        "lvl": mon.get("level") or "",
        "moves": ",".join(mon.get("moves") or []),
        "held_item": mon.get("item") or "",
        "iv": "",
        "version_group_id": reference.VERSION_GROUP_ID,
        "load_build": reference.LOAD_BUILD,
        "slot": slot,
        "ability": mon.get("ability") or "",
        "ability_clean": mon.get("ability_clean") or "",
        "nature": "",
    }


GAME_CONTEXTS = {"blaze black": 17, "volt white": 18}


def build_boss_rows(fights, problems):
    """Match doc fights to the vanilla skeleton; emit trainer, pokemon, and
    boss preview rows."""
    trainers, pokemon, bosses = [], [], []
    base_by_person = parse_bosses.base_fights_by_person()
    doc_counters = defaultdict(int)
    matched_base = set()
    special_keys = defaultdict(int)

    def items_of(mons):
        return ",".join(sorted({m["item"] for m in mons if m.get("item")}))

    def person_base_row(person):
        fights_for = base_by_person.get(person, [])
        return fights_for[0][0] if fights_for else None

    def emit_trainer(key, person, mons, base_row, details, is_event="", location_id=""):
        trainers.append({
            "encounter_name": key,
            "trainer_name": person,
            "trainer_class": (base_row or {}).get("trainer_class") or "TRAINER_CLASS_PKMN_TRAINER",
            "canonical_location_id": location_id,
            "is_rematch": "",
            "is_event": is_event,
            "trainer_items": items_of(mons),
            "trainer_pic": (base_row or {}).get("trainer_pic") or "",
            "trainer_double": "",
            "details": details,
            "version_group_id": reference.VERSION_GROUP_ID,
            "load_build": reference.LOAD_BUILD,
            "game_id": "",
        })
        for slot, mon in enumerate(mons, start=1):
            pokemon.append(mon_row(key, slot, mon))

    def emit_boss(base_row, key, person, battle_type):
        game = base_row["game_id"]
        bosses.append({
            "trainer_id": "",
            "trainer_index": "",
            "encounter_name": key,
            "trainer_name": person,
            "sort_order": base_row["sort_order"],
            "encounter_title": base_row["encounter_title"],
            "starter": base_row["starter"],
            "type_focus": base_row["type_focus"],
            "version_group_id": reference.VERSION_GROUP_ID,
            "event_type": base_row["event_type"],
            "game_id": reference.BASE_GAME_IDS.get(int(game), "") if game else "",
            "badge_id": base_row["badge_id"],
            "battle_type": battle_type,
            "is_level_cap": base_row["is_level_cap"],
        })

    def emit_special(team, fight, mons, battle_type):
        """A team with no skeleton slot: post-game replacement, Elite Four
        round two, or similar. Loads as an is_event trainer, placed when the
        context names a place."""
        person = team["person"]
        context = team["context"] or team["variant"] or fight["header"]
        location_id = ""
        location_text = (team["context"] or "").split(";")[0].strip()
        if location_text and location_text.lower() not in GAME_CONTEXTS:
            location = reference.resolve_location(location_text)
            if location:
                location_id = location[0]
            else:
                problems.append(f"unresolved special-team location for {person}: {location_text!r}")

        order = parse_bosses.variant_order(mons, person, problems)
        conditionals = [m for m in mons if "conditional" in m]
        if conditionals and order:
            for i, starter in enumerate(order):
                variant_mons = [
                    (m["conditional"][i] if "conditional" in m else m) for m in mons
                ]
                key = _special_key(person, f"{context}_{starter}")
                emit_trainer(key, person, variant_mons, person_base_row(person),
                             f"blazeblack_doc=important; special={context}; starter={starter}",
                             is_event="true", location_id=location_id)
        else:
            if conditionals:
                problems.append(f"conditional mons in special team {person}; kept first alternative")
            flat = [(m["conditional"][0] if "conditional" in m else m) for m in mons]
            key = _special_key(person, context)
            emit_trainer(key, person, flat, person_base_row(person),
                         f"blazeblack_doc=important; special={context}",
                         is_event="true", location_id=location_id)

    def _special_key(person, context):
        base = "TRAINER_BB_SPECIAL_" + re.sub(
            r"[^A-Za-z0-9]+", "_", f"{person}_{context}"
        ).strip("_").upper()[:52]
        special_keys[base] += 1
        return base if special_keys[base] == 1 else f"{base}_{special_keys[base]}"

    for fight in fights:
        fight_person_index = {}
        for team in fight["teams"]:
            person = team["person"]
            mons = parse_bosses.build_team_mons(team, problems)
            if not mons:
                problems.append(f"team with no mons: {person} ({fight['header']!r})")
                continue
            battle_type = team["battle_type"] or fight["battle_type"]
            context_key = (team["context"] or "").lower()
            game_filter = GAME_CONTEXTS.get(context_key)
            is_replacement = "replace" in context_key
            is_round_two = team["variant"] in ("second", "third")

            if is_replacement or is_round_two:
                emit_special(team, fight, mons, battle_type)
                continue

            base_fights = base_by_person.get(person, [])
            # Teams of the same person under one fight header share a slot
            # (the final N fight's Blaze Black / Volt White split).
            if person in fight_person_index:
                fight_index = fight_person_index[person]
            else:
                doc_counters[person] += 1
                fight_index = doc_counters[person] - 1
                fight_person_index[person] = fight_index

            if fight_index >= len(base_fights):
                emit_special(team, fight, mons, battle_type)
                continue

            base_rows = base_fights[fight_index]
            if game_filter is not None:
                base_rows = [r for r in base_rows if r["game_id"] and int(r["game_id"]) == game_filter]
                if not base_rows:
                    problems.append(f"no game-split base row for {person} ({team['context']})")
                    continue
            for row in base_rows:
                matched_base.add(row["event_id"])

            has_conditional = any("conditional" in m for m in mons)
            starter_rows = {r["starter"]: r for r in base_rows if r["starter"]}
            order = parse_bosses.variant_order(mons, person, problems) if has_conditional else None

            if has_conditional and starter_rows and order:
                for i, starter in enumerate(order):
                    base_row = starter_rows.get(starter)
                    if base_row is None:
                        problems.append(f"no base row for starter {starter} in {person} fight {fight_index + 1}")
                        continue
                    variant_mons = [
                        (m["conditional"][i] if "conditional" in m else m) for m in mons
                    ]
                    key = re.sub(r"[^A-Za-z0-9_]+", "_",
                                 f"TRAINER_BB_{person}_{fight_index + 1}_{starter.upper()}")
                    emit_trainer(key, person, variant_mons, base_row,
                                 f"blazeblack_doc=important; fight={fight['header']}; starter={starter}")
                    emit_boss(base_row, key, person, battle_type)
            else:
                if has_conditional:
                    problems.append(
                        f"conditional team without starter mapping: {person} fight {fight_index + 1}; kept first alternative")
                flat = [(m["conditional"][0] if "conditional" in m else m) for m in mons]
                key = re.sub(r"[^A-Za-z0-9_]+", "_", f"TRAINER_BB_{person}_{fight_index + 1}")
                if game_filter is not None:
                    key += f"_G{game_filter}"
                emit_trainer(key, person, flat, base_rows[0],
                             f"blazeblack_doc=important; fight={fight['header']}")
                for base_row in base_rows:
                    emit_boss(base_row, key, person, battle_type)

    unmatched = [
        f"{row['encounter_title']} (sort {row['sort_order']}, {row['trainer_name']})"
        for row in reference.base_bosses() if row["event_id"] not in matched_base
    ]
    for entry in unmatched:
        problems.append(f"base fight with no Blaze Black team: {entry}")

    return trainers, pokemon, bosses, len(matched_base)


def main():
    problems = []

    roster_trainers, roster_pokemon, roster_problems = parse_trainers.parse(read_doc("Trainer Rosters.txt"))
    problems += roster_problems

    fights, fight_problems = parse_bosses.parse_document(read_doc("Important Trainer Rosters.txt"))
    problems += fight_problems
    boss_trainers, boss_pokemon, boss_rows, matched_base = build_boss_rows(fights, problems)

    wild_rows, wild_problems = parse_wild.parse(read_doc("Wild Pokemon.txt"))
    problems += wild_problems

    ids = species_ids()
    for row in wild_rows:
        row["species_id"] = ids[row["species_id"]]

    trainers = roster_trainers + boss_trainers
    pokemon = roster_pokemon + boss_pokemon
    names = [t["encounter_name"] for t in trainers]
    duplicate_names = sorted({n for n in names if names.count(n) > 1})
    for name in duplicate_names:
        problems.append(f"duplicate encounter_name: {name}")

    out = config.preview_dir(PREVIEW_DIR_NAME)
    preview.write_csv(out / "trainer_pool_preview.csv", trainers, list(trainers[0]))
    preview.write_csv(out / "trainer_pokemon_preview.csv", pokemon, list(pokemon[0]))
    preview.write_csv(out / "event_bosses_preview.csv", boss_rows, list(boss_rows[0]))
    preview.write_csv(out / "encounter_pool_preview.csv", wild_rows, list(wild_rows[0]))

    placed = sum(1 for t in trainers if t["canonical_location_id"])
    summary = {
        "version_group_id": reference.VERSION_GROUP_ID,
        "load_build": reference.LOAD_BUILD,
        "trainer_rows": len(trainers),
        "roster_trainers": len(roster_trainers),
        "boss_trainers": len(boss_trainers),
        "trainer_pokemon_rows": len(pokemon),
        "event_boss_rows": len(boss_rows),
        "base_boss_rows_matched": matched_base,
        "base_boss_rows_total": len(reference.base_bosses()),
        "located_rows": placed,
        "encounter_rows": len(wild_rows),
        "problems": problems,
    }
    preview.write_summary(out / "validation_summary.json", summary)

    print(f"trainers={len(trainers)} (rosters {len(roster_trainers)}, bosses {len(boss_trainers)}), "
          f"pokemon={len(pokemon)}, bosses={len(boss_rows)}, encounters={len(wild_rows)}")
    print(f"base skeleton matched {matched_base}/{len(reference.base_bosses())}; "
          f"placed {placed}/{len(trainers)}")
    if problems:
        print(f"\n{len(problems)} problems:")
        for problem in problems[:40]:
            print(f"  - {problem}")
        if len(problems) > 40:
            print(f"  ... and {len(problems) - 40} more")
    fatal = [p for p in problems if "unresolved" in p and "species" in p]
    if fatal or duplicate_names:
        print("\nFATAL: unresolved species or duplicate keys; fix before loading.", file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
