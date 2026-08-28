import pokebase as pb
import json
from pathlib import Path
from typing import Any, Dict, Optional

CACHE_DIR = Path("seed_cache")
STAT_CACHE = CACHE_DIR / "pokemon_stats"
STAT_MOVE_CACHE = CACHE_DIR / "pokemon_stats"
POKEMON_CACHE = CACHE_DIR / "pokemon_moves"
POKEMON_MOVE_CACHE = CACHE_DIR / "pokemon_move"
POKEMON_CACHE.mkdir(parents=True, exist_ok=True)
POKEMON_MOVE_CACHE.mkdir(parents=True, exist_ok=True)

def build_movesets(moves):
    moveset = []
    for move in moves:
        payload = {'move_id': move.move.id_, 'version_group': []}
        for group in move.version_group_details:
            payload['version_group'].append({'level_learned': group.level_learned_at, 'learn_method': group.move_learn_method.name ,'version_group': group.version_group.id_,})
        moveset.append(payload)

    return moveset

def build_movesets2(moves):
    moveset = []
    for move in moves:
        payload = {'move_id': move['move']['url'].split('/')[::-1][1], 'version_group': []}
        for group in move['version_group_details']:
            payload['version_group'].append({'level_learned': group['level_learned_at'], 'learn_method': group['move_learn_method']['name'] ,'version_group': group['version_group']['url'].split('/')[::-1][1],})
        moveset.append(payload)

    return moveset

def post_moveset(conn, species_id, payload):
    print(f'seeding species {species_id}')
    for move in payload:
        move_id = move['move_id']
        for version_group in move['version_group']:
            conn.execute('insert or ignore into movesets (species_id, move_id, version_group_id, learn_method, learn_level) VALUES (?,?,?,?,?)',(species_id, move['move_id'], version_group['version_group'], version_group['learn_method'], version_group['level_learned'],))
    conn.commit()

def pokemon_get_moves(identifier: str | int, *, use_cache: bool = True) -> Dict[str, Any]:
    """
    Fast path for seeding your Species + Gen3 typing tables.
    Avoids expensive fields (like location encounters).
    """
    # normalize cache key
    key = str(identifier).lower()
    cache_path = POKEMON_CACHE / f"{key}.json"

    if use_cache and cache_path.exists():
        return json.loads(cache_path.read_text(encoding="utf-8"))

    stat_path = STAT_CACHE / f"{key}.json"
    source = ''
    if use_cache and stat_path.exists():
        source = 'cache'
        mon = json.loads(stat_path.read_text(encoding="utf-8"))
    else:
        print(f"fetching pokemon({identifier})")
        mon = pb.pokemon(identifier)
    if source == 'cache':
        data = build_movesets2(mon['moves'])
    else:
        data = build_movesets(mon.moves)

    cache_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return data

def get_move(move_id: str, *, use_cache: bool = True) -> Dict[str, Any]:
    print(f"fetching move({move_id})")

    key = str(move_id).lower()
    cache_path = POKEMON_MOVE_CACHE / f"{key}.json"

    if use_cache and cache_path.exists():
        vessel = json.loads(cache_path.read_text(encoding="utf-8"))
        if vessel.get('move_name'):
            return vessel

    move = pb.move(move_id)
    payload = {
        'move_name' : move.name,
        'move_id': move_id,
        'damage class':move.damage_class.name,
        'accuracy': move.accuracy,
        'power': move.power,
        'type': move.type.name,
        'past_value': [{'past_accuracy': x.accuracy, 'past_power': x.power, 'past_type': x.type.name if x.type else None, 'past_version_group': x.version_group.id_} for x in move.past_values]
    }

    cache_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload

import time
import sqlite3
conn = sqlite3.connect('identifier.sqlite')
conn.row_factory = sqlite3.Row

def post_move(conn, payload):
    #adjust name
    payload['move_name'] = ' '.join(word.capitalize() for word in payload['move_name'].replace('-',' ').split())
    #upload initial move
    conn.execute('insert or ignore into moves (move_id, move_name, type, damage_class, power, accuracy, version_group_id) values (?,?,?,?,?,?,?)',(payload['move_id'], payload['move_name'], payload['type'], payload['damage class'], payload['power'], payload['accuracy'], 'BASE'))
    #upload for each version
    if payload.get('past_value'):
        for past in payload['past_value']:
            pass
            conn.execute('insert or ignore into moves (move_id, move_name, type, damage_class, power, accuracy, version_group_id) values (?,?,?,?,?,?,?)',(
                payload['move_id'],
                payload['move_name'],
                past['past_type'] if past.get('past_type') else payload['type'],
                payload['damage class'],
                past['past_power'] if past.get('past_power') else payload['power'],
                past['past_accuracy'] if past.get('past_accuracy') else payload['accuracy'],
                past['past_version_group'],
            ))
    conn.commit()

start_total = time.perf_counter()
moves = []
errand = []

def post(dex_id):
    try:
        print(f"posting dex({dex_id})")
        # move = get_move(dex_id)
        # post_move(conn, move)
        data = pokemon_get_moves(dex_id)
        post_moveset(conn, dex_id, data)
    except:
        errand.append(i)
# for i in range(1,1025):
#     post(i)
# for i in range(10001, 10326):
#     post(i)
move = []
for i in range(1,919):
    post_move(conn,get_move(i))

end_total = time.perf_counter()
total_elapsed = end_total - start_total
print('time_elapsed', total_elapsed)

print('done')