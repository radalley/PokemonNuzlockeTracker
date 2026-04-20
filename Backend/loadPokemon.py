from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

import pokebase as pb

CACHE_DIR = Path("seed_cache")
POKEMON_CACHE = CACHE_DIR / "pokemon_stats"
POKEMON_CACHE.mkdir(parents=True, exist_ok=True)


def _to_jsonable(obj: Any) -> Any:
    """
    Convert Pokebase objects to plain JSONable primitives.
    We only keep the bits we need, so this is minimal.
    """
    if obj is None or isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, (list, tuple)):
        return [_to_jsonable(x) for x in obj]
    if isinstance(obj, dict):
        return {str(k): _to_jsonable(v) for k, v in obj.items()}

    # Pokebase resources have .name and .id_ often
    name = getattr(obj, "name", None)
    if name is not None:
        return str(name)
    id_ = getattr(obj, "id_", None)
    if id_ is not None:
        return int(id_)

    # Fallback: string representation (last resort)
    return str(obj)


def pokemon_get_min(identifier: str | int, *, use_cache: bool = True) -> Dict[str, Any]:
    """
    Fast path for seeding your Species + Gen3 typing tables.
    Avoids expensive fields (like location encounters).
    """
    # normalize cache key
    key = str(identifier).lower()
    cache_path = POKEMON_CACHE / f"{key}.json"

    if use_cache and cache_path.exists():
        return json.loads(cache_path.read_text(encoding="utf-8"))

    print(f"fetching pokemon({identifier})")
    identifier = 36
    p = pb.pokemon(identifier)

    # Extract only primitives you need
    species_id = int(p.id_)
    name = str(p.name).upper()

    if hasattr(p, 'past_abilities'):
        pass
    if hasattr(p, 'past_stats'):
        pass
    if hasattr(p, 'past_types'):
        pass

    # types can be 1 or 2; sort by slot to be safe
    type_entries = sorted(p.types, key=lambda t: int(t.slot))
    type1 = str(type_entries[0].type.name)
    type2: Optional[str] = str(type_entries[1].type.name) if len(type_entries) > 1 else None

    # gather abilities and patch past
    slot1 = None
    slot2 = None
    slot3 = None
    # abilities
    abilities = [{'ability': ab.ability, 'slot': ab.slot, 'is_hidden': ab.is_hidden} for ab in p.abilities]

    for i in abilities:
        if i['slot'] == 1:
            slot1 = i['ability'].name
        elif i['slot'] == 2:
            slot2 = i['ability'].name
        elif i['slot'] == 3:
            slot3 = i['ability'].name
        else:
            print('none')

    # extract stats and calculate BST
    stats = {stt.stat.name: stt.base_stat for stt in p.stats}

    past_abilities = [{'generation': pa.generation.id_,
                       'abilities': [{'ability': ab.ability, 'slot': ab.slot, 'is_hidden': ab.is_hidden} for ab in
                                     pa.abilities]} for pa in p.past_abilities] if hasattr(p,
                                                                                           'past_abilities') else None

    past_stats = [{'generation': ps.generation.id_, 'stats': {stt.stat.name: stt.base_stat for stt in ps.stats}} for ps
                  in p.past_stats] if hasattr(p, 'past_stats') else None

    past_types = [{'generation': pt.generation.id_, 'types': [{'slot': t.slot, 'type': t.type.name} for t in pt.types]}
                  for pt in p.past_types] if hasattr(p, 'past_types') else None

    data = {
        'species_id': species_id,
        'name': name,
        'type1': type1,
        'type2': type2,
        'ability1': slot1,
        'ability2': slot2,
        'ability3': slot3,
        'bst': sum(stats[i] for i in stats),
        'hp': stats['hp'],
        'atk': stats['attack'],
        'def': stats['defense'],
        'spa': stats['special-attack'],
        'spd': stats['special-defense'],
        'spe': stats['speed'],
        'past_abilities': past_abilities,
        'past_stats': past_stats,
        'past_types': past_types
    }

    cache_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return data

import sqlite3
from typing import Optional, Dict, Any

def upsert_species(conn: sqlite3.Connection, row: Dict[str, Any]) -> None:
    conn.execute(
        "INSERT OR IGNORE INTO species (species_id, name) VALUES (?, ?);",
        (row["species_id"], row["name"]),
    )
    conn.execute(
        """
        INSERT OR REPLACE INTO species_gen3 (species_id, name, type1, type2, ability1, ability2, ability3, bst, hp, atk, def, spa, spd, spe)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """,
        (row["species_id"], row['name'], row["type1"], row["type2"], row["ability1"], row["ability2"], row["ability3"],
         row['bst'], row["hp"], row["atk"], row["def"], row["spa"], row["spd"], row["spe"]),
    )
    # conn.commit()
    pass

def standardize_stats(base_stats, patch):
    if patch.get('special'):
        patch['special-attack'] = patch['special']
        patch['special-defense'] = patch['special']

    stats = {
        'hp' : patch['hp'] if patch.get('hp') else base_stats['hp'],
        'attack' : patch['attack'] if patch.get('attack') else base_stats['attack'],
        'defense': patch['defense'] if patch.get('defense') else base_stats['defense'],
        'special-attack': patch['special-attack'] if patch.get('special-attack') else base_stats['special-attack'],
        'special-defense': patch['special-defense'] if patch.get('special-defense') else base_stats['special-defense'],
        'speed': patch['speed'] if patch.get('speed') else base_stats['speed'],
    }
    stats['bst'] = sum(stats[i] for i in stats)

    return stats

def seed_stats(conn, data: Dict[str, Any]) -> Dict[str, Any]:
    #upload base stats
    species_id = data['id']
    name = data['name']
    type1 = data['types'][0]['type']['name'] if len(data['types']) >= 1 else None
    type2 = data['types'][1]['type']['name'] if len(data['types']) == 2 else None

    slot1, slot2, slot3 = None, None, None

    for i in data['abilities']:
        if i['slot'] == 1:
            slot1 = i['ability']['name']
        elif i['slot'] == 2:
            slot2 = i['ability']['name']
        elif i['slot'] == 3:
            slot3 = i['ability']['name']

    raw_stats = data['stats']
    stats = {}
    for stat in raw_stats:
        stats[stat['stat']['name']] = stat['base_stat']

    past_abilities = [{'generation': pa['generation'], 'abilities': pa['abilities']} for pa in data.get('past_abilities', [])]

    past_stats = [{'generation': change['generation']['name'],'stats': [{'base_stat': stat['base_stat'], 'stat': stat['stat']['name']   } for stat in change['stats']]} for change in data['past_stats']] if data.get('past_stats') else None
    past_types = [{'generation': change['generation']['name'], 'types': [{'slot': type['slot'], 'type': type['type']['name']} for type in change['types']]   } for change in data['past_types']] if data.get('past_types') else None

    row = {
        'species_id': species_id,
        'name': name.upper(),
        'type1': type1,
        'type2': type2,
        'ability1': slot1,
        'ability2': slot2,
        'ability3': slot3,
        'bst': sum(stats[i] for i in stats),
        'hp': stats['hp'],
        'attack': stats['attack'],
        'defense': stats['defense'],
        'special-attack': stats['special-attack'],
        'special-defense': stats['special-defense'],
        'speed': stats['speed'],
        'past_abilities': past_abilities,
        'past_stats': past_stats,
        'past_types': past_types
    }
    conn.execute(
        "INSERT OR IGNORE INTO species (species_id, name) VALUES (?, ?);",
        (row["species_id"], row["name"]),
    )
    conn.execute(
        """
        INSERT OR IGNORE INTO species_stats (species_id, bst, hp, atk, def, spa, spd, spe)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?);
        """,
        (row["species_id"], row['bst'], row["hp"], row["attack"], row["defense"], row["special-attack"], row["special-defense"], row["speed"]),
    )

    gen = {'i':1, 'ii': 2,'iii': 3,'iv': 4 ,'v': 5, 'vi': 6, 'vii': 7, 'viii': 8, 'ix': 9}

    if row.get('past_stats') and len(row.get('past_stats')) > 1:
        nrow = {}
        for x in row['past_stats']:
            generation = gen[x['generation'].split('-')[1]]
            for stat in x['stats']:
                nrow[stat['stat']] = stat['base_stat']
            stats = standardize_stats(row, nrow)
            conn.execute(
                """
                INSERT INTO species_stats (species_id, bst, hp, atk, def, spa, spd, spe, generation)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (row["species_id"], stats['bst'], stats["hp"], stats["attack"], stats["defense"], stats["special-attack"],
                 stats["special-defense"], stats["speed"], generation),
            )

    conn.execute(
        """
        INSERT OR IGNORE INTO species_types (species_id, type1, type2)
        VALUES ( ?, ?, ?);
        """,
        (row["species_id"], row["type1"], row["type2"]),
    )

    if row.get('past_types'):
        for x in row['past_types']:
            generation = gen[x['generation'].split('-')[1]]
            type1 = 'ignore'
            type2 = 'ignore'
            for type in x['types']:
                if type['slot'] == 1:
                    type1 = type['type']
                elif type['slot'] == 2:
                    type2 = type['type']
            conn.execute(
                """
                INSERT OR IGNORE INTO species_types (species_id, type1, type2, generation)
                VALUES ( ?, ?, ?, ?);
                """,
                (row["species_id"], type1 if type1 != 'ignore' else row["type1"], type2 if type2 != 'ignore' else row["type2"], generation),
            )

    conn.execute(
        """
        INSERT OR IGNORE INTO species_abilities (species_id, ability1, ability2, ability3)
        VALUES ( ?, ?, ?, ?);
        """,
        (row["species_id"], row["ability1"], row["ability2"], row["ability3"]),
    )
    if row.get('past_abilities'):
        for x in row.get('past_abilities'):
            ability1 = 'ignore'
            ability2 = 'ignore'
            ability3 = 'ignore'
            generation = gen[x['generation']['name'].split('-')[1]]
            for ability in x['abilities']:
                if ability['slot'] == 1:
                    ability1 = ability['ability']['name'] if ability['ability'] else ability['ability']
                elif ability['slot'] == 2:
                    ability2 = ability['ability']['name'] if ability['ability'] else ability['ability']
                elif ability['slot'] == 3:
                    ability3 =  ability['ability']['name'] if ability['ability'] else ability['ability']
            try:
                conn.execute(
                    """
                    INSERT OR IGNORE INTO species_abilities (species_id, ability1, ability2, ability3, generation)
                    VALUES ( ?, ?, ?, ?, ?);
                    """,
                    (row["species_id"], ability1 if ability1 != 'ignore' else row["ability1"], ability2 if ability2 != 'ignore' else row["ability2"], ability3 if ability3 != 'ignore' else row["ability3"], generation),
                )
            except:
                pass
    conn.commit()

def seed_species(conn: sqlite3.Connection) -> None:
    for dex_id in range(1, 1025):
        # (1, 152):
        data = pokemon_get_min(dex_id, use_cache=True)
        seed_stats(conn, data)
        # upsert_species(conn, data)

conn = sqlite3.connect('identifier.sqlite')
seed_species(conn)
print('done')
