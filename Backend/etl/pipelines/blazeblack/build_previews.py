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
from . import (parse_bosses, parse_learnsets, parse_species_changes,
               parse_trainers, parse_wild, reference)

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


def _pick_gen5_row(rows):
    """Mirror of the generation patch join's pick for generation 5: the
    lowest generation >= 5, else the default (generation 0/null) row."""
    versioned = sorted(
        (r for r in rows if (r.get("generation") or 0) and int(r["generation"]) >= 5),
        key=lambda r: int(r["generation"]),
    )
    if versioned:
        return versioned[0]
    defaults = [r for r in rows if not (r.get("generation") or 0)]
    return defaults[0] if defaults else None


def build_species_overrides(problems):
    """Materialize the species/learnset override previews from the two docs.

    Learnset deltas apply against the live vanilla BW (vg 11) learnsets;
    stat and type changes apply against the row the app would pick at
    generation 5. Everything lands keyed at version group 1001.
    """
    vg = reference.VERSION_GROUP_ID
    changes, change_problems = parse_species_changes.parse(read_doc("Pokemon Changes.txt"))
    problems += change_problems
    move_changes, learnset_deltas, learnset_problems = parse_learnsets.parse(
        read_doc("Level Up Move Changes.txt"))
    problems += learnset_problems

    # --- reference data -------------------------------------------------
    move_rows = db.query_rows(
        "select move_id, move_name, coalesce(type,''), coalesce(damage_class,''), "
        "coalesce(power::text,''), coalesce(accuracy::text,'') "
        "from moves where version_group_id is null or version_group_id = 0"
    )
    move_by_slug, move_default = {}, {}
    for move_id, name, mtype, dclass, power, accuracy in move_rows:
        slug = re.sub(r"[^a-z0-9]+", "", name.lower())
        move_by_slug.setdefault(slug, int(move_id))
        move_default[int(move_id)] = {
            "move_name": name, "type": mtype, "damage_class": dclass,
            "power": power, "accuracy": accuracy,
        }
    for old, new in parse_bosses.MOVE_RENAMES.items():
        if new in move_by_slug:
            move_by_slug.setdefault(old, move_by_slug[new])

    type_canon = {}
    for (value,) in db.query_rows(
        "select distinct type1 from species_types where type1 is not null and type1 <> ''"
    ):
        type_canon.setdefault(value.strip().lower(), value)

    vanilla_learnsets = defaultdict(list)
    for species_id, move_id, level in db.query_rows(
        "select species_id, move_id, learn_level from movesets "
        "where learn_method = 'level-up' and version_group_id = 11"
    ):
        vanilla_learnsets[int(species_id)].append((int(move_id), int(level)))

    stats_rows, types_rows = defaultdict(list), defaultdict(list)
    for row in db.query_rows(
        "select species_id, coalesce(generation, 0), bst, hp, atk, def, spa, spd, spe "
        "from species_stats where version_group_id is null"
    ):
        stats_rows[int(row[0])].append({
            "generation": int(row[1]), "bst": row[2], "hp": row[3], "atk": row[4],
            "def": row[5], "spa": row[6], "spd": row[7], "spe": row[8],
        })
    for row in db.query_rows(
        "select species_id, coalesce(generation, 0), coalesce(type1,''), coalesce(type2,'') "
        "from species_types where version_group_id is null"
    ):
        types_rows[int(row[0])].append({
            "generation": int(row[1]), "type1": row[2], "type2": row[3],
        })

    # Custom moves Drayano added to the ROM; they exist nowhere in our move
    # data, so their learnset entries are skipped with a note.
    known_custom_moves = {"woodhorn"}

    def move_id_for(name, context):
        slug = re.sub(r"[^a-z0-9]+", "", name.lower())
        if slug in known_custom_moves:
            problems.append(f"note: custom hack move {name!r} skipped ({context})")
            return None
        move_id = move_by_slug.get(slug)
        if move_id is None:
            problems.append(f"unresolved override move {name!r} ({context})")
        return move_id

    # --- abilities (all species, Regular mode) --------------------------
    ability_rows = [{
        "species_id": sid,
        "generation": "",
        "ability1": c["ability1"] or "",
        "ability2": c["ability2"] or "",
        "ability3": "",
        "version_group_id": vg,
    } for sid, c in sorted(changes.items()) if c["ability1"]]

    # --- stats (changed species; complete rows with recomputed bst) -----
    stat_override_rows = []
    for sid, c in sorted(changes.items()):
        if not c["stats"]:
            continue
        base = _pick_gen5_row(stats_rows.get(sid, []))
        if base is None:
            problems.append(f"stat change for species {sid} with no vanilla stats row")
            continue
        merged = {k: int(base[k] or 0) for k in ("hp", "atk", "def", "spa", "spd", "spe")}
        merged.update(c["stats"])
        stat_override_rows.append({
            "species_id": sid, "generation": "",
            "bst": sum(merged.values()), **merged, "version_group_id": vg,
        })

    # --- types (the retyped species) ------------------------------------
    type_override_rows = []
    for sid, c in sorted(changes.items()):
        if not c["types"]:
            continue
        type1, type2 = c["types"]
        type_override_rows.append({
            "species_id": sid, "generation": "",
            "type1": type_canon.get(type1.lower(), type1),
            "type2": type_canon.get(type2.lower(), type2) if type2 else "",
            "version_group_id": vg,
        })

    # --- learnsets (vanilla copy + deltas, changed species only) --------
    learnset_rows = []
    for sid, delta_list in sorted(learnset_deltas.items()):
        entries = set(vanilla_learnsets.get(sid, []))
        doc_added = set()
        if not entries:
            problems.append(f"learnset deltas for species {sid} with no vanilla vg-11 learnset")
        for op, level, move_name in delta_list:
            if op == "reset":
                entries = set()
                doc_added = set()
                continue
            move_id = move_id_for(move_name, f"species {sid}")
            if move_id is None:
                continue
            if op == "auto":
                # '+/=': shift when the member already knows the move.
                op = "=" if any(m == move_id for m, _ in entries) else "+"
            if op == "-":
                # '-' replaces "the move usually learned at that level":
                # it removes VANILLA entries at the level, never moves the
                # doc itself added earlier in the block (Natu's Safeguard).
                entries = {(m, l) for m, l in entries if l != level or (m, l) in doc_added}
            elif op == "=":
                entries = {(m, l) for m, l in entries if m != move_id}
            entries.add((move_id, level))
            doc_added.add((move_id, level))
        for move_id, level in sorted(entries, key=lambda e: (e[1], e[0])):
            learnset_rows.append({
                "species_id": sid, "move_id": move_id, "learn_method": "level-up",
                "learn_level": level, "version_group_id": vg,
            })

    # --- move rebalances -------------------------------------------------
    move_override_rows = []
    seen_moves = set()
    for change in move_changes:
        move_id = move_id_for(change["name"], "move rebalance")
        if move_id is None or move_id in seen_moves:
            continue
        seen_moves.add(move_id)
        base = dict(move_default[move_id])
        if change["power"] is not None:
            base["power"] = change["power"]
        if change["accuracy"] is not None:
            base["accuracy"] = change["accuracy"]
        if change["type"] is not None:
            base["type"] = type_canon.get(change["type"].lower(), change["type"].lower())
        move_override_rows.append({"move_id": move_id, **base, "version_group_id": vg})

    return {
        "species_abilities": ability_rows,
        "species_stats": stat_override_rows,
        "species_types": type_override_rows,
        "movesets": learnset_rows,
        "moves": move_override_rows,
    }


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

    overrides = build_species_overrides(problems)

    out = config.preview_dir(PREVIEW_DIR_NAME)
    preview.write_csv(out / "trainer_pool_preview.csv", trainers, list(trainers[0]))
    preview.write_csv(out / "trainer_pokemon_preview.csv", pokemon, list(pokemon[0]))
    preview.write_csv(out / "event_bosses_preview.csv", boss_rows, list(boss_rows[0]))
    preview.write_csv(out / "encounter_pool_preview.csv", wild_rows, list(wild_rows[0]))
    for name, rows in overrides.items():
        if rows:
            preview.write_csv(out / f"{name}_override_preview.csv", rows, list(rows[0]))

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
        "override_rows": {name: len(rows) for name, rows in overrides.items()},
        "problems": problems,
    }
    preview.write_summary(out / "validation_summary.json", summary)

    print(f"trainers={len(trainers)} (rosters {len(roster_trainers)}, bosses {len(boss_trainers)}), "
          f"pokemon={len(pokemon)}, bosses={len(boss_rows)}, encounters={len(wild_rows)}")
    print("overrides: " + ", ".join(f"{name}={len(rows)}" for name, rows in overrides.items()))
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
