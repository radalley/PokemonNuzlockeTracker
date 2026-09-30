"""Split catalogue, durable item curation, and battle-time party snapshots.

Item keys use badge identity (shared across starter variants) or the stable
trainer encounter key, never a display label or an ETL-generated event id.
"""
import json


def split_kind(row):
    kind = str(row.get('event_type') or '').strip().lower()
    title = str(row.get('encounter_title') or '').strip().lower()
    if row.get('badge_id') is not None or kind == 'gym leader':
        return 'gym'
    if kind == 'elite four' or title.startswith('elite four'):
        return 'elite_four'
    if kind == 'champion' or title == 'champion':
        return 'champion'
    return None


def split_key(row):
    if row.get('badge_id') is not None:
        return f"badge:{row['badge_id']}"
    return f"boss:{row['encounter_name']}" if row.get('encounter_name') else None


def catalogue(conn, game_id, starter=None):
    game = conn.execute('select game_id, version_group_id from games where game_id = %s', (game_id,)).fetchone()
    if not game:
        raise ValueError('Game not found')
    rows = conn.execute(
        'select eb.*, tp.encounter_name, tp.trainer_name, tp.trainer_class, tp.trainer_pic '
        'from event_bosses eb join trainer_pool tp on tp.trainer_id = eb.trainer_id '
        'where eb.version_group_id = %s and (eb.game_id is null or eb.game_id = %s) '
        'and (%s is null or eb.starter is null or eb.starter = \'\' or eb.starter = %s) '
        'order by nullif(eb.sort_order, \'\')::numeric nulls last, eb.event_id',
        (game['version_group_id'], game_id, starter, starter),
    ).fetchall()
    result, seen = [], set()
    for raw in rows:
        row = dict(raw)
        kind, key = split_kind(row), split_key(row)
        if not kind or not key or key in seen:
            continue
        seen.add(key)
        result.append({**row, 'split_key': key, 'kind': kind})
    return result


def get_items(conn, game_id):
    items = [dict(row) for row in conn.execute(
        'select * from curated_split_items where game_id = %s order by item_record_id', (game_id,)
    ).fetchall()]
    if not items:
        return items
    has_sources = conn.execute(
        "select to_regclass('public.curated_split_item_sources') is not null as ready"
    ).fetchone()['ready']
    if has_sources:
        rows = conn.execute(
            'select src.*, s.name as species_name from curated_split_item_sources src '
            'left join species s on s.species_id = src.source_species_id '
            'join curated_split_items item on item.item_record_id = src.item_record_id '
            'where item.game_id = %s order by src.sort_order, src.item_source_id', (game_id,)
        ).fetchall()
        by_item = {}
        for row in rows:
            source = dict(row)
            by_item.setdefault(source.pop('item_record_id'), []).append(source)
        for item in items:
            item['sources'] = by_item.get(item['item_record_id'], [])
    else:
        for item in items:
            item['sources'] = []
    return items


def save_item(conn, game_id, key, item_name, method, record_id=None):
    if not isinstance(item_name, str) or not 1 <= len(item_name.strip()) <= 100:
        raise ValueError('Item must be between 1 and 100 characters')
    if not isinstance(method, str) or not 1 <= len(method.strip()) <= 500:
        raise ValueError('Method must be between 1 and 500 characters')
    valid = {s['split_key'] for s in catalogue(conn, game_id) if s['kind'] == 'gym'}
    if key not in valid:
        raise ValueError('Choose a gym split in this game; League battles have no item tables')
    if record_id is None:
        row = conn.execute(
            'insert into curated_split_items(game_id, split_key, item_name, method) '
            'values (%s, %s, %s, %s) on conflict (game_id, split_key, item_name, method) '
            'do update set updated_at = curated_split_items.updated_at returning *',
            (game_id, key, item_name.strip(), method.strip()),
        ).fetchone()
    else:
        row = conn.execute(
            'update curated_split_items set split_key = %s, item_name = %s, method = %s, '
            'updated_at = current_timestamp where item_record_id = %s and game_id = %s returning *',
            (key, item_name.strip(), method.strip(), record_id, game_id),
        ).fetchone()
        if not row:
            raise ValueError('Item record not found')
    if conn.execute("select to_regclass('public.curated_split_item_sources') is not null as ready").fetchone()['ready']:
        structured = conn.execute(
            "select 1 from curated_split_item_sources where item_record_id = %s and method_kind <> 'manual' limit 1",
            (row['item_record_id'],),
        ).fetchone()
        if not structured:
            conn.execute(
                'insert into curated_split_item_sources(item_record_id, source_key, method_kind, source_detail) '
                "values (%s, 'manual:editor', 'manual', %s) on conflict (item_record_id, source_key) "
                'do update set source_detail = excluded.source_detail',
                (row['item_record_id'], method.strip()),
            )
    conn.commit()
    saved = dict(row)
    saved['sources'] = []
    return saved


def get_records(conn, attempt_id):
    records = [dict(row) for row in conn.execute(
        'select * from attempt_battle_records where attempt_id = %s order by recorded_at, battle_record_id',
        (attempt_id,),
    ).fetchall()]
    available = {row['pokemon_id'] for row in conn.execute(
        'select pokemon_id from pokebank where attempt_id = %s', (attempt_id,)
    ).fetchall()}
    for record in records:
        for member in record['party']:
            member['available'] = member['pokemon_id'] in available
    return records


def prepare_party(conn, attempt_id, participant_ids=None, fainted_ids=None):
    """Resolve identity/appearance on the server; never trust client sprites.

    The modal's roster includes participants removed from the current party
    during the battle. Explicit fainting is per battle, never inferred from
    today's Dead status. Call under the attempt's FOR UPDATE lock.
    """
    if participant_ids is None:
        participant_ids = [r['pokemon_id'] for r in conn.execute(
            'select pokemon_id from party where attempt_id = %s order by party_slot', (attempt_id,)
        ).fetchall()]
    fainted_ids = [] if fainted_ids is None else fainted_ids
    for ids in (participant_ids, fainted_ids):
        if not isinstance(ids, list) or len(ids) > 6 or any(type(x) is not int or x <= 0 for x in ids):
            raise ValueError('Battle participants must be a list of up to six Pokemon IDs')
        if len(set(ids)) != len(ids):
            raise ValueError('Duplicate battle participant')
    fainted = set(fainted_ids)
    if not fainted.issubset(set(participant_ids)):
        raise ValueError('Fallen Pokemon must be in this battle party')
    rows = conn.execute(
        'select pb.pokemon_id, pb.species_id, pb.nickname, pb.gender, pb.shiny, pb.status, '
        's.name as species_name from pokebank pb left join species s on s.species_id = pb.species_id '
        'where pb.attempt_id = %s and pb.pokemon_id = any(%s)', (attempt_id, participant_ids),
    ).fetchall() if participant_ids else []
    by_id = {r['pokemon_id']: dict(r) for r in rows}
    if len(by_id) != len(participant_ids) or any(r['status'] not in ('Captured', 'Dead') for r in rows):
        raise ValueError('Battle Pokemon must belong to this attempt')
    return [{k: v for k, v in {**by_id[pid], 'slot': i + 1, 'died_in_battle': pid in fainted}.items()
             if k != 'status'} for i, pid in enumerate(participant_ids)]


def record_victory(conn, attempt_id, trainer_id, event_id, party):
    boss = conn.execute(
        'select eb.*, tp.encounter_name from event_bosses eb '
        'join trainer_pool tp on tp.trainer_id = eb.trainer_id where eb.event_id = %s', (event_id,)
    ).fetchone() if event_id is not None else None
    key = split_key(dict(boss)) if boss and split_kind(dict(boss)) else None
    conn.execute(
        'insert into attempt_battle_records(attempt_id, trainer_id, boss_event_id, split_key, party) '
        'values (%s, %s, %s, %s, %s::jsonb) on conflict (attempt_id, trainer_id) do nothing',
        (attempt_id, trainer_id, event_id, key, json.dumps(party)),
    )
    fainted = [m['pokemon_id'] for m in party if m['died_in_battle']]
    if fainted:
        conn.execute("update pokebank set status = 'Dead' where attempt_id = %s and pokemon_id = any(%s)", (attempt_id, fainted))
        conn.execute('delete from party where attempt_id = %s and pokemon_id = any(%s)', (attempt_id, fainted))
        # The fallen leave a gap; the caller closes it (importing backend
        # here would be a cycle, since backend imports this module).
