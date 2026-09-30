import pokebase as pb
import json
from pathlib import Path
from typing import Any, Dict, Optional

CACHE_DIR = Path("seed_cache")
POKEMON_CACHE = CACHE_DIR / "pokemon_evos"
POKEMON_CACHE.mkdir(parents=True, exist_ok=True)

def species_evolutions(item):
    payload = {'Species': item.species.name, 'Species_id': item.species.id_}
    if item.evolution_details:
        method = item.evolution_details[0].trigger.name
        payload['Evolution_details'] = {'Method': method,}
        # match method:
        #     case 'level-up':
        #         payload['Evolution_details']['Level'] = item.evolution_details[0].min_level
        #     case 'item':
    if item.evolves_to:
        payload['Evolves_to'] = [species_evolutions(evo) for evo in item.evolves_to]
    return payload


def pokemon_get_evos(identifier: str | int, *, use_cache: bool = True) -> Dict[str, Any]:
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
    evo = pb.evolution_chain(identifier)

    data = species_evolutions(evo.chain)
    pass
    # for loc in p.location_area_encounters:
    #     version_details = []
    #     area_name = loc.location_area.name
    #     area_id = loc.location_area.id_
    #     for ver in loc.version_details:
    #         version_name = ver.version.name
    #         version_id = ver.version.id_
    #         version_details.append({
    #             'version_name': version_name.capitalize(),
    #             'version_id': version_id})
    #     data.append({
    #         'area_name': area_name,
    #         'area_id': area_id,
    #         'version_details': version_details,
    #     })

    cache_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return data

# for i in range(1,549):
errand = []
chains = []
for i in range(1, 549):
    print(f'pulling for chain : {i}')
    try:
        chains.append({'chain_id': i, 'chain': pokemon_get_evos(i)})
    except Exception as e:
        errand.append(i)
        print(f'error on evo chain : {i}')
pass

def post_evolution(conn, species_id, evolves_to):
    for evo in evolves_to:
        method = evo['Evolution_details']['Method'] if evo.get('Evolution_details') else None
        conn.execute('INSERT or REPLACE INTO evolutions (from_species_id, to_species_id, method) VALUES (?, ?, ?)', (species_id, evo['Species_id'], method))
        if evo.get('Evolves_to'):
            post_evolution(conn, evo['Species_id'], evo['Evolves_to'])


import sqlite3
conn = sqlite3.connect('identifier.sqlite')
conn.row_factory = sqlite3.Row

for chain in chains:
    item = chain['chain']
    if item.get('Evolves_to'):
        print(f'posting evolution from {chain}')
        post_evolution(conn, item['Species_id'], item['Evolves_to'])
conn.commit()
print('done')