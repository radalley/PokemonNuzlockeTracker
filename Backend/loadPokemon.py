from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

import pokebase as pb

CACHE_DIR = Path("seed_cache")
POKEMON_CACHE = CACHE_DIR / "pokemon_min"
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
    p = pb.pokemon(identifier)

    # Extract only primitives you need
    species_id = int(p.id_)
    name = str(p.name).upper()

    # types can be 1 or 2; sort by slot to be safe
    type_entries = sorted(p.types, key=lambda t: int(t.slot))
    type1 = str(type_entries[0].type.name)
    type2: Optional[str] = str(type_entries[1].type.name) if len(type_entries) > 1 else None

    #gather abilities and patch past
    slot1 = None
    slot2 = None
    slot3 = None
    # abilities
    abilities = [{'ability': ab.ability, 'slot': ab.slot, 'is_hidden': ab.is_hidden} for ab in p.abilities]
    #past abilities
    past_abilities = [{'generation': pa.generation, 'abilities': [     {'ability': ab.ability, 'slot': ab.slot, 'is_hidden': ab.is_hidden} for ab in pa.abilities ]} for pa in p.past_abilities] if hasattr(p,'past_abilities') else None

    for i in abilities:
        if i['slot'] == 1:
            slot1 = i['ability'].name
        elif i['slot'] == 2:
            slot2 = i['ability'].name
        elif i['slot'] == 3:
            slot3 = i['ability'].name
        else:
            print('none')


    #extract stats and calculate BST
    stats = {stt.stat.name: stt.base_stat for stt in p.stats}

    data = {
        'species_id': species_id,
        'name': name,
        'type1': type1,
        'type2': type2,
        'ability1' : slot1,
        'ability2': slot2,
        'ability3': slot3,
        'bst': sum(stats[i] for i in stats),
        'hp' : stats['hp'],
        'atk' : stats['attack'],
        'def' : stats['defense'],
        'spa' : stats['special-attack'],
        'spd' : stats['special-defense'],
        'spe' : stats['speed'],
    }

    cache_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return data

kanto_mon = ['bulbasaur', 'ivysaur', 'venusaur', 'charmander', 'charmeleon', 'charizard', 'squirtle', 'wartortle', 'blastoise', 'caterpie', 'metapod', 'butterfree', 'weedle', 'kakuna', 'beedrill',
             'pidgey', 'pidgeotto', 'pidgeot', 'rattata', 'raticate', 'spearow', 'fearow', 'ekans', 'arbok', 'pikachu', 'raichu', 'sandshrew', 'sandslash', 'nidoran-f', 'nidorina', 'nidoqueen',
             'nidoran-m', 'nidorino', 'nidoking', 'clefairy', 'clefable', 'vulpix', 'ninetales', 'jigglypuff', 'wigglytuff', 'zubat', 'golbat', 'oddish', 'gloom', 'vileplume', 'paras', 'parasect',
             'venonat', 'venomoth', 'diglett', 'dugtrio', 'meowth', 'persian', 'psyduck', 'golduck', 'mankey', 'primeape', 'growlithe', 'arcanine', 'poliwag', 'poliwhirl', 'poliwrath', 'abra',
             'kadabra', 'alakazam', 'machop', 'machoke', 'machamp', 'bellsprout', 'weepinbell', 'victreebel', 'tentacool', 'tentacruel', 'geodude', 'graveler', 'golem', 'ponyta', 'rapidash',
             'slowpoke', 'slowbro', 'magnemite', 'magneton', 'farfetchd', 'doduo', 'dodrio', 'seel', 'dewgong', 'grimer', 'muk', 'shellder', 'cloyster', 'gastly', 'haunter', 'gengar', 'onix',
             'drowzee', 'hypno', 'krabby', 'kingler', 'voltorb', 'electrode', 'exeggcute', 'exeggutor', 'cubone', 'marowak', 'hitmonlee', 'hitmonchan', 'lickitung', 'koffing', 'weezing', 'rhyhorn',
             'rhydon', 'chansey', 'tangela', 'kangaskhan', 'horsea', 'seadra', 'goldeen', 'seaking', 'staryu', 'starmie', 'mr-mime', 'scyther', 'jynx', 'electabuzz', 'magmar', 'pinsir', 'tauros',
             'magikarp', 'gyarados', 'lapras', 'ditto', 'eevee', 'vaporeon', 'jolteon', 'flareon', 'porygon', 'omanyte', 'omastar', 'kabuto', 'kabutops', 'aerodactyl', 'snorlax', 'articuno',
             'zapdos', 'moltres', 'dratini', 'dragonair', 'dragonite', 'mewtwo', 'mew']

gen = 3
print('starting')
butterfree = pokemon_get_min('butterfree')


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
        (row["species_id"], row['name'], row["type1"], row["type2"], row["ability1"], row["ability2"], row["ability3"], row['bst'], row["hp"], row["atk"], row["def"], row["spa"], row["spd"], row["spe"]),
    )
    conn.commit()

def seed_gen1_species(conn: sqlite3.Connection) -> None:
    for dex_id in range(1,152):
        #(1, 152):
        data = pokemon_get_min(dex_id, use_cache=True)  # will fetch once then cache forever
        upsert_species(conn, data)

conn = sqlite3.connect('identifier.sqlite')
seed_gen1_species(conn)
print('done')
