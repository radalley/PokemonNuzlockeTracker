import psycopg2
import psycopg2.extras
import time
import json
from werkzeug.security import check_password_hash, generate_password_hash


class _PGCursor:
    """Wraps a psycopg2 RealDictCursor to mimic sqlite3's cursor interface."""
    def __init__(self, cur):
        self._cur = cur

    def fetchone(self):
        return self._cur.fetchone()

    def fetchall(self):
        return self._cur.fetchall()

    @property
    def rowcount(self):
        return self._cur.rowcount

    def __iter__(self):
        return iter(self._cur.fetchall())

    def __getitem__(self, idx):
        return self._cur.fetchall()[idx]


class PGConn:
    """
    Thin wrapper around a psycopg2 connection that exposes the sqlite3-style
    ``conn.execute(sql, params)`` interface so that the rest of backend.py can
    stay largely unchanged.
    """
    def __init__(self, raw):
        self._raw = raw

    def execute(self, sql, params=()):
        cur = self._raw.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(sql, params if params else None)
        return _PGCursor(cur)

    def commit(self):
        self._raw.commit()

    def rollback(self):
        self._raw.rollback()

    def close(self):
        self._raw.close()

    # Expose raw connection for direct cursor creation if ever needed
    @property
    def raw(self):
        return self._raw


def wrap_conn(raw_psycopg2_conn):
    """Wrap a raw psycopg2 connection in the sqlite3-compatible PGConn wrapper."""
    return PGConn(raw_psycopg2_conn)


def _cursor(conn):
    """Return a RealDictCursor for the given connection."""
    return conn.raw.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

state = {'active_run_id' : None, 'active_attempt_id': None, 'active_game_id': None, 'active_starter': None, 'version_group_id': None}
active_party = {
    1:'',
    2:'',
    3:'',
    4:'',
    5:'',
    6:''
}

def get_games(conn):
    cur = _cursor(conn)
    cur.execute("SELECT game_id, name, game_tag, generation, version_group_id from games where valid_game = 'valid'")
    return cur.fetchall()

def _get_game_generation(conn, game_id=None, run_id=None):
    cur = _cursor(conn)
    if game_id is not None:
        cur.execute('select generation from games where nullif(game_id::text, \'\')::integer = %s', (game_id,))
        row = cur.fetchone()
        return row['generation'] if row else None
    if run_id is not None:
        cur.execute(
            'select g.generation from runs r '
            'join games g on nullif(r.game_id::text, \'\')::integer = nullif(g.game_id::text, \'\')::integer '
            'where nullif(r.run_id::text, \'\')::integer = %s',
            (run_id,)
        )
        row = cur.fetchone()
        return row['generation'] if row else None
    return None

def _build_generation_patch_join(table_name, join_alias, species_expr, generation_expr):
    return (
        f'left join lateral (\n'
        f'  select * from {table_name} x\n'
        f'  where x.species_id = {species_expr}\n'
        f'    and (x.generation is null or x.generation >= coalesce({generation_expr}, 9999))\n'
        f'  order by case when x.generation is null then 1 else 0 end, x.generation asc\n'
        f'  limit 1\n'
        f') {join_alias} on true\n'
    )

def set_active_game(conn, game):
    state['active_game_id'] = game
    state['version_group_id'] = conn.execute('select version_group_id from games where game_id = (%s)', (game,)).fetchone()['version_group_id']

def create_run(conn, name, user_id=None):
    _ensure_auth_schema(conn)
    conn.execute(
        "insert into runs (game_id, name, user_id) values (%s,%s,%s)",
        (state['active_game_id'], name, user_id)
    )
    conn.commit()
    set_active_run(conn.execute('select run_id from runs order by run_id desc limit 1').fetchone()['run_id'])
    new_attempt(conn)

def get_runs(conn, user_id=None):
    _ensure_auth_schema(conn)
    query = (
        'SELECT '
        '  r.run_id, '
        '  r.game_id, '
        '  g.name as game_name, '
        '  g.game_tag, '
        '  r.name as run_name, '
        '  a.latest_attempt, '
        '  a.total_attempts, '
        '  r.created_at, '
        '  coalesce(r.victory, \'false\') as victory_item, '
        '  r.beaten_at '
        'FROM runs r '
        'LEFT JOIN games g on nullif(r.game_id::text, \'\')::integer = nullif(g.game_id::text, \'\')::integer '
        'LEFT JOIN ('
        '  SELECT run_id, max(attempt_number) as latest_attempt, count(*) as total_attempts '
        '  FROM attempts '
        '  GROUP BY run_id'
        ') a ON r.run_id = a.run_id '
    )
    params = []
    if user_id is not None:
        query += 'WHERE nullif(r.user_id::text, \'\')::integer = %s '
        params.append(user_id)
    query += 'ORDER BY r.run_id DESC'
    runs = conn.execute(query, params).fetchall()

    enriched_runs = []
    for row in runs:
        run_data = dict(row)
        latest_attempt = run_data.get('latest_attempt')
        if latest_attempt is not None:
            latest_party = get_party_for_attempt(conn, run_data['run_id'], latest_attempt)
            run_data['latest_party'] = [dict(member) for member in latest_party]
            run_data['latest_attempt_stats'] = get_attempt_session_stats(conn, run_data['run_id'], latest_attempt)
            attempt_row = conn.execute(
                'select attempt_id from attempts where run_id = %s and attempt_number = %s',
                (run_data['run_id'], latest_attempt)
            ).fetchone()
            run_data['latest_attempt_badges'] = sorted(
                _get_attempt_badge_ids(
                    conn,
                    attempt_row['attempt_id'],
                    run_id=run_data['run_id'],
                    fallback_to_pokebank=True
                )
            ) if attempt_row else []
        else:
            run_data['latest_party'] = []
            run_data['latest_attempt_stats'] = None
            run_data['latest_attempt_badges'] = []
        enriched_runs.append(run_data)

    return enriched_runs
def get_run_by_id(conn, run_id, attempt_number, user_id=None):
    # return conn.execute('select run_id, runs.name, runs.game_id, games.name as game_name from runs left join games on runs.game_id = games.game_id where runs.run_id = (%s)',(run_id,)).fetchone()
    _ensure_auth_schema(conn)
    query = (
        'select run.run_id, run.name, run.game_id, run.game_name, run.version_group_id, attempts.starter '
        'from ('
        '  select run_id, runs.name, runs.game_id, runs.user_id, games.name as game_name, games.version_group_id '
        '  from runs left join games on nullif(runs.game_id::text, \'\')::integer = nullif(games.game_id::text, \'\')::integer where nullif(runs.run_id::text, \'\')::integer = %s'
        ') as run '
        'left join attempts on run.run_id = attempts.run_id '
        'where attempts.attempt_number = %s'
    )
    params = [run_id, attempt_number]
    if user_id is not None:
        query += ' and run.user_id = %s'
        params.append(user_id)
    return conn.execute(query, params).fetchone()

def delete_run(conn, run_id):
    attempts = [x['attempt_id'] for x in conn.execute('select attempt_id from attempts where run_id = (%s)',(run_id,)).fetchall()]
    #delete from runs
    conn.execute('delete from runs where run_id = (%s)',(run_id,))
    #delete from pokebank
    conn.execute('delete from pokebank where run_id = (%s)',(run_id,))
    #delete from party
    for attempt_id in attempts:
        conn.execute('delete from party where attempt_id = (%s)',(attempt_id,))
        # delete from attempts
        conn.execute('delete from attempts where attempt_id = (%s)',(attempt_id,))
        conn.execute('delete from badges where attempt_id = (%s)',(attempt_id,))
        conn.execute('delete from trainers_defeated where attempt_id = (%s)',(attempt_id,))
    conn.commit()

def set_active_run(run_id):
    state['active_run_id'] = run_id

def new_attempt(conn, ):
    has_attempt_badges_earned = _has_column(conn, 'attempts', 'badges_earned')
    attempts = conn.execute(f'select attempt_number, is_active from attempts where run_id = {state["active_run_id"]}').fetchall()
    if len(attempts) == 0:
        #create new attempt on run with id = 1
        if has_attempt_badges_earned:
            conn.execute("insert into attempts (run_id, attempt_number, starter, badges_earned) values (%s,%s,%s,%s)",
                        (state['active_run_id'], 1, 'Fire', '') )
        else:
            conn.execute("insert into attempts (run_id, attempt_number, starter) values (%s,%s,%s)",
                        (state['active_run_id'], 1, 'Fire') )
        state['active_attempt_id'] = 1
    else:
        new_attempt_number = attempts[::-1][0][0] + 1
        #create new attempt on run with id = 1
        if has_attempt_badges_earned:
            conn.execute("insert into attempts (run_id, attempt_number, starter, badges_earned) values (%s,%s,%s,%s)",
                        (state['active_run_id'], new_attempt_number, 'Fire', '') )
        else:
            conn.execute("insert into attempts (run_id, attempt_number, starter) values (%s,%s,%s)",
                        (state['active_run_id'], new_attempt_number, 'Fire') )
        set_active_attempt(new_attempt_number)
    conn.commit()

def get_attempts(conn):
    return conn.execute(f'select attempt_number from attempts where run_id = {state["active_run_id"]}').fetchall()

def get_attempts_for_run(conn, run_id):
    return conn.execute(
        'select attempt_number from attempts where run_id = %s order by attempt_number asc',
        (run_id,)
    ).fetchall()

def update_starter(conn, run_id, attempt_number, starter):
    conn.execute(
        'update attempts set starter = %s where run_id = %s and attempt_number = %s',
        (starter, run_id, attempt_number)
    )
    conn.commit()

def create_attempt_for_run(conn, run_id):
    latest = conn.execute(
        'select max(attempt_number) as max_num from attempts where run_id = %s',
        (run_id,)
    ).fetchone()['max_num'] or 0
    new_num = latest + 1
    if _has_column(conn, 'attempts', 'badges_earned'):
        conn.execute(
            'insert into attempts (run_id, attempt_number, starter, badges_earned) values (%s, %s, %s, %s)',
            (run_id, new_num, 'Fire', '')
        )
    else:
        conn.execute(
            'insert into attempts (run_id, attempt_number, starter) values (%s, %s, %s)',
            (run_id, new_num, 'Fire')
        )
    conn.commit()
    return new_num

def get_latest_attempt(conn):
    return conn.execute(f'select attempt_id from attempts where run_id = {state["active_run_id"]} order by attempt_id desc limit 1').fetchone()

def set_active_attempt(attempt):
    state['active_attempt_id'] = attempt

def get_pokebank(conn):
    return conn.execute(f'select pokemon_id, species_id, location_id, level_met, nickname, status, shiny, storage, party_slot, bonus_location, bonus_note from pokebank').fetchall()

def get_pokebank_feed_for_user(conn, user_id, limit=360):
    has_badges_earned = conn.execute(
        "select 1 from information_schema.columns where table_name = 'pokebank' and column_name = 'badges_earned' limit 1"
    ).fetchone() is not None

    badges_select = 'pb.badges_earned' if has_badges_earned else "'' as badges_earned"

    rows = conn.execute(
        f'select pb.species_id, {badges_select}, pb.shiny, pb.status '
        f'from pokebank pb '
        f'join runs r on nullif(pb.run_id::text, \'\')::integer = nullif(r.run_id::text, \'\')::integer '
        f'where r.user_id = %s and (pb.status = %s or pb.status = %s) '
        f'order by RANDOM() '
        f'limit %s',
        (user_id, 'Captured', 'Dead', min(limit, 500))
    ).fetchall()
    return [dict(r) for r in rows]

def get_graveyard(conn):
    return conn.execute("select pokemon_id, species_id, location_id, level_met, nickname, status, shiny, storage, party_slot, bonus_location, bonus_note from pokebank where status = 'Dead'").fetchall()

def get_party(conn):
    party = conn.execute('select party_slot, pokemon_id from party where attempt_id = (%s)', (state['active_attempt_id'],)).fetchall()
    #emplace in active_party
    for member in party:
        active_party[member['party_slot']] = member['pokemon_id']

def update_party():
    pass

def swap_party_slots(pokemon_1, pokemon_2):
    active_party[pokemon_1['party_slot']] = pokemon_2['pokemon_id']
    #within party
    if pokemon_2['party_slot']:
        active_party[pokemon_2['party_slot']] = pokemon_1['pokemon_id']
    #outside of party

def drop_from_party(party_slot):
    active_party[party_slot] = ''
    update_party()

def get_box(conn):
    return conn.execute("select pokemon_id, species_id, location_id, level_met, nickname, status, shiny, storage, party_slot, bonus_location, bonus_note from pokebank where attempt_id = (%s) and run_id = (%s) and status = 'Captured'", (state['active_attempt_id'], state['active_run_id'],)).fetchall()

def get_species_search(conn, name):
    return conn.execute('select name, species_id from species where name like (%s)',('%'+name+'%',)).fetchall()

def get_species_summary(conn, species_id, game_id=None):
    game_generation = _get_game_generation(conn, game_id=game_id)
    row = conn.execute(
        'select s.species_id, s.name, st.type1, st.type2, ss.bst, ss.hp, ss.atk, ss.def, ss.spa, ss.spd, ss.spe '
        'from species s '
        + _build_generation_patch_join('species_stats', 'ss', 's.species_id', '%s')
        + _build_generation_patch_join('species_types', 'st', 's.species_id', '%s')
        + 'where s.species_id = %s',
        (game_generation, game_generation, species_id)
    ).fetchone()
    return dict(row) if row else None

def get_evolutions(conn, species_id):
    return conn.execute(
        'select e.to_species_id, s.name from evolutions e '
        'join species s on e.to_species_id = s.species_id '
        'where e.from_species_id = (%s)',
        (species_id,)
    ).fetchall()

def _get_attempt_row(conn, run_id, attempt_number):
    return conn.execute(
        'select attempt_id from attempts where run_id = %s and attempt_number = %s',
        (run_id, attempt_number)
    ).fetchone()

def _get_run_version_group_id(conn, run_id):
    row = conn.execute(
        'select g.version_group_id '
        'from runs r join games g on nullif(r.game_id::text, \'\')::integer = nullif(g.game_id::text, \'\')::integer '
        'where nullif(r.run_id::text, \'\')::integer = %s',
        (run_id,)
    ).fetchone()
    return row['version_group_id'] if row else None

def _ensure_bonus_locations_schema(conn):
    conn.execute(
        'create table if not exists bonus_locations ('
        'bonus_location_id serial primary key, '
        'run_id integer, '
        'attempt_id integer, '
        'canonical_location_id integer, '
        'canonical_name text not null, '
        'sort_order integer, '
        'secondary_sort_order integer default 0, '
        'is_active integer default 1, '
        'version_group_id integer, '
        'event_type text'
        ')'
    )
    conn.commit()

def create_bonus_location(conn, run_id, attempt_number, canonical_location_id):
    _ensure_bonus_locations_schema(conn)
    attempt_row = _get_attempt_row(conn, run_id, attempt_number)
    if not attempt_row:
        return {'success': False, 'error': 'Attempt not found'}

    attempt_id = attempt_row['attempt_id']
    version_group_id = _get_run_version_group_id(conn, run_id)
    if version_group_id is None:
        return {'success': False, 'error': 'Run not found'}

    base_row = conn.execute(
        'select canonical_name, sort_order, coalesce(secondary_sort_order, 0) as secondary_sort_order, event_type '
        'from event_locations '
        'where canonical_location_id = %s and version_group_id = %s '
        'limit 1',
        (canonical_location_id, version_group_id)
    ).fetchone()
    if not base_row:
        return {'success': False, 'error': 'Base location not found'}

    existing_max = conn.execute(
        'select max(secondary_sort_order) as max_secondary_sort_order '
        'from bonus_locations '
        'where run_id = %s and attempt_id = %s and canonical_location_id = %s and is_active = 1',
        (run_id, attempt_id, canonical_location_id)
    ).fetchone()['max_secondary_sort_order']

    next_secondary_sort = max(int(base_row['secondary_sort_order'] or 0), int(existing_max or 0)) + 1
    canonical_name = f"{base_row['canonical_name']} - Bonus"

    conn.execute(
        'insert into bonus_locations ('
        'run_id, attempt_id, canonical_location_id, canonical_name, sort_order, '
        'secondary_sort_order, is_active, version_group_id, event_type'
        ') values (%s, %s, %s, %s, %s, %s, %s, %s, %s)',
        (
            run_id,
            attempt_id,
            canonical_location_id,
            canonical_name,
            base_row['sort_order'],
            next_secondary_sort,
            1,
            version_group_id,
            base_row['event_type'],
        )
    )
    conn.commit()

    return {
        'success': True,
        'run_id': run_id,
        'attempt_id': attempt_id,
        'event_id': canonical_location_id,
        'display_name': canonical_name,
        'sort_order': base_row['sort_order'],
        'secondary_sort_order': next_secondary_sort,
        'encounter_key': f'{canonical_location_id}:{next_secondary_sort}',
        'event_type': base_row['event_type'],
        'is_bonus_location': True,
    }

def delete_bonus_location(conn, run_id, attempt_number, canonical_location_id, secondary_sort_order):
    _ensure_bonus_locations_schema(conn)
    attempt_row = _get_attempt_row(conn, run_id, attempt_number)
    if not attempt_row:
        return {'success': False, 'error': 'Attempt not found'}

    attempt_id = attempt_row['attempt_id']
    bonus_row = conn.execute(
        'select 1 from bonus_locations '
        'where run_id = %s and attempt_id = %s and canonical_location_id = %s and secondary_sort_order = %s and is_active = 1 '
        'limit 1',
        (run_id, attempt_id, canonical_location_id, secondary_sort_order)
    ).fetchone()
    if not bonus_row:
        return {'success': False, 'error': 'Bonus location not found'}

    pokemon_ids = [
        row['pokemon_id'] for row in conn.execute(
            'select pokemon_id from pokebank '
            'where run_id = %s and attempt_id = %s and location_id = %s and coalesce(bonus_location, 0) = %s',
            (run_id, attempt_id, canonical_location_id, secondary_sort_order)
        ).fetchall()
    ]

    if pokemon_ids:
        placeholders = ','.join(['%s'] * len(pokemon_ids))
        conn.execute(
            f'delete from party where attempt_id = %s and pokemon_id in ({placeholders})',
            (attempt_id, *pokemon_ids)
        )

    conn.execute(
        'delete from pokebank '
        'where run_id = %s and attempt_id = %s and location_id = %s and coalesce(bonus_location, 0) = %s',
        (run_id, attempt_id, canonical_location_id, secondary_sort_order)
    )
    conn.execute(
        'delete from bonus_locations '
        'where run_id = %s and attempt_id = %s and canonical_location_id = %s and secondary_sort_order = %s',
        (run_id, attempt_id, canonical_location_id, secondary_sort_order)
    )
    conn.commit()

    return {'success': True}

def rename_bonus_location(conn, run_id, attempt_number, canonical_location_id, secondary_sort_order, canonical_name):
    _ensure_bonus_locations_schema(conn)
    attempt_row = _get_attempt_row(conn, run_id, attempt_number)
    if not attempt_row:
        return {'success': False, 'error': 'Attempt not found'}

    new_name = (canonical_name or '').strip()
    if not new_name:
        return {'success': False, 'error': 'Location name required'}

    attempt_id = attempt_row['attempt_id']
    updated = conn.execute(
        'update bonus_locations '
        'set canonical_name = %s '
        'where run_id = %s and attempt_id = %s and canonical_location_id = %s and secondary_sort_order = %s and is_active = 1',
        (new_name, run_id, attempt_id, canonical_location_id, secondary_sort_order)
    )
    if updated.rowcount == 0:
        return {'success': False, 'error': 'Bonus location not found'}

    conn.commit()
    return {'success': True, 'canonical_name': new_name}

def get_party_for_attempt(conn, run_id, attempt_number):
    row = conn.execute(
        'select attempt_id from attempts where run_id = %s and attempt_number = %s',
        (run_id, attempt_number)
    ).fetchone()
    if not row:
        return []
    attempt_id = row['attempt_id']
    game_generation = _get_game_generation(conn, run_id=run_id)

    has_badges_earned = conn.execute(
        "select 1 from information_schema.columns where table_name = 'pokebank' and column_name = 'badges_earned' limit 1"
    ).fetchone() is not None

    badges_select = ', pb.badges_earned' if has_badges_earned else ''
    return conn.execute(
        'select p.party_slot, p.pokemon_id, pb.species_id, s.name as species_name, pb.nickname, pb.shiny, '
        'pb.level_met, st.type1, st.type2, sa.ability1, sa.ability2, sa.ability3, ss.bst, ss.hp, ss.atk, ss.def, ss.spa, ss.spd, ss.spe '
        + badges_select + ' '
        'from party p '
        'join pokebank pb on p.pokemon_id = pb.pokemon_id '
        'join species s on pb.species_id = s.species_id '
        + _build_generation_patch_join('species_stats', 'ss', 'pb.species_id', '%s')
        + _build_generation_patch_join('species_types', 'st', 'pb.species_id', '%s')
        + _build_generation_patch_join('species_abilities', 'sa', 'pb.species_id', '%s')
        + 'where p.attempt_id = %s '
        + 'order by p.party_slot',
        (game_generation, game_generation, game_generation, attempt_id)
    ).fetchall()

def add_to_party_for_attempt(conn, run_id, attempt_number, pokemon_id):
    row = conn.execute(
        'select attempt_id from attempts where run_id = %s and attempt_number = %s',
        (run_id, attempt_number)
    ).fetchone()
    if not row:
        return None
    attempt_id = row['attempt_id']
    occupied = {r['party_slot'] for r in conn.execute(
        'select party_slot from party where attempt_id = %s', (attempt_id,)
    ).fetchall()}
    # check if already in party
    already = conn.execute(
        'select party_slot from party where attempt_id = %s and pokemon_id = %s', (attempt_id, pokemon_id)
    ).fetchone()
    if already:
        return already['party_slot']
    next_slot = next((i for i in range(1, 7) if i not in occupied), None)
    if next_slot is None:
        return None
    conn.execute(
        'insert into party (attempt_id, party_slot, pokemon_id) values (%s, %s, %s)',
        (attempt_id, next_slot, pokemon_id)
    )
    conn.commit()
    return next_slot

def remove_from_party_for_attempt(conn, run_id, attempt_number, pokemon_id):
    row = conn.execute(
        'select attempt_id from attempts where run_id = %s and attempt_number = %s',
        (run_id, attempt_number)
    ).fetchone()
    if not row:
        return
    attempt_id = row['attempt_id']
    conn.execute(
        'delete from party where attempt_id = %s and pokemon_id = %s',
        (attempt_id, pokemon_id)
    )
    conn.commit()

def _parse_id_set(value):
    if value is None:
        return set()
    text = str(value).strip()
    if not text:
        return set()

    if text.startswith('['):
        try:
            data = json.loads(text)
            return {int(x) for x in data if str(x).strip().isdigit()}
        except Exception:
            pass

    parts = [p.strip() for p in text.replace('[', '').replace(']', '').split(',')]
    return {int(p) for p in parts if p.isdigit()}

def _parse_badges_earned(value):
    return _parse_id_set(value)

def _has_column(conn, table_name, column_name):
    return conn.execute(
        'select 1 from information_schema.columns '
        'where table_name = %s and column_name = %s limit 1',
        (table_name, column_name)
    ).fetchone() is not None

def _normalize_email(email):
    return (email or '').strip().lower()

def _public_user(row):
    if not row:
        return None
    return {
        'user_id': int(row['user_id']),
        'email': row['email'],
        'display_name': row['display_name'] or row['email'].split('@')[0],
        'created_at': row['created_at'],
    }

def _ensure_auth_schema(conn):
    conn.execute(
        'create table if not exists users ('
        'user_id serial primary key, '
        'email text not null unique, '
        'password_hash text not null default \'\', '
        'display_name text, '
        "created_at text not null default to_char(current_timestamp, 'YYYY-MM-DD HH24:MI:SS')"
        ')'
    )
    if not _has_column(conn, 'runs', 'user_id'):
        conn.execute('alter table runs add column user_id integer')
    if not _has_column(conn, 'users', 'supabase_id'):
        conn.execute('alter table users add column supabase_id text unique')
    conn.execute('create index if not exists idx_runs_user_id on runs(user_id)')
    conn.execute('create index if not exists idx_users_email on users(email)')
    conn.execute('create index if not exists idx_users_supabase_id on users(supabase_id)')
    conn.commit()

def get_user_by_id(conn, user_id):
    _ensure_auth_schema(conn)
    row = conn.execute(
        'select user_id, email, display_name, created_at from users where user_id = %s',
        (user_id,)
    ).fetchone()
    return _public_user(row)

def get_or_create_user_by_supabase_id(conn, supabase_id, email=None):
    _ensure_auth_schema(conn)
    row = conn.execute(
        'select user_id, email, display_name, created_at from users where supabase_id = %s',
        (supabase_id,)
    ).fetchone()
    if row:
        return _public_user(row)

    normalized_email = _normalize_email(email)

    # If this email already exists locally (legacy account), link it instead of inserting.
    if normalized_email:
        existing = conn.execute(
            'select user_id, email, display_name, created_at, supabase_id '
            'from users where lower(email) = %s',
            (normalized_email,)
        ).fetchone()
        if existing:
            existing_supabase_id = (existing.get('supabase_id') or '').strip()
            if not existing_supabase_id or existing_supabase_id == supabase_id:
                conn.execute(
                    'update users set supabase_id = %s where user_id = %s',
                    (supabase_id, existing['user_id'])
                )
                conn.commit()
                user = _public_user(existing)
                if user:
                    claim_legacy_runs_for_user(conn, user['user_id'])
                return user

    # First login for this Supabase user with no local email match — create a local record.
    try:
        conn.execute(
            'insert into users (supabase_id, email, password_hash, display_name) values (%s, %s, %s, %s)',
            (supabase_id, normalized_email or '', '', None)
        )
        conn.commit()
    except psycopg2.errors.UniqueViolation:
        # A concurrent insert/link won the race. Recover by reloading the now-existing row.
        conn.rollback()

    row = conn.execute(
        'select user_id, email, display_name, created_at from users where supabase_id = %s',
        (supabase_id,)
    ).fetchone()

    if not row and normalized_email:
        row = conn.execute(
            'select user_id, email, display_name, created_at from users where lower(email) = %s',
            (normalized_email,)
        ).fetchone()
        if row:
            conn.execute(
                'update users set supabase_id = %s where user_id = %s',
                (supabase_id, row['user_id'])
            )
            conn.commit()
            row = conn.execute(
                'select user_id, email, display_name, created_at from users where supabase_id = %s',
                (supabase_id,)
            ).fetchone()

    user = _public_user(row)
    if user:
        claim_legacy_runs_for_user(conn, user['user_id'])
    return user

def get_user_by_email(conn, email):
    _ensure_auth_schema(conn)
    normalized_email = _normalize_email(email)
    if not normalized_email:
        return None
    row = conn.execute(
        'select user_id, email, display_name, created_at from users where lower(email) = %s',
        (normalized_email,)
    ).fetchone()
    return _public_user(row)

def register_user(conn, email, password, display_name=None):
    _ensure_auth_schema(conn)
    normalized_email = _normalize_email(email)
    cleaned_name = (display_name or '').strip()

    if not normalized_email or '@' not in normalized_email:
        return {'success': False, 'error': 'Valid email required'}
    if len(password or '') < 8:
        return {'success': False, 'error': 'Password must be at least 8 characters'}
    if get_user_by_email(conn, normalized_email):
        return {'success': False, 'error': 'An account with that email already exists'}

    conn.execute(
        'insert into users (email, password_hash, display_name) values (%s, %s, %s)',
        (normalized_email, generate_password_hash(password), cleaned_name or None)
    )
    conn.commit()
    user = get_user_by_email(conn, normalized_email)
    if user:
        claim_legacy_runs_for_user(conn, user['user_id'])
    return {'success': True, 'user': user}

def authenticate_user(conn, email, password):
    _ensure_auth_schema(conn)
    normalized_email = _normalize_email(email)
    row = conn.execute(
        'select user_id, email, password_hash, display_name, created_at from users where lower(email) = %s',
        (normalized_email,)
    ).fetchone()
    if not row or not check_password_hash(row['password_hash'], password or ''):
        return {'success': False, 'error': 'Invalid email or password'}

    user = _public_user(row)
    claim_legacy_runs_for_user(conn, user['user_id'])
    return {'success': True, 'user': user}

def claim_legacy_runs_for_user(conn, user_id):
    _ensure_auth_schema(conn)
    user_count = conn.execute('select count(*) as count from users').fetchone()['count']
    if int(user_count or 0) != 1:
        return 0
    updated = conn.execute('update runs set user_id = %s where user_id is null', (user_id,))
    conn.commit()
    return updated.rowcount

def get_run_owner_id(conn, run_id):
    _ensure_auth_schema(conn)
    row = conn.execute('select user_id from runs where run_id = %s', (run_id,)).fetchone()
    return row['user_id'] if row else None

def run_belongs_to_user(conn, run_id, user_id):
    owner_id = get_run_owner_id(conn, run_id)
    return owner_id is not None and int(owner_id) == int(user_id)

def get_run_id_for_pokemon(conn, pokemon_id):
    row = conn.execute('select run_id from pokebank where pokemon_id = %s', (pokemon_id,)).fetchone()
    return row['run_id'] if row else None

def pokemon_belongs_to_user(conn, pokemon_id, user_id):
    run_id = get_run_id_for_pokemon(conn, pokemon_id)
    if run_id is None:
        return False
    return run_belongs_to_user(conn, run_id, user_id)

def _ensure_attempt_badges_earned_schema(conn):
    if not _has_column(conn, 'attempts', 'badges_earned'):
        conn.execute("alter table attempts add column badges_earned text")
        conn.commit()

def _get_attempt_badge_ids(conn, attempt_id, run_id=None, fallback_to_pokebank=False):
    has_attempt_badges_column = _has_column(conn, 'attempts', 'badges_earned')
    if _has_column(conn, 'attempts', 'badges_earned'):
        row = conn.execute(
            'select badges_earned from attempts where attempt_id = %s',
            (attempt_id,)
        ).fetchone()
        badge_ids = _parse_badges_earned(row['badges_earned']) if row else set()
        if badge_ids or not fallback_to_pokebank:
            return badge_ids

    if fallback_to_pokebank and run_id is not None and _has_column(conn, 'pokebank', 'badges_earned'):
        badge_rows = conn.execute(
            'select badges_earned from pokebank where run_id = %s and attempt_id = %s',
            (run_id, attempt_id)
        ).fetchall()
        badge_ids = set()
        for row in badge_rows:
            badge_ids.update(_parse_badges_earned(row['badges_earned']))
        if badge_ids and has_attempt_badges_column:
            _set_attempt_badge_ids(conn, attempt_id, badge_ids)
            conn.commit()
        return badge_ids

    return set()

def _set_attempt_badge_ids(conn, attempt_id, badge_ids):
    _ensure_attempt_badges_earned_schema(conn)
    badge_text = ','.join(str(x) for x in sorted(int(badge_id) for badge_id in badge_ids))
    conn.execute(
        'update attempts set badges_earned = %s where attempt_id = %s',
        (badge_text, attempt_id)
    )

def _badge_id_for_gym_leader(trainer_name, encounter_title):
    tname = (trainer_name or '').upper()
    etitle = (encounter_title or '').lower()

    if 'BROCK' in tname or 'pewter' in etitle:
        return 1
    if 'MISTY' in tname or 'cerulean' in etitle:
        return 2
    if 'LT_SURGE' in tname or 'vermilion' in etitle:
        return 3
    if 'ERIKA' in tname or 'celadon' in etitle:
        return 4
    if 'KOGA' in tname or 'fuchsia' in etitle:
        return 5
    if 'SABRINA' in tname or 'saffron' in etitle:
        return 6
    if 'BLAINE' in tname or 'cinnabar' in etitle:
        return 7
    if 'GIOVANNI' in tname or 'viridian' in etitle:
        return 8
    return None

def mark_trainer_victory(conn, run_id, attempt_number, trainer_id, trainer_name, trainer_class, encounter_title):
    row = conn.execute(
        'select attempt_id from attempts where run_id = %s and attempt_number = %s',
        (run_id, attempt_number)
    ).fetchone()
    if not row:
        return {'success': False, 'error': 'Attempt not found'}
    attempt_id = row['attempt_id']

    existing = conn.execute(
        'select 1 from trainers_defeated where run_id = %s and attempt_id = %s and trainer_id = %s limit 1',
        (run_id, attempt_id, trainer_id)
    ).fetchone()
    if not existing:
        conn.execute(
            'insert into trainers_defeated (run_id, attempt_id, trainer_id) values (%s, %s, %s)',
            (run_id, attempt_id, trainer_id)
        )

    class_text = (trainer_class or '').upper()
    is_gym_leader = 'LEADER' in class_text
    badge_awarded = None
    updated_party_pokemon = 0
    _ensure_attempt_badges_earned_schema(conn)

    has_badges_earned = _has_column(conn, 'pokebank', 'badges_earned')
    if not has_badges_earned:
        conn.execute('alter table pokebank add column badges_earned text')
        conn.commit()
        has_badges_earned = True

    has_trainers_defeated = _has_column(conn, 'pokebank', 'trainers_defeated')
    if not has_trainers_defeated:
        conn.execute('alter table pokebank add column trainers_defeated text')
        conn.commit()
        has_trainers_defeated = True

    if has_trainers_defeated:
        party_rows = conn.execute(
            'select pb.pokemon_id, pb.trainers_defeated '
            'from party p join pokebank pb on p.pokemon_id = pb.pokemon_id '
            'where p.attempt_id = %s',
            (attempt_id,)
        ).fetchall()
        for pr in party_rows:
            defeated_ids = _parse_id_set(pr['trainers_defeated'])
            if trainer_id in defeated_ids:
                continue
            defeated_ids.add(trainer_id)
            defeated_text = ','.join(str(x) for x in sorted(defeated_ids))
            conn.execute(
                'update pokebank set trainers_defeated = %s where pokemon_id = %s',
                (defeated_text, pr['pokemon_id'])
            )
            updated_party_pokemon += 1

    if is_gym_leader and has_badges_earned:
        badge_id = _badge_id_for_gym_leader(trainer_name, encounter_title)
        if badge_id is not None:
            badge_row = conn.execute(
                'select badge_id, badge_name from badges where badge_id = %s limit 1',
                (badge_id,)
            ).fetchone()
            badge_awarded = dict(badge_row) if badge_row else {'badge_id': badge_id, 'badge_name': f'Badge {badge_id}'}

            attempt_badges = _get_attempt_badge_ids(conn, attempt_id, run_id=run_id, fallback_to_pokebank=True)
            if badge_id not in attempt_badges:
                attempt_badges.add(badge_id)
                _set_attempt_badge_ids(conn, attempt_id, attempt_badges)

            party_rows = conn.execute(
                'select pb.pokemon_id, pb.badges_earned '
                'from party p join pokebank pb on p.pokemon_id = pb.pokemon_id '
                'where p.attempt_id = %s',
                (attempt_id,)
            ).fetchall()
            for pr in party_rows:
                earned = _parse_badges_earned(pr['badges_earned'])
                if badge_id in earned:
                    continue
                earned.add(badge_id)
                earned_text = ','.join(str(x) for x in sorted(earned))
                conn.execute(
                    'update pokebank set badges_earned = %s where pokemon_id = %s',
                    (earned_text, pr['pokemon_id'])
                )
                updated_party_pokemon += 1

    conn.commit()
    return {
        'success': True,
        'badge_awarded': badge_awarded,
        'is_gym_leader': is_gym_leader,
        'updated_party_pokemon': updated_party_pokemon,
        'has_badges_earned_column': has_badges_earned,
        'has_trainers_defeated_column': has_trainers_defeated,
    }

def get_evolution_families(conn, species_ids):
    """Return all species_ids in the same evolution chain(s) as the given ids."""
    if not species_ids:
        return []
    # Normalize to integers so the IN clause is always type-safe on Postgres.
    family = {int(s) for s in species_ids}
    frontier = set(family)
    while frontier:
        placeholders = ','.join(['%s'] * len(frontier))
        frontier_list = list(frontier)
        next_frontier = set()
        for row in conn.execute(
            f'SELECT to_species_id FROM evolutions WHERE from_species_id IN ({placeholders})',
            frontier_list,
        ).fetchall():
            sid = int(dict(row)['to_species_id'])
            if sid not in family:
                next_frontier.add(sid)
                family.add(sid)
        for row in conn.execute(
            f'SELECT from_species_id FROM evolutions WHERE to_species_id IN ({placeholders})',
            frontier_list,
        ).fetchall():
            sid = int(dict(row)['from_species_id'])
            if sid not in family:
                next_frontier.add(sid)
                family.add(sid)
        frontier = next_frontier
    return sorted(family)

def get_attempt_page_data(conn, run_id, attempt_number):
    run = get_run_by_id(conn, run_id, attempt_number)
    if not run:
        return None
    run_dict = dict(run)
    starter = run_dict.get('starter') or 'Fire'
    game_id = run_dict.get('game_id')
    game_row = conn.execute('select version_group_id from games where game_id = %s', (game_id,)).fetchone() if game_id else None
    version_group_id = game_row['version_group_id'] if game_row else None

    script = get_script(conn, starter, version_group_id=version_group_id, run_id=run_id, attempt_number=attempt_number)
    script_list = [dict(r) for r in script]

    attempt_row = conn.execute(
        'select attempt_id from attempts where run_id = %s and attempt_number = %s',
        (run_id, attempt_number)
    ).fetchone()
    defeated_ids = set()
    if attempt_row:
        defeated_rows = conn.execute(
            'select trainer_id from trainers_defeated where run_id = %s and attempt_id = %s',
            (run_id, attempt_row['attempt_id'])
        ).fetchall()
        defeated_ids = {int(r['trainer_id']) for r in defeated_rows}

    for row in script_list:
        trainer_id = row.get('event_id')
        row['is_defeated'] = bool(trainer_id in defeated_ids)
        row['secondary_sort_order'] = int(row.get('secondary_sort_order') or 0)
        row['is_bonus_location'] = bool(row.get('is_bonus_location'))
        row['encounter_key'] = f"{row['event_id']}:{row['secondary_sort_order']}"

    location_ids = sorted({r['event_id'] for r in script_list if r['event_type'] == 'Location'})

    available_trainers_by_location = {}
    if attempt_row and location_ids:
        placeholders = ','.join(['%s'] * len(location_ids))
        trainer_rows = conn.execute(
            f'select tp.location_id, '
            f"count(case when case when lower(coalesce(tp.is_event::text, '')) in ('1', 'true', 't', 'yes') then 1 else 0 end = 0 then 1 end) as trainer_count, "
            f"count(case when case when lower(coalesce(tp.is_event::text, '')) in ('1', 'true', 't', 'yes') then 1 else 0 end = 0 and td.trainer_id is null then 1 end) as available_trainer_count "
            f'from trainer_pool tp '
            f'left join trainers_defeated td '
            f'on td.trainer_id = tp.trainer_id and td.run_id = %s and td.attempt_id = %s '
            f'where tp.location_id in ({placeholders}) '
            f'group by tp.location_id',
            [run_id, attempt_row['attempt_id'], *location_ids]
        ).fetchall()
        available_trainers_by_location = {
            int(row['location_id']): {
                'trainer_count': int(row['trainer_count'] or 0),
                'available_trainer_count': int(row['available_trainer_count'] or 0),
            }
            for row in trainer_rows
        }

    for row in script_list:
        if row['event_type'] != 'Location':
            continue
        trainer_meta = available_trainers_by_location.get(int(row['event_id']), None)
        row['trainer_count'] = trainer_meta['trainer_count'] if trainer_meta else 0
        row['available_trainer_count'] = trainer_meta['available_trainer_count'] if trainer_meta else 0
        row['has_available_trainers'] = bool(row['available_trainer_count'])

    pools = {}
    if location_ids and game_id:
        placeholders = ','.join(['%s'] * len(location_ids))
        rows = conn.execute(
            f'SELECT ep.canonical_location_id, ep.species_id, s.name '
            f'FROM encounter_pool ep '
            f'LEFT JOIN species s ON ep.species_id = s.species_id '
            f'WHERE nullif(ep.canonical_location_id::text, \'\')::integer IN ({placeholders}) AND nullif(ep.game_id::text, \'\')::integer = %s',
            location_ids + [int(game_id)]
        ).fetchall()
        pool_species_ids = {}
        for row in rows:
            lid = int(row['canonical_location_id'])
            if lid not in pools:
                pools[lid] = []
                pool_species_ids[lid] = set()
            if row['species_id'] in pool_species_ids[lid]:
                continue
            pool_species_ids[lid].add(row['species_id'])
            pools[lid].append({'species_id': row['species_id'], 'name': row['name']})

    pokebank = get_pokebank_for_attempt(conn, run_id, attempt_number)
    encounters = {p['encounter_key']: p for p in pokebank}

    return {
        'run': run_dict,
        'script': script_list,
        'pools': pools,
        'encounters': encounters,
    }

def get_attempt_session_stats(conn, run_id, attempt_number):
    attempt_row = conn.execute(
        'select attempt_id from attempts where run_id = %s and attempt_number = %s',
        (run_id, attempt_number)
    ).fetchone()
    if not attempt_row:
        return {'error': 'Attempt not found'}

    attempt_id = attempt_row['attempt_id']

    status_counts = {
        'pokemon_caught': 0,
        'pokemon_dead': 0,
        'pokemon_missed': 0,
    }
    status_rows = conn.execute(
        'select status, count(*) as count '
        'from pokebank '
        'where run_id = %s and attempt_id = %s '
        'group by status',
        (run_id, attempt_id)
    ).fetchall()
    for row in status_rows:
        status = (row['status'] or '').strip().lower()
        count = int(row['count'] or 0)
        if status == 'captured':
            status_counts['pokemon_caught'] = count
        elif status == 'dead':
            status_counts['pokemon_dead'] = count
        elif status == 'missed':
            status_counts['pokemon_missed'] = count

    trainers_defeated = conn.execute(
        'select count(distinct trainer_id) as count from trainers_defeated where run_id = %s and attempt_id = %s',
        (run_id, attempt_id)
    ).fetchone()['count']

    badge_ids = _get_attempt_badge_ids(conn, attempt_id, run_id=run_id, fallback_to_pokebank=True)
    badges_earned = len(badge_ids)

    return {
        'run_id': run_id,
        'attempt_number': attempt_number,
        'badges_earned': badges_earned,
        'badge_ids': sorted(badge_ids),
        'trainers_defeated': int(trainers_defeated or 0),
        'pokemon_caught': status_counts['pokemon_caught'],
        'pokemon_dead': status_counts['pokemon_dead'],
        'pokemon_missed': status_counts['pokemon_missed'],
    }

def add_pokemon(conn, species_id, location_id, nickname, status, shiny):
    conn.execute('insert into pokebank (run_id, attempt_id, species_id, location_id, nickname, status, shiny) values (%s,%s,%s,%s,%s,%s,%s)', (state['active_run_id'],state['active_attempt_id'],species_id, location_id, nickname, status, shiny))
    conn.commit()

def drop_pokemon(conn, pokemon_id):
    conn.execute(f'delete from pokebank where pokemon_id = {pokemon_id}')
    conn.commit()

def get_pokemon_name_from_id(conn, species_id):
    return conn.execute('select name from species where species_id = (%s)',(species_id,)).fetchone()[0]

def upsert_encounter(conn, run_id, attempt_number, location_id, species_id, nickname, nature, status, shiny, pokemon_id=None, bonus_location=0):
    attempt_id = conn.execute(
        'select attempt_id from attempts where run_id = %s and attempt_number = %s',
        (run_id, attempt_number)
    ).fetchone()['attempt_id']
    if pokemon_id:
        conn.execute(
            'update pokebank set species_id=%s, location_id=%s, nickname=%s, nature=%s, status=%s, shiny=%s, bonus_location=%s where pokemon_id=%s',
            (species_id, location_id, nickname, nature, status, shiny, bonus_location, pokemon_id)
        )
        conn.commit()
        return pokemon_id
    else:
        conn.execute(
            'insert into pokebank (run_id, attempt_id, species_id, location_id, nickname, nature, status, shiny, bonus_location) values (%s,%s,%s,%s,%s,%s,%s,%s,%s)',
            (run_id, attempt_id, species_id, location_id, nickname, nature, status, shiny, bonus_location)
        )
        conn.commit()
        return conn.execute('select currval(pg_get_serial_sequence(''pokebank'', ''pokemon_id''))').fetchone()[0]

def delete_encounter(conn, pokemon_id):
    conn.execute('delete from pokebank where pokemon_id = %s', (pokemon_id,))
    conn.commit()
def get_script(conn, starter, version_group_id=None, run_id=None, attempt_number=None):
    _ensure_bonus_locations_schema(conn)
    boss_filter = ''
    loc_filter = ''
    bonus_sql = ''
    params = [starter]

    if version_group_id is not None:
        boss_filter = 'and eb.version_group_id = %s '
        loc_filter = 'where version_group_id = %s '
        params.append(version_group_id)
        params.append(version_group_id)

    if run_id is not None and attempt_number is not None:
        attempt_row = _get_attempt_row(conn, run_id, attempt_number)
        if attempt_row:
            bonus_sql = (
                'union all '
                'select nullif(bl.canonical_location_id::text, \'\')::integer as event_id, bl.canonical_name as display_name, '
                'nullif(bl.sort_order::text, \'\')::double precision as sort_order, coalesce(nullif(bl.secondary_sort_order::text, \'\')::double precision, 0) as secondary_sort_order, '
                'bl.event_type, null, null, null, null, 1 as is_bonus_location '
                'from bonus_locations bl '
                'where bl.run_id = %s and bl.attempt_id = %s and bl.is_active = 1 '
            )
            params.append(run_id)
            params.append(attempt_row['attempt_id'])

    return conn.execute(
        'select nullif(eb.trainer_id::text, \'\')::integer as event_id, eb.encounter_title as display_name, nullif(eb.sort_order::text, \'\')::double precision as sort_order, 0::double precision as secondary_sort_order, eb.event_type, tp.encounter_name, tp.trainer_name, tp.trainer_class, tp.trainer_items, 0::integer as is_bonus_location '
        'from event_bosses eb left join trainer_pool tp on eb.trainer_id = tp.trainer_id '
        "where (eb.starter = (%s) or eb.starter is null or eb.starter = '') "
        f'{boss_filter}'
        'union all '
        'select nullif(canonical_location_id::text, \'\')::integer as event_id, canonical_name as display_name, nullif(sort_order::text, \'\')::double precision as sort_order, coalesce(nullif(secondary_sort_order::text, \'\')::double precision, 0) as secondary_sort_order, event_type, null, null, null, null, 0::integer as is_bonus_location '
        f'from event_locations {loc_filter}'
        f'{bonus_sql}'
        'order by sort_order asc, secondary_sort_order asc',
        tuple(params)).fetchall()

def get_location_by_id(conn, location_id):
    return conn.execute('select canonical_name from event_locations where canonical_location_id = (%s) and version_group_id = (%s)', (location_id, state['version_group_id'],)).fetchone()[0]

def _dedupe_encounter_pool_rows(rows):
    unique_rows = []
    seen_species_ids = set()
    for row in rows:
        row = dict(row)
        species_id = row['species_id']
        if species_id in seen_species_ids:
            continue
        seen_species_ids.add(species_id)
        unique_rows.append({'species_id': species_id, 'name': row['name']})
    return unique_rows

def get_encounter_pool(conn, location_id, game_id):
    tmp = conn.execute('select encounter_pool.species_id, species.name from encounter_pool left join species on encounter_pool.species_id = species.species_id where canonical_location_id::integer = (%s) and game_id::integer = (%s)', (int(location_id), int(game_id))).fetchall()
    return _dedupe_encounter_pool_rows(tmp)

def get_encounters_for_attempt(conn, run_id, attempt_id):
    return conn.execute('select species_id, location_id from pokebank where run_id = (%s) and attempt_id = (%s)', (run_id, attempt_id)).fetchall()

def get_pokebank_with_stats(conn, run_id, attempt_number):
    # Check if badges_earned column exists
    has_badges_earned = conn.execute(
        "select 1 from information_schema.columns where table_name = 'pokebank' and column_name = 'badges_earned' limit 1"
    ).fetchone() is not None
    has_trainers_defeated = conn.execute(
        "select 1 from information_schema.columns where table_name = 'pokebank' and column_name = 'trainers_defeated' limit 1"
    ).fetchone() is not None
    
    badges_select = ', pb.badges_earned' if has_badges_earned else ", '' as badges_earned"
    trainers_defeated_select = ', pb.trainers_defeated' if has_trainers_defeated else ", '' as trainers_defeated"
    
    rows = conn.execute(
        f'select pb.pokemon_id, pb.species_id, s.name as species_name, pb.location_id, '
        f'el.canonical_name as location_name, '
        f'pb.level_met, pb.nickname, pb.nature, pb.status, pb.shiny, '
        f'st.type1, st.type2, sa.ability1, sa.ability2, sa.ability3, ss.hp, ss.atk, ss.def, ss.spa, ss.spd, ss.spe, ss.bst'
        f'{badges_select}{trainers_defeated_select} '
        f'from pokebank pb '
        f'join attempts a on nullif(pb.attempt_id::text, \'\')::integer = nullif(a.attempt_id::text, \'\')::integer '
        f'join runs r on nullif(pb.run_id::text, \'\')::integer = nullif(r.run_id::text, \'\')::integer '
        f'join games g on nullif(r.game_id::text, \'\')::integer = nullif(g.game_id::text, \'\')::integer '
        f'left join species s on pb.species_id = s.species_id '
        f'left join event_locations el on nullif(el.canonical_location_id::text, \'\')::integer = nullif(pb.location_id::text, \'\')::integer and nullif(el.version_group_id::text, \'\')::integer = nullif(g.version_group_id::text, \'\')::integer '
        + _build_generation_patch_join('species_stats', 'ss', 'pb.species_id', 'g.generation')
        + _build_generation_patch_join('species_types', 'st', 'pb.species_id', 'g.generation')
        + _build_generation_patch_join('species_abilities', 'sa', 'pb.species_id', 'g.generation')
        + f'where nullif(pb.run_id::text, \'\')::integer = %s and nullif(a.attempt_number::text, \'\')::integer = %s',
        (run_id, attempt_number)
    ).fetchall()
    return [dict(r) for r in rows]

def get_pokebank_for_attempt(conn, run_id, attempt_number):
    version_group_id = _get_run_version_group_id(conn, run_id)
    rows = conn.execute(
        'select pb.pokemon_id, pb.species_id, s.name as species_name, pb.location_id, '
        'case '
        '  when coalesce(pb.bonus_location, 0) > 0 then pb.bonus_location '
        '  else coalesce(el.secondary_sort_order, 0) '
        'end as secondary_sort_order, '
        'pb.level_met, pb.nickname, pb.nature, pb.status, pb.shiny '
        'from pokebank pb '
        'join attempts a on pb.attempt_id = a.attempt_id '
        'left join species s on pb.species_id = s.species_id '
        'left join event_locations el on el.canonical_location_id = pb.location_id and el.version_group_id = %s '
        'where pb.run_id = (%s) and a.attempt_number = (%s)',
        (version_group_id, run_id, attempt_number)
    ).fetchall()
    result = []
    for row in rows:
        item = dict(row)
        item['secondary_sort_order'] = int(item.get('secondary_sort_order') or 0)
        item['encounter_key'] = f"{item['location_id']}:{item['secondary_sort_order']}"
        result.append(item)
    return result

def get_trainers_by_location(conn, location_id, run_id=None, attempt_number=None):
    attempt_id = None
    if run_id is not None and attempt_number is not None:
        attempt_row = conn.execute(
            'select attempt_id from attempts where run_id = %s and attempt_number = %s',
            (run_id, attempt_number)
        ).fetchone()
        attempt_id = attempt_row['attempt_id'] if attempt_row else None

    params = [location_id]
    defeated_join = ''
    defeated_select = '0 as is_defeated '

    if run_id is not None and attempt_id is not None:
        defeated_join = (
            'left join trainers_defeated td '
            'on td.trainer_id = tp.trainer_id and td.run_id = %s and td.attempt_id = %s '
        )
        defeated_select = 'case when td.trainer_id is null then 0 else 1 end as is_defeated '
        params = [run_id, attempt_id, location_id]

    return conn.execute(
        'select tp.trainer_id, tp.encounter_name, tp.trainer_name, tp.trainer_class, tp.trainer_items, '
        "case when lower(coalesce(tp.is_event::text, '')) in ('1', 'true', 't', 'yes') then 1 else 0 end as is_event, "
        + defeated_select +
        'from trainer_pool tp '
        + defeated_join +
        'where tp.location_id = %s and coalesce(tp.is_rematch, \'\') != \'True\' '
        "order by case when lower(coalesce(tp.is_event::text, '')) in ('1', 'true', 't', 'yes') then 1 else 0 end asc, tp.trainer_id asc",
        params
    ).fetchall()

def _normalize_move_constant(move_token):
    token = (move_token or '').strip()
    if token.startswith('MOVE_'):
        token = token[5:]
    return token.lower().replace('_', '-')

def _format_label(value):
    if value is None:
        return None
    return str(value).replace('_', ' ').replace('-', ' ').title()

def _resolve_move_details(conn, move_id, version_group_id):
    if move_id is None:
        return None

    default = None
    future_candidates = []

    rows = conn.execute(
        'select move_id, move_name, type, damage_class, power, accuracy, version_group_id '
        'from moves where move_id = %s order by version_group_id asc',
        (move_id,)
    ).fetchall()

    for row in rows:
        r = dict(row)
        vg = r.get('version_group_id')
        if vg is None:
            default = r
        elif version_group_id is not None and vg > version_group_id:
            future_candidates.append(r)

    # moves.past_values are stored keyed by the version group where the change happened;
    # for an older game, pick the nearest change row above the target version group.
    selected = min(future_candidates, key=lambda x: x['version_group_id']) if future_candidates else default
    if not selected:
        return None

    return {
        'move_id': selected['move_id'],
        'move_name': _format_label(selected['move_name']),
        'type': _format_label(selected['type']),
        'damage_class': _format_label(selected['damage_class']),
        'power': selected['power'],
        'accuracy': selected['accuracy'],
        'debug_target_version_group_id': version_group_id,
        'debug_selected_version_group_id': selected.get('version_group_id'),
        'debug_selected_row_type': 'versioned' if selected.get('version_group_id') is not None else 'default',
    }

def _resolve_explicit_moves(conn, moves_text, version_group_id):
    if not moves_text or not moves_text.strip():
        return []

    resolved = []
    for token in [t for t in moves_text.split(',') if t.strip()]:
        move_slug = _normalize_move_constant(token)
        if move_slug in ('none', 'move-none'):
            continue
        move_row = conn.execute(
            'select move_id from moves '
            "where lower(replace(move_name, ' ', '-')) = %s "
            'order by case when version_group_id is null then 1 else 0 end, version_group_id desc limit 1',
            (move_slug,)
        ).fetchone()
        if not move_row:
            continue
        details = _resolve_move_details(conn, move_row['move_id'], version_group_id)
        if details:
            resolved.append(details)
    return resolved

def _pick_moveset_version_group(conn, species_id, target_version_group_id):
    rows = conn.execute(
        "select distinct version_group_id from movesets where species_id = %s and learn_method = 'level-up' order by version_group_id asc",
        (species_id,)
    ).fetchall()
    if not rows:
        return None

    values = [int(r['version_group_id']) for r in rows if r['version_group_id'] is not None]
    if not values:
        return None
    if target_version_group_id is None:
        return max(values)

    eligible = [v for v in values if v <= target_version_group_id]
    if eligible:
        return max(eligible)
    return min(values)

def _resolve_levelup_moves(conn, species_id, level, version_group_id):
    if species_id is None:
        return []

    selected_vg = _pick_moveset_version_group(conn, species_id, version_group_id)
    if selected_vg is None:
        return []

    rows = conn.execute(
        'select move_id, learn_level from movesets '
        "where species_id = %s and learn_method = 'level-up' and version_group_id = %s and learn_level <= %s "
        'order by learn_level desc, move_id desc',
        (species_id, selected_vg, int(level or 1))
    ).fetchall()

    seen = set()
    recent_move_ids = []
    for row in rows:
        move_id = row['move_id']
        if move_id in seen:
            continue
        seen.add(move_id)
        recent_move_ids.append(move_id)
        if len(recent_move_ids) == 4:
            break

    resolved = []
    for move_id in recent_move_ids:
        details = _resolve_move_details(conn, move_id, version_group_id)
        if details:
            resolved.append(details)
    return resolved

def get_trainer_parties_by_encounter(conn, trainer_name, game_id=None):
    version_group_id = None
    game_generation = _get_game_generation(conn, game_id=game_id)
    if game_id is not None:
        game_row = conn.execute('select version_group_id from games where game_id = %s', (game_id,)).fetchone()
        if game_row:
            version_group_id = game_row['version_group_id']

    rows = conn.execute(
        'select sp.species_id, t.species_name, st.type1, st.type2, sa.ability1, ss.bst, ss.hp, ss.atk, ss.def, ss.spa, ss.spd, ss.spe, '
        't.iv, t.lvl, t.moves, t.held_item '
        'from trainer_pokemon t '
        'left join species sp on t.species_name = sp.name '
        + _build_generation_patch_join('species_stats', 'ss', 'sp.species_id', '%s')
        + _build_generation_patch_join('species_types', 'st', 'sp.species_id', '%s')
        + _build_generation_patch_join('species_abilities', 'sa', 'sp.species_id', '%s')
        + 'where encounter_name = (%s)',
        (game_generation, game_generation, game_generation, trainer_name)
    ).fetchall()

    party = []
    for row in rows:
        pokemon = dict(row)
        pokemon['debug_game_version_group_id'] = version_group_id
        explicit_moves = _resolve_explicit_moves(conn, pokemon.get('moves'), version_group_id)
        if explicit_moves:
            pokemon['resolved_moves'] = explicit_moves
            pokemon['moves_estimated'] = False
            pokemon['debug_moveset_selected_version_group_id'] = None
            pokemon['debug_moves_source'] = 'trainer_custom'
        else:
            selected_moveset_vg = _pick_moveset_version_group(conn, pokemon.get('species_id'), version_group_id)
            pokemon['resolved_moves'] = _resolve_levelup_moves(
                conn,
                pokemon.get('species_id'),
                pokemon.get('lvl'),
                version_group_id,
            )
            pokemon['moves_estimated'] = len(pokemon['resolved_moves']) > 0
            pokemon['debug_moveset_selected_version_group_id'] = selected_moveset_vg
            pokemon['debug_moves_source'] = 'moveset_generated'
        party.append(pokemon)
    return party

def get_pokemon_trainers_and_badges(conn, run_id, attempt_number, pokemon_id):
    """Get trainers defeated and badges earned for a specific pokemon in a run/attempt."""
    # Get the pokemon details and badges_earned
    has_badges_earned = conn.execute(
        "select 1 from information_schema.columns where table_name = 'pokebank' and column_name = 'badges_earned' limit 1"
    ).fetchone() is not None
    has_trainers_defeated = conn.execute(
        "select 1 from information_schema.columns where table_name = 'pokebank' and column_name = 'trainers_defeated' limit 1"
    ).fetchone() is not None
    
    badges_select = 'pb.badges_earned' if has_badges_earned else "'' as badges_earned"
    trainers_defeated_select = 'pb.trainers_defeated' if has_trainers_defeated else "'' as trainers_defeated"
    
    pokemon = conn.execute(
        f'select pb.pokemon_id, pb.species_id, pb.run_id, pb.attempt_id, {badges_select}, {trainers_defeated_select} '
        f'from pokebank pb '
        f'join attempts a on pb.attempt_id = a.attempt_id '
        f'where pb.pokemon_id = %s and pb.run_id = %s and a.attempt_number = %s',
        (pokemon_id, run_id, attempt_number)
    ).fetchone()
    
    if not pokemon:
        return {'error': 'Pokemon not found'}
    
    pokemon_dict = dict(pokemon)

    defeated_trainer_ids = sorted(_parse_id_set(pokemon_dict.get('trainers_defeated')))
    total_defeated = len(defeated_trainer_ids)

    rival_ids = set()
    boss_ids = set()
    if defeated_trainer_ids:
        placeholders = ','.join(['%s'] * len(defeated_trainer_ids))
        boss_rows = conn.execute(
            f'select trainer_id, event_type from event_bosses where trainer_id in ({placeholders})',
            defeated_trainer_ids
        ).fetchall()
        for row in boss_rows:
            tid = int(row['trainer_id'])
            etype = (row['event_type'] or '').strip().lower()
            if etype == 'rival':
                rival_ids.add(tid)
            else:
                boss_ids.add(tid)

    rivals_defeated = len(rival_ids)
    bosses_defeated = len(boss_ids)
    trainers_defeated = max(total_defeated - rivals_defeated - bosses_defeated, 0)
    
    # Parse badges earned
    badges_earned_str = pokemon_dict.get('badges_earned') or ''
    badge_ids = []
    if badges_earned_str:
        try:
            # Try to parse as JSON array
            badge_ids = json.loads(badges_earned_str)
        except (json.JSONDecodeError, TypeError):
            # Try comma-separated string
            if isinstance(badges_earned_str, str):
                badge_ids = [int(b.strip()) for b in badges_earned_str.split(',') if b.strip().isdigit()]
    
    # Get badge details
    badges = []
    if badge_ids:
        placeholders = ','.join(['%s'] * len(badge_ids))
        badge_rows = conn.execute(
            f'select badge_id, badge_name from badges where badge_id in ({placeholders})',
            badge_ids
        ).fetchall()
        badges = [dict(b) for b in badge_rows]
    
    return {
        'pokemon_id': pokemon_id,
        'trainers_defeated': trainers_defeated,
        'trainers_defeated_count': trainers_defeated,
        'bosses_defeated_count': bosses_defeated,
        'rivals_defeated_count': rivals_defeated,
        'total_defeated_count': total_defeated,
        'badges_earned': badges,
        'badges_count': len(badges)
    }

def get_badges_by_ids(conn, badge_ids):
    cleaned = [int(b) for b in badge_ids if str(b).isdigit()]
    if not cleaned:
        return []

    placeholders = ','.join(['%s'] * len(cleaned))
    rows = conn.execute(
        f'select badge_id, badge_name from badges where badge_id in ({placeholders}) order by badge_id asc',
        cleaned
    ).fetchall()
    return [dict(r) for r in rows]

if __name__ == '__main__':
    import os
    import psycopg2
    raw = psycopg2.connect(os.environ['DATABASE_URL'])
    conn = wrap_conn(raw)

    runs = [dict(x) for x in get_runs(conn)]
    state['active_run_id'] = 1
    m_species_id = 1
    m_location_id = 8
    m_nickname = 'Arbithor'
    m_status = 'Captured'
    m_shiny = 'False'
    state['active_attempt_id'] = 2
    starter = 'Grass'
    set_active_game(conn, 10)

    script = [dict(x) for x in get_script(conn, starter)]
    trainers = [dict(x) for x in get_trainers_by_location(conn, m_location_id)]
    trainer_party = [dict(x) for x in get_trainer_parties_by_encounter(conn, trainers[0]['trainer_name'])]
    graveyard = get_graveyard(conn)
    pokebank = get_pokebank(conn)
    # encounter_pool = [dict(x) for x in get_encounter_pool(script[15]['event_id'])]
    # encounter_pool_names = [get_pokemon_name_from_id(x['species_id']) for x in encounter_pool]
    location_dict = {}
    for event in script:
        if event['event_type'] == 'Location':
            location_dict[f'Location: {get_location_by_id(conn, event["event_id"])}'] = set([get_pokemon_name_from_id(conn, x['species_id']) for x in get_encounter_pool(conn, event['event_id'], 10)])
    box = get_box(conn)
    get_party(conn)
    print(f'party = {active_party}')
    swap_party_slots(  {'party_slot': 1, 'pokemon_id': active_party[1]}, {'party_slot': 4, 'pokemon_id': active_party[4]} )
    print(f'party = {active_party}')
    swap_party_slots( {'party_slot': 2, 'pokemon_id': active_party[2]}, {'party_slot': '', 'pokemon_id': 26} )
    print(f'party = {active_party}')
    delete_run(conn, 1)
    # run = get_run_by_id(conn,1)
    species = get_species_search(conn, 'ew')
    get_latest_attempt(conn)
