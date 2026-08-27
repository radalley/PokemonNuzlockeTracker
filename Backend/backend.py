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
_schema_ready = {'auth': False, 'badge': False, 'bonus_locations': False, 'contact_reports': False}
active_party = {
    1:'',
    2:'',
    3:'',
    4:'',
    5:'',
    6:''
}

BADGE_DEFINITIONS = (
    (1, 'Boulder Badge', 'Kanto'),
    (2, 'Cascade Badge', 'Kanto'),
    (3, 'Thunder Badge', 'Kanto'),
    (4, 'Rainbow Badge', 'Kanto'),
    (5, 'Soul Badge', 'Kanto'),
    (6, 'Marsh Badge', 'Kanto'),
    (7, 'Volcano Badge', 'Kanto'),
    (8, 'Earth Badge', 'Kanto'),
    (9, 'Zephyr Badge', 'Johto'),
    (10, 'Hive Badge', 'Johto'),
    (11, 'Plain Badge', 'Johto'),
    (12, 'Fog Badge', 'Johto'),
    (13, 'Storm Badge', 'Johto'),
    (14, 'Mineral Badge', 'Johto'),
    (15, 'Glacier Badge', 'Johto'),
    (16, 'Rising Badge', 'Johto'),
    (17, 'Stone Badge', 'Hoenn'),
    (18, 'Knuckle Badge', 'Hoenn'),
    (19, 'Dynamo Badge', 'Hoenn'),
    (20, 'Heat Badge', 'Hoenn'),
    (21, 'Balance Badge', 'Hoenn'),
    (22, 'Feather Badge', 'Hoenn'),
    (23, 'Mind Badge', 'Hoenn'),
    (24, 'Rain Badge', 'Hoenn'),
    (25, 'Coal Badge', 'Sinnoh'),
    (26, 'Forest Badge', 'Sinnoh'),
    (27, 'Cobble Badge', 'Sinnoh'),
    (28, 'Fen Badge', 'Sinnoh'),
    (29, 'Relic Badge', 'Sinnoh'),
    (30, 'Mine Badge', 'Sinnoh'),
    (31, 'Icicle Badge', 'Sinnoh'),
    (32, 'Beacon Badge', 'Sinnoh'),
    (33, 'Trio Badge', 'Unova'),
    (34, 'Basic Badge', 'Unova'),
    (35, 'Insect Badge', 'Unova'),
    (36, 'Bolt Badge', 'Unova'),
    (37, 'Quake Badge', 'Unova'),
    (38, 'Jet Badge', 'Unova'),
    (39, 'Freeze Badge', 'Unova'),
    (40, 'Legend Badge', 'Unova'),
    (41, 'Toxic Badge', 'Unova'),
    (42, 'Wave Badge', 'Unova'),
)

EVENT_BADGE_MAPPINGS = (
    ((1, 2, 3, 4, 7, 10), 'pewter city gym', 1),
    ((1, 2, 3, 4, 7, 10), 'cerulean city gym', 2),
    ((1, 2, 3, 4, 7, 10), 'vermilion city gym', 3),
    ((1, 2, 3, 4, 7, 10), 'vermillion city gym', 3),
    ((1, 2, 3, 4, 7, 10), 'celadon city gym', 4),
    ((1, 2, 3, 4, 7, 10), 'fuschia city gym', 5),
    ((1, 2, 3, 4, 7, 10), 'fuchsia city gym', 5),
    ((1, 2, 3, 4, 7, 10), 'saffron city gym', 6),
    ((1, 2, 3, 4, 7, 10), 'cinnabar island gym', 7),
    ((1, 2, 3, 4, 7, 10), 'viridian city gym', 8),
    ((3, 4, 10), 'violet city gym', 9),
    ((3, 4, 10), 'azalea town gym', 10),
    ((3, 4, 10), 'goldenrod city gym', 11),
    ((3, 4, 10), 'ecruteak city gym', 12),
    ((3, 4, 10), 'cianwood city gym', 13),
    ((3, 4, 10), 'olivine city gym', 14),
    ((3, 4, 10), 'mahogany town gym', 15),
    ((3, 4, 10), 'blackthorn city gym', 16),
    ((5, 6), 'rustboro city gym', 17),
    ((5, 6), 'dewford town gym', 18),
    ((5, 6), 'mauville city gym', 19),
    ((5, 6), 'lavaridge town gym', 20),
    ((5, 6), 'lavaridge city gym', 20),
    ((5, 6), 'petalburg city gym', 21),
    ((5, 6), 'fortree city gym', 22),
    ((5, 6), 'mossdeep city gym', 23),
    ((5, 6), 'sootopolis city gym', 24),
    ((8, 9), 'oreburgh city gym', 25),
    ((8, 9), 'eterna city gym', 26),
    ((8, 9), 'veilstone city gym', 27),
    ((8, 9), 'pastoria city gym', 28),
    ((8, 9), 'hearthome city gym', 29),
    ((8, 9), 'canalave city gym', 30),
    ((8, 9), 'snowpoint city gym', 31),
    ((8, 9), 'sunyshore city gym', 32),
    ((11,), 'striaton city gym', 33),
    ((11,), 'nacrene city gym', 34),
    ((11, 14), 'castelia city gym', 35),
    ((11, 14), 'nimbasa city gym', 36),
    ((11, 14), 'driftveil city gym', 37),
    ((11, 14), 'mistralton city gym', 38),
    ((11,), 'icirrus city gym', 39),
    ((11, 14), 'opelucid city gym', 40),
    ((14,), 'aspertia city gym', 34),
    ((14,), 'virbank city gym', 41),
    ((14,), 'humilau city gym', 42),
)

def get_games(conn):
    cur = _cursor(conn)
    cur.execute(
        "SELECT g.game_id, g.name, g.game_tag, g.generation, g.version_group_id, "
        "g.base_game_id, g.is_rom_hack, base.name as base_game_name "
        "FROM games g LEFT JOIN games base ON base.game_id = g.base_game_id "
        "WHERE g.valid_game = 'valid'"
    )
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

def _build_generation_patch_join(table_name, join_alias, species_expr, generation_expr, version_group_expr=None):
    """Pick the species row for a game context.

    Rows tagged with a version_group_id are exact overrides for that version
    group (a ROM hack's rewrites) and win outright when the caller supplies
    one; untagged rows keep the generation-based semantics. Callers without
    game context never see override rows.
    """
    if version_group_expr is None:
        vg_filter = 'x.version_group_id is null'
    else:
        vg_filter = (
            f'(x.version_group_id = {version_group_expr} '
            f'or (x.version_group_id is null '
            f'and (coalesce(x.generation, 0) = 0 or x.generation >= coalesce({generation_expr}, 9999))))'
        )
    generation_filter = (
        f'(coalesce(x.generation, 0) = 0 or x.generation >= coalesce({generation_expr}, 9999))'
        if version_group_expr is None else 'true'
    )
    return (
        f'left join lateral (\n'
        f'  select * from {table_name} x\n'
        f'  where x.species_id = {species_expr}\n'
        f'    and {vg_filter}\n'
        f'    and {generation_filter}\n'
        f'  order by case when x.version_group_id is not null then 0 else 1 end,\n'
        f'           case when coalesce(x.generation, 0) = 0 then 1 else 0 end, x.generation asc\n'
        f'  limit 1\n'
        f') {join_alias} on true\n'
    )

def set_active_game(conn, game):
    state['active_game_id'] = game
    state['version_group_id'] = conn.execute('select version_group_id from games where game_id = (%s)', (game,)).fetchone()['version_group_id']

def create_run(conn, name, game_id, user_id=None):
    _ensure_auth_schema(conn)
    if game_id is None:
        raise ValueError('game_id is required to create a run')
    row = conn.execute(
        "insert into runs (game_id, name, user_id, last_opened_at, last_opened_attempt_number) "
        "values (%s,%s,%s,current_timestamp,1) returning run_id",
        (game_id, name, user_id)
    ).fetchone()
    conn.commit()
    set_active_run(row['run_id'])
    new_attempt(conn)
    return row['run_id']

def get_party_for_attempts_bulk(conn, attempt_ids):
    """
    Batched equivalent of calling get_party_for_attempt() once per attempt_id.

    A single attempt_ids list can span multiple different games (a user's
    runs aren't all the same generation), so this can't patch stats/types/
    abilities using one shared generation value the way a single-attempt
    query can. Instead it joins each row back through attempts -> runs ->
    games so every row is patched using *its own* attempt's generation.

    Returns {attempt_id: [party_rows]}.
    """
    _ensure_badge_schema(conn)
    attempt_ids = [a for a in attempt_ids if a is not None]
    if not attempt_ids:
        return {}
    placeholders = ','.join(['%s'] * len(attempt_ids))
    badges_select = ', ' + _pokemon_badges_text_expr('pb')
    rows = conn.execute(
        'select p.attempt_id, p.party_slot, p.pokemon_id, pb.species_id, s.name as species_name, pb.nickname, pb.shiny, '
        'pb.level_met, st.type1, st.type2, sa.ability1, sa.ability2, sa.ability3, ss.bst, ss.hp, ss.atk, ss.def, ss.spa, ss.spd, ss.spe'
        + badges_select + ' '
        'from party p '
        'join pokebank pb on p.pokemon_id = pb.pokemon_id '
        'join species s on pb.species_id = s.species_id '
        'join attempts patt on p.attempt_id = patt.attempt_id '
        'join runs prun on patt.run_id = prun.run_id '
        'left join games pgame on nullif(prun.game_id::text, \'\')::integer = nullif(pgame.game_id::text, \'\')::integer '
        + _build_generation_patch_join('species_stats', 'ss', 'pb.species_id', 'pgame.generation', 'pgame.version_group_id')
        + _build_generation_patch_join('species_types', 'st', 'pb.species_id', 'pgame.generation', 'pgame.version_group_id')
        + _build_generation_patch_join('species_abilities', 'sa', 'pb.species_id', 'pgame.generation', 'pgame.version_group_id')
        + f'where p.attempt_id in ({placeholders}) '
        + 'order by p.attempt_id, p.party_slot',
        tuple(attempt_ids)
    ).fetchall()

    grouped = {}
    for row in rows:
        grouped.setdefault(row['attempt_id'], []).append(row)
    return grouped


def get_attempt_session_stats_bulk(conn, attempt_ids):
    """
    Batched equivalent of calling get_attempt_session_stats() once per
    attempt_id. Returns {attempt_id: {badges_earned, badge_ids,
    trainers_defeated, pokemon_caught, pokemon_dead, pokemon_missed}}
    (same shape as get_attempt_session_stats minus run_id/attempt_number,
    which the caller already has).
    """
    _ensure_badge_schema(conn)
    attempt_ids = [a for a in attempt_ids if a is not None]
    if not attempt_ids:
        return {}
    placeholders = ','.join(['%s'] * len(attempt_ids))

    buckets = {
        attempt_id: {
            'pokemon_caught': 0, 'pokemon_dead': 0, 'pokemon_missed': 0,
            'trainers_defeated': 0, 'badge_ids': set(),
        }
        for attempt_id in attempt_ids
    }

    status_rows = conn.execute(
        f'select attempt_id, status, count(*) as count from pokebank '
        f'where attempt_id in ({placeholders}) group by attempt_id, status',
        tuple(attempt_ids)
    ).fetchall()
    for row in status_rows:
        bucket = buckets.get(row['attempt_id'])
        if bucket is None:
            continue
        status = (row['status'] or '').strip().lower()
        count = int(row['count'] or 0)
        if status == 'captured':
            bucket['pokemon_caught'] = count
        elif status == 'dead':
            bucket['pokemon_dead'] = count
        elif status == 'missed':
            bucket['pokemon_missed'] = count

    trainers_rows = conn.execute(
        f'select attempt_id, count(distinct trainer_id) as count from trainers_defeated '
        f'where attempt_id in ({placeholders}) group by attempt_id',
        tuple(attempt_ids)
    ).fetchall()
    for row in trainers_rows:
        bucket = buckets.get(row['attempt_id'])
        if bucket is not None:
            bucket['trainers_defeated'] = int(row['count'] or 0)

    badge_rows = conn.execute(
        f'select attempt_id, badge_id from attempt_badges where attempt_id in ({placeholders})',
        tuple(attempt_ids)
    ).fetchall()
    for row in badge_rows:
        bucket = buckets.get(row['attempt_id'])
        if bucket is not None:
            bucket['badge_ids'].add(int(row['badge_id']))

    return {
        attempt_id: {
            'badges_earned': len(bucket['badge_ids']),
            'badge_ids': sorted(bucket['badge_ids']),
            'trainers_defeated': bucket['trainers_defeated'],
            'pokemon_caught': bucket['pokemon_caught'],
            'pokemon_dead': bucket['pokemon_dead'],
            'pokemon_missed': bucket['pokemon_missed'],
        }
        for attempt_id, bucket in buckets.items()
    }


def get_runs(conn, user_id=None):
    _ensure_auth_schema(conn)
    query = (
        'SELECT '
        '  r.run_id, '
        '  r.game_id, '
        '  g.name as game_name, '
        '  g.game_tag, '
        '  g.generation, '
        '  g.version_group_id, '
        '  r.name as run_name, '
        '  a.latest_attempt, '
        '  a.latest_attempt_id, '
        '  a.total_attempts, '
        '  r.created_at, '
        '  coalesce(r.victory, \'false\') as victory_item, '
        '  r.beaten_at '
        'FROM runs r '
        'LEFT JOIN games g on nullif(r.game_id::text, \'\')::integer = nullif(g.game_id::text, \'\')::integer '
        'LEFT JOIN ('
        '  SELECT DISTINCT ON (run_id) run_id, attempt_id as latest_attempt_id, attempt_number as latest_attempt, '
        '    count(*) OVER (PARTITION BY run_id) as total_attempts '
        '  FROM attempts '
        '  ORDER BY run_id, attempt_number DESC'
        ') a ON r.run_id = a.run_id '
    )
    params = []
    if user_id is not None:
        query += 'WHERE nullif(r.user_id::text, \'\')::integer = %s '
        params.append(user_id)
    query += 'ORDER BY g.game_id ASC, r.run_id DESC'
    runs = conn.execute(query, params).fetchall()

    attempt_ids = [row['latest_attempt_id'] for row in runs if row['latest_attempt_id'] is not None]
    party_by_attempt = get_party_for_attempts_bulk(conn, attempt_ids)
    stats_by_attempt = get_attempt_session_stats_bulk(conn, attempt_ids)

    enriched_runs = []
    for row in runs:
        run_data = dict(row)
        latest_attempt = run_data.get('latest_attempt')
        attempt_id = run_data.pop('latest_attempt_id', None)
        if attempt_id is not None:
            party_rows = party_by_attempt.get(attempt_id, [])
            run_data['latest_party'] = [dict(member) for member in party_rows]
            bulk_stats = stats_by_attempt.get(attempt_id)
            if bulk_stats:
                run_data['latest_attempt_stats'] = {
                    'run_id': run_data['run_id'],
                    'attempt_number': latest_attempt,
                    **bulk_stats,
                }
                run_data['latest_attempt_badges'] = bulk_stats['badge_ids']
            else:
                run_data['latest_attempt_stats'] = None
                run_data['latest_attempt_badges'] = []
        else:
            run_data['latest_party'] = []
            run_data['latest_attempt_stats'] = None
            run_data['latest_attempt_badges'] = []
        enriched_runs.append(run_data)

    return enriched_runs

def get_run_menu_summary(conn, user_id):
    _ensure_auth_schema(conn)
    has_runs = conn.execute(
        'select 1 from runs where nullif(user_id::text, \'\')::integer = %s limit 1',
        (user_id,)
    ).fetchone() is not None
    if not has_runs:
        return {'has_runs': False, 'latest_run': None}

    row = conn.execute(
        'SELECT '
        '  r.run_id, r.game_id, g.name as game_name, g.game_tag, g.generation, g.version_group_id, '
        '  r.name as run_name, r.created_at, coalesce(r.victory, \'false\') as victory_item, r.beaten_at, '
        '  coalesce(r.last_opened_attempt_number, a.latest_attempt) as continuation_attempt, '
        '  a.latest_attempt, a.total_attempts '
        'FROM runs r '
        'LEFT JOIN games g on nullif(r.game_id::text, \'\')::integer = nullif(g.game_id::text, \'\')::integer '
        'LEFT JOIN ('
        '  SELECT run_id, max(attempt_number) as latest_attempt, count(*) as total_attempts '
        '  FROM attempts GROUP BY run_id'
        ') a ON r.run_id = a.run_id '
        'WHERE nullif(r.user_id::text, \'\')::integer = %s '
        'ORDER BY r.last_opened_at DESC NULLS LAST, r.created_at DESC NULLS LAST, r.run_id DESC '
        'LIMIT 1',
        (user_id,)
    ).fetchone()
    if not row:
        return {'has_runs': True, 'latest_run': None}

    run_data = dict(row)
    attempt_number = run_data.get('continuation_attempt') or run_data.get('latest_attempt')
    if attempt_number is None:
        return {'has_runs': True, 'latest_run': None}

    party = get_party_for_attempt(conn, run_data['run_id'], attempt_number)
    attempt_row = conn.execute(
        'select attempt_id from attempts where run_id = %s and attempt_number = %s',
        (run_data['run_id'], attempt_number)
    ).fetchone()
    run_data['party'] = [dict(member) for member in party]
    run_data['badges'] = sorted(
        _get_attempt_badge_ids(
            conn,
            attempt_row['attempt_id'],
            run_id=run_data['run_id'],
            fallback_to_pokebank=True
        )
    ) if attempt_row else []
    run_data['attempt_number'] = int(attempt_number)
    return {'has_runs': True, 'latest_run': run_data}

def mark_run_opened(conn, run_id, user_id, attempt_number):
    _ensure_auth_schema(conn)
    updated = conn.execute(
        'update runs set last_opened_at = current_timestamp, last_opened_attempt_number = %s '
        'where run_id = %s and nullif(user_id::text, \'\')::integer = %s '
        'and exists ('
        '  select 1 from attempts where attempts.run_id = runs.run_id and attempts.attempt_number = %s'
        ')',
        (attempt_number, run_id, user_id, attempt_number)
    )
    conn.commit()
    return updated.rowcount == 1

def get_run_by_id(conn, run_id, attempt_number, user_id=None):
    # return conn.execute('select run_id, runs.name, runs.game_id, games.name as game_name from runs left join games on runs.game_id = games.game_id where runs.run_id = (%s)',(run_id,)).fetchone()
    _ensure_auth_schema(conn)
    query = (
        'select run.run_id, run.name, run.game_id, run.game_name, run.version_group_id, run.generation, run.base_game_id, run.base_game_name, run.s_ref, run.b_ref, run.pdb_ref, attempts.starter '
        'from ('
        '  select run_id, runs.name, runs.game_id, runs.user_id, games.name as game_name, games.version_group_id, games.generation, games.base_game_id, '
        '  (select b.name from games b where b.game_id = games.base_game_id) as base_game_name, games.s_ref, games.b_ref, games.pdb_ref '
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
        conn.execute('delete from trainers_defeated where attempt_id = (%s)',(attempt_id,))
    conn.commit()

def set_active_run(run_id):
    state['active_run_id'] = run_id

def new_attempt(conn, ):
    attempts = conn.execute('select attempt_number from attempts where run_id = %s', (state["active_run_id"],)).fetchall()
    if len(attempts) == 0:
        conn.execute("insert into attempts (run_id, attempt_number, starter) values (%s,%s,%s)",
                    (state['active_run_id'], 1, 'Fire') )
        state['active_attempt_id'] = 1
    else:
        new_attempt_number = attempts[::-1][0]['attempt_number'] + 1
        conn.execute("insert into attempts (run_id, attempt_number, starter) values (%s,%s,%s)",
                    (state['active_run_id'], new_attempt_number, 'Fire') )
        set_active_attempt(new_attempt_number)
    conn.commit()

def get_attempts(conn):
    return conn.execute(f'select attempt_number from attempts where run_id = {state["active_run_id"]}').fetchall()

def get_attempts_for_run(conn, run_id):
    return conn.execute(
        'select attempt_number, outcome, ended_at from attempts '
        'where run_id = %s order by attempt_number asc',
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
    conn.execute(
        'insert into attempts (run_id, attempt_number, starter) values (%s, %s, %s)',
        (run_id, new_num, 'Fire')
    )
    conn.commit()
    return new_num

def end_attempt(conn, run_id, attempt_number, outcome='dead', trainer_id=None, note=None):
    """End an attempt, recording how it died.

    trainer_id names the killer when defeat was declared from a trainer
    battle; note carries free text for wild/other deaths. Raises ValueError
    on a missing attempt, an already-ended attempt, or an unknown trainer.
    """
    if outcome not in ('dead', 'won'):
        raise ValueError(f'Unknown outcome {outcome!r}')
    if note is not None and not isinstance(note, str):
        note = str(note)
    attempt = conn.execute(
        'select attempt_id, outcome from attempts where run_id = %s and attempt_number = %s',
        (run_id, attempt_number)
    ).fetchone()
    if not attempt:
        raise ValueError(f'Attempt {attempt_number} not found for run {run_id}')
    if attempt['outcome']:
        raise ValueError(f'Attempt {attempt_number} already ended ({attempt["outcome"]})')
    if trainer_id is not None:
        # The killer must belong to the run's game world, not merely exist.
        trainer = conn.execute(
            'select tp.trainer_id from trainer_pool tp '
            'join runs r on nullif(r.run_id::text, \'\')::integer = %s '
            'join games g on nullif(r.game_id::text, \'\')::integer = g.game_id '
            'where tp.trainer_id = %s and tp.version_group_id = g.version_group_id',
            (run_id, trainer_id)
        ).fetchone()
        if not trainer:
            raise ValueError(f'Trainer {trainer_id} does not belong to this run\'s game')
    # The outcome guard in the WHERE clause makes concurrent declarations
    # first-writer-wins instead of last-writer-overwrites.
    updated = conn.execute(
        'update attempts set outcome = %s, ended_at = current_timestamp, '
        'ended_by_trainer_id = %s, death_note = %s '
        'where run_id = %s and attempt_number = %s and outcome is null',
        (outcome, trainer_id, (note or '').strip()[:500] or None, run_id, attempt_number)
    )
    conn.commit()
    if updated.rowcount != 1:
        raise ValueError(f'Attempt {attempt_number} already ended')
    return {'success': True, 'outcome': outcome}

def reopen_attempt(conn, run_id, attempt_number):
    """Undo an accidental end-of-attempt declaration."""
    attempt = conn.execute(
        'select 1 from attempts where run_id = %s and attempt_number = %s',
        (run_id, attempt_number)
    ).fetchone()
    if not attempt:
        raise ValueError(f'Attempt {attempt_number} not found for run {run_id}')
    updated = conn.execute(
        'update attempts set outcome = null, ended_at = null, '
        'ended_by_trainer_id = null, death_note = null '
        'where run_id = %s and attempt_number = %s and outcome is not null',
        (run_id, attempt_number)
    )
    conn.commit()
    return updated.rowcount == 1

def get_attempt_summary(conn, run_id, attempt_number):
    """Everything the post-mortem screen shows for one attempt."""
    _ensure_badge_schema(conn)
    run = get_run_by_id(conn, run_id, attempt_number)
    if not run:
        return None
    attempt = conn.execute(
        'select attempt_id, attempt_number, starter, started_at, outcome, '
        'ended_at, ended_by_trainer_id, death_note '
        'from attempts where run_id = %s and attempt_number = %s',
        (run_id, attempt_number)
    ).fetchone()
    if not attempt:
        return None
    attempt_dict = dict(attempt)
    attempt_id = attempt_dict.pop('attempt_id')

    killer = None
    if attempt_dict.get('ended_by_trainer_id') is not None:
        killer_row = conn.execute(
            'select tp.trainer_id, tp.trainer_name, tp.trainer_class, tp.trainer_pic, '
            'cl.canonical_location_name as location_name '
            'from trainer_pool tp '
            'left join canon_locations cl on cl.canonical_location_id = tp.canonical_location_id '
            'where tp.trainer_id = %s',
            (attempt_dict['ended_by_trainer_id'],)
        ).fetchone()
        killer = dict(killer_row) if killer_row else None

    badges = [dict(r) for r in conn.execute(
        'select ab.badge_id, b.badge_name, ab.earned_at '
        'from attempt_badges ab join badges b on b.badge_id = ab.badge_id '
        'where ab.attempt_id = %s order by ab.earned_at asc',
        (attempt_id,)
    ).fetchall()]

    deaths = [dict(r) for r in conn.execute(
        'select pb.pokemon_id, pb.species_id, s.name as species_name, pb.nickname, '
        'pb.level_met, cl.canonical_location_name as location_name '
        'from pokebank pb '
        'left join species s on s.species_id = pb.species_id '
        'left join canon_locations cl on cl.canonical_location_id = pb.canonical_location_id '
        "where pb.run_id = %s and pb.attempt_id = %s and pb.status = 'Dead' "
        'order by pb.pokemon_id asc',
        (run_id, attempt_id)
    ).fetchall()]

    survivors = [dict(r) for r in conn.execute(
        'select pb.pokemon_id, pb.species_id, s.name as species_name, pb.nickname, '
        'p.party_slot '
        'from pokebank pb '
        'left join species s on s.species_id = pb.species_id '
        'left join party p on p.pokemon_id = pb.pokemon_id and p.attempt_id = %s '
        "where pb.run_id = %s and pb.attempt_id = %s and pb.status = 'Captured' "
        'order by p.party_slot asc nulls last, pb.pokemon_id asc',
        (attempt_id, run_id, attempt_id)
    ).fetchall()]

    counts = dict(conn.execute(
        'select '
        "count(*) filter (where status = 'Captured') as captured, "
        "count(*) filter (where status = 'Missed') as missed, "
        "count(*) filter (where status = 'Dead') as dead, "
        '(select count(distinct td.trainer_id) from trainers_defeated td where td.run_id = %s and td.attempt_id = %s) as trainers_defeated '
        'from pokebank where run_id = %s and attempt_id = %s',
        (run_id, attempt_id, run_id, attempt_id)
    ).fetchone())

    return {
        'run': {k: run[k] for k in ('run_id', 'name', 'game_id', 'game_name', 'generation') if k in run.keys()},
        'attempt': attempt_dict,
        'killer': killer,
        'badges': badges,
        'deaths': deaths,
        'survivors': survivors,
        'counts': counts,
    }

def get_latest_attempt(conn):
    return conn.execute(f'select attempt_id from attempts where run_id = {state["active_run_id"]} order by attempt_id desc limit 1').fetchone()

def set_active_attempt(attempt):
    state['active_attempt_id'] = attempt

def get_pokebank(conn):
    return conn.execute(f'select pokemon_id, species_id, canonical_location_id as location_id, level_met, nickname, status, shiny, storage, party_slot, bonus_location, bonus_note from pokebank').fetchall()

def get_pokebank_feed_for_user(conn, user_id, limit=360):
    _ensure_badge_schema(conn)
    badges_select = _pokemon_badges_text_expr('pb')

    rows = conn.execute(
        f'select pb.species_id, pb.nickname, {badges_select}, pb.shiny, pb.status '
        f'from pokebank pb '
        f'join runs r on nullif(pb.run_id::text, \'\')::integer = nullif(r.run_id::text, \'\')::integer '
        f'where r.user_id = %s and (pb.status = %s or pb.status = %s) '
        f'order by case when pb.species_id = 260 and upper(coalesce(pb.nickname, \'\')) = \'MAGNUS\' then 0 else 1 end, RANDOM() '
        f'limit %s',
        (user_id, 'Captured', 'Dead', min(limit, 500))
    ).fetchall()
    return [dict(r) for r in rows]

def get_graveyard(conn):
    return conn.execute("select pokemon_id, species_id, canonical_location_id as location_id, level_met, nickname, status, shiny, storage, party_slot, bonus_location, bonus_note from pokebank where status = 'Dead'").fetchall()

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
    return conn.execute("select pokemon_id, species_id, canonical_location_id as location_id, level_met, nickname, status, shiny, storage, party_slot, bonus_location, bonus_note from pokebank where attempt_id = (%s) and run_id = (%s) and status = 'Captured'", (state['active_attempt_id'], state['active_run_id'],)).fetchall()

def get_species_search(conn, name):
    return conn.execute("select name, species_id, valid from species where name like (%s) and valid = 'true'",('%'+name+'%',)).fetchall()

def get_species_summary(conn, species_id, game_id=None):
    game_generation = _get_game_generation(conn, game_id=game_id)
    row = conn.execute(
        'select s.species_id, s.name, st.type1, st.type2, ss.bst, ss.hp, ss.atk, ss.def, ss.spa, ss.spd, ss.spe, '
        's.has_gender, s.has_female, s.default_gender, s.one_gender, '
        'sa.ability1, sa.ability2, sa.ability3 '
        'from species s '
        + _build_generation_patch_join('species_stats', 'ss', 's.species_id', '%s')
        + _build_generation_patch_join('species_types', 'st', 's.species_id', '%s')
        + _build_generation_patch_join('species_abilities', 'sa', 's.species_id', '%s')
        + 'where s.species_id = %s',
        (game_generation, game_generation, game_generation, species_id)
    ).fetchone()
    return dict(row) if row else None

def get_evolutions(conn, species_id):
    return conn.execute(
        'select e.to_species_id, s.name from evolutions e '
        'join species s on e.to_species_id = s.species_id '
        'where e.from_species_id = (%s)',
        (species_id,)
    ).fetchall()

def get_species_forms(conn, species_id):
    # Check if this species is a parent (has child forms)
    children = conn.execute(
        'select s.species_id, s.name from forms f '
        'join species s on s.species_id = f.child_species_id '
        'where f.parent_species_id = %s '
        'order by f.form_id',
        (species_id,)
    ).fetchall()
    if children:
        parent = conn.execute(
            'select species_id, name from species where species_id = %s',
            (species_id,)
        ).fetchone()
        result = [{'species_id': parent['species_id'], 'name': parent['name'], 'is_parent': True}]
        result += [{'species_id': r['species_id'], 'name': r['name'], 'is_parent': False} for r in children]
        return result
    # Check if this species is a child form
    parent_row = conn.execute(
        'select f.parent_species_id, s.name as parent_name from forms f '
        'join species s on s.species_id = f.parent_species_id '
        'where f.child_species_id = %s',
        (species_id,)
    ).fetchone()
    if parent_row:
        parent_id = parent_row['parent_species_id']
        siblings = conn.execute(
            'select s.species_id, s.name from forms f '
            'join species s on s.species_id = f.child_species_id '
            'where f.parent_species_id = %s '
            'order by f.form_id',
            (parent_id,)
        ).fetchall()
        result = [{'species_id': parent_id, 'name': parent_row['parent_name'], 'is_parent': True}]
        result += [{'species_id': r['species_id'], 'name': r['name'], 'is_parent': False} for r in siblings]
        return result
    return []

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
    if _schema_ready['bonus_locations']:
        return
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
    _schema_ready['bonus_locations'] = True

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
        'select cl.canonical_location_name as canonical_name, el.sort_order, coalesce(el.secondary_sort_order, 0) as secondary_sort_order, el.event_type '
        'from event_locations el '
        'join canon_locations cl on nullif(cl.canonical_location_id::text, \'\')::integer = nullif(el.canonical_location_id::text, \'\')::integer '
        'where el.canonical_location_id = %s and el.version_group_id = %s '
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
            'where run_id = %s and attempt_id = %s and canonical_location_id = %s and coalesce(bonus_location, 0) = %s',
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
        'where run_id = %s and attempt_id = %s and canonical_location_id = %s and coalesce(bonus_location, 0) = %s',
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
    _ensure_badge_schema(conn)
    row = conn.execute(
        'select attempt_id from attempts where run_id = %s and attempt_number = %s',
        (run_id, attempt_number)
    ).fetchone()
    if not row:
        return []
    attempt_id = row['attempt_id']
    game_generation = _get_game_generation(conn, run_id=run_id)
    run_vg_row = conn.execute(
        'select g.version_group_id from runs r '
        'join games g on nullif(r.game_id::text, \'\')::integer = nullif(g.game_id::text, \'\')::integer '
        'where nullif(r.run_id::text, \'\')::integer = %s', (run_id,)
    ).fetchone()
    run_vg = run_vg_row['version_group_id'] if run_vg_row else None

    badges_select = ', ' + _pokemon_badges_text_expr('pb')
    return conn.execute(
        'select p.party_slot, p.pokemon_id, pb.species_id, s.name as species_name, pb.nickname, pb.shiny, '
        'pb.level_met, st.type1, st.type2, sa.ability1, sa.ability2, sa.ability3, ss.bst, ss.hp, ss.atk, ss.def, ss.spa, ss.spd, ss.spe '
        + badges_select + ' '
        'from party p '
        'join pokebank pb on p.pokemon_id = pb.pokemon_id '
        'join species s on pb.species_id = s.species_id '
        + _build_generation_patch_join('species_stats', 'ss', 'pb.species_id', '%s', '%s')
        + _build_generation_patch_join('species_types', 'st', 'pb.species_id', '%s', '%s')
        + _build_generation_patch_join('species_abilities', 'sa', 'pb.species_id', '%s', '%s')
        + 'where p.attempt_id = %s '
        + 'order by p.party_slot',
        (run_vg, game_generation, run_vg, game_generation, run_vg, game_generation, attempt_id)
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

def _has_column(conn, table_name, column_name):
    return conn.execute(
        'select 1 from information_schema.columns '
        'where table_name = %s and column_name = %s limit 1',
        (table_name, column_name)
    ).fetchone() is not None

def _has_constraint(conn, table_name, constraint_name):
    return conn.execute(
        'select 1 from information_schema.table_constraints '
        'where table_schema = current_schema() and table_name = %s and constraint_name = %s limit 1',
        (table_name, constraint_name)
    ).fetchone() is not None

def _ensure_badge_schema(conn):
    if _schema_ready['badge']:
        return
    conn.execute(
        'create table if not exists schema_migrations ('
        'migration_name text primary key, '
        'applied_at timestamp with time zone not null default current_timestamp'
        ')'
    )
    conn.execute(
        'create table if not exists badges ('
        'badge_id integer, '
        'badge_name text not null'
        ')'
    )

    if not _has_constraint(conn, 'badges', 'badges_pkey'):
        conn.execute('alter table badges add constraint badges_pkey primary key (badge_id)')
    if not _has_column(conn, 'badges', 'region'):
        conn.execute('alter table badges add column region text')
    if not _has_column(conn, 'badges', 'sprite_key'):
        conn.execute('alter table badges add column sprite_key text')
    if not _has_column(conn, 'event_bosses', 'badge_id'):
        conn.execute('alter table event_bosses add column badge_id integer')
    if not _has_constraint(conn, 'event_bosses', 'event_bosses_badge_id_fkey'):
        conn.execute(
            'alter table event_bosses add constraint event_bosses_badge_id_fkey '
            'foreign key (badge_id) references badges(badge_id)'
        )

    conn.execute(
        'create table if not exists attempt_badges ('
        'attempt_id integer not null references attempts(attempt_id) on delete cascade, '
        'badge_id integer not null references badges(badge_id), '
        'event_id integer references event_bosses(event_id) on delete set null, '
        'earned_at timestamp with time zone not null default current_timestamp, '
        'primary key (attempt_id, badge_id)'
        ')'
    )
    conn.execute(
        'create table if not exists pokemon_badges ('
        'pokemon_id integer not null references pokebank(pokemon_id) on delete cascade, '
        'badge_id integer not null references badges(badge_id), '
        'event_id integer references event_bosses(event_id) on delete set null, '
        'earned_at timestamp with time zone not null default current_timestamp, '
        'primary key (pokemon_id, badge_id)'
        ')'
    )
    conn.execute('create index if not exists idx_attempt_badges_badge_id on attempt_badges(badge_id)')
    conn.execute('create index if not exists idx_pokemon_badges_badge_id on pokemon_badges(badge_id)')

    migration_name = 'badge_architecture_v1'
    applied = conn.execute(
        'select 1 from schema_migrations where migration_name = %s',
        (migration_name,)
    ).fetchone()
    if applied:
        conn.commit()
        _schema_ready['badge'] = True
        return

    for badge_id, badge_name, region in BADGE_DEFINITIONS:
        conn.execute(
            'insert into badges (badge_id, badge_name, region, sprite_key) '
            'values (%s, %s, %s, %s) '
            'on conflict (badge_id) do update set '
            'badge_name = excluded.badge_name, region = excluded.region, sprite_key = excluded.sprite_key',
            (badge_id, badge_name, region, str(badge_id))
        )

    for version_group_ids, title_fragment, badge_id in EVENT_BADGE_MAPPINGS:
        placeholders = ','.join(['%s'] * len(version_group_ids))
        conn.execute(
            f'update event_bosses set badge_id = %s '
            f'where badge_id is null and version_group_id in ({placeholders}) '
            "and regexp_replace(lower(coalesce(encounter_title, '')), '\\s+', ' ', 'g') = %s",
            [badge_id, *version_group_ids, title_fragment]
        )

    if _has_column(conn, 'attempts', 'badges_earned'):
        conn.execute(
            'insert into attempt_badges (attempt_id, badge_id) '
            'select distinct a.attempt_id, token::integer '
            'from attempts a '
            "cross join lateral regexp_split_to_table(translate(coalesce(a.badges_earned, ''), '[]', ''), E'\\\\s*,\\\\s*') token "
            "where token ~ '^[0-9]+$' and exists (select 1 from badges b where b.badge_id = token::integer) "
            'on conflict (attempt_id, badge_id) do nothing'
        )

    if _has_column(conn, 'pokebank', 'badges_earned'):
        conn.execute(
            'insert into pokemon_badges (pokemon_id, badge_id) '
            'select distinct pb.pokemon_id, token::integer '
            'from pokebank pb '
            "cross join lateral regexp_split_to_table(translate(coalesce(pb.badges_earned, ''), '[]', ''), E'\\\\s*,\\\\s*') token "
            "where token ~ '^[0-9]+$' and exists (select 1 from badges b where b.badge_id = token::integer) "
            'on conflict (pokemon_id, badge_id) do nothing'
        )

    conn.execute(
        'insert into attempt_badges (attempt_id, badge_id) '
        'select distinct pb.attempt_id, pbadge.badge_id '
        'from pokemon_badges pbadge join pokebank pb on pb.pokemon_id = pbadge.pokemon_id '
        'on conflict (attempt_id, badge_id) do nothing'
    )

    conn.execute(
        'insert into schema_migrations (migration_name) values (%s) '
        'on conflict (migration_name) do nothing',
        (migration_name,)
    )
    conn.commit()
    _schema_ready['badge'] = True

def _pokemon_badges_text_expr(pokemon_alias):
    return (
        "coalesce((select string_agg(pbadge.badge_id::text, ',' order by pbadge.badge_id) "
        f'from pokemon_badges pbadge where pbadge.pokemon_id = {pokemon_alias}.pokemon_id), \'\') '
        'as badges_earned'
    )

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
        'account_type': row['account_type'] if 'account_type' in row.keys() else None,
    }

def _ensure_auth_schema(conn):
    if _schema_ready['auth']:
        return
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
    if not _has_column(conn, 'runs', 'last_opened_at'):
        conn.execute('alter table runs add column last_opened_at timestamp with time zone')
    if not _has_column(conn, 'runs', 'last_opened_attempt_number'):
        conn.execute('alter table runs add column last_opened_attempt_number integer')
    if not _has_column(conn, 'users', 'supabase_id'):
        conn.execute('alter table users add column supabase_id text unique')
    conn.execute('create index if not exists idx_runs_user_id on runs(user_id)')
    conn.execute('create index if not exists idx_runs_user_last_opened on runs(user_id, last_opened_at desc)')
    conn.execute('create index if not exists idx_users_email on users(email)')
    conn.execute('create index if not exists idx_users_supabase_id on users(supabase_id)')
    conn.commit()
    _schema_ready['auth'] = True

def _ensure_contact_reports_schema(conn):
    if _schema_ready['contact_reports']:
        return
    _ensure_auth_schema(conn)
    conn.execute(
        'create table if not exists contact_reports ('
        'report_id serial primary key, '
        'report_type text not null, '
        'topic text, '
        'title text, '
        'details text not null, '
        'reproduction_steps text, '
        'status text not null default \'open\', '
        'priority text not null default \'normal\', '
        'admin_notes text, '
        'user_id integer, '
        'run_id text, '
        'attempt_number integer, '
        'game_id integer, '
        'version_group_id integer, '
        'run_name text, '
        'game_name text, '
        'page_url text, '
        'user_agent text, '
        "created_at text not null default to_char(current_timestamp, 'YYYY-MM-DD HH24:MI:SS'), "
        "updated_at text not null default to_char(current_timestamp, 'YYYY-MM-DD HH24:MI:SS'), "
        'resolved_at text'
        ')'
    )
    conn.execute('create index if not exists idx_contact_reports_status on contact_reports(status)')
    conn.execute('create index if not exists idx_contact_reports_created_at on contact_reports(created_at)')
    conn.execute('create index if not exists idx_contact_reports_user_id on contact_reports(user_id)')
    conn.commit()
    _schema_ready['contact_reports'] = True

def create_contact_report(conn, report):
    _ensure_contact_reports_schema(conn)
    row = conn.execute(
        'insert into contact_reports ('
        'report_type, topic, title, details, reproduction_steps, user_id, run_id, attempt_number, '
        'game_id, version_group_id, run_name, game_name, page_url, user_agent'
        ') values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) '
        'returning report_id',
        (
            report.get('report_type'),
            report.get('topic'),
            report.get('title'),
            report.get('details'),
            report.get('reproduction_steps'),
            report.get('user_id'),
            report.get('run_id'),
            report.get('attempt_number'),
            report.get('game_id'),
            report.get('version_group_id'),
            report.get('run_name'),
            report.get('game_name'),
            report.get('page_url'),
            report.get('user_agent'),
        )
    ).fetchone()
    conn.commit()
    return int(row['report_id'])

def get_contact_reports(conn, status=None, game_id=None, version_group_id=None, limit=100):
    _ensure_contact_reports_schema(conn)
    params = []
    where_clauses = []
    if status:
        where_clauses.append('cr.status = %s')
        params.append(status)
    if game_id is not None:
        where_clauses.append('cr.game_id = %s')
        params.append(game_id)
    if version_group_id is not None:
        where_clauses.append('cr.version_group_id = %s')
        params.append(version_group_id)
    where = f'where {" and ".join(where_clauses)} ' if where_clauses else ''
    params.append(min(int(limit or 100), 250))
    rows = conn.execute(
        'select cr.report_id, cr.report_type, cr.topic, cr.title, cr.details, cr.reproduction_steps, '
        'cr.status, cr.priority, cr.admin_notes, cr.user_id, u.email as user_email, u.display_name as user_display_name, '
        'cr.run_id, cr.attempt_number, cr.game_id, cr.version_group_id, cr.run_name, cr.game_name, '
        'cr.page_url, cr.user_agent, cr.created_at, cr.updated_at, cr.resolved_at '
        'from contact_reports cr '
        'left join users u on cr.user_id = u.user_id '
        f'{where}'
        'order by cr.report_id desc '
        'limit %s',
        params
    ).fetchall()
    return [dict(row) for row in rows]

def get_contact_report_stats(conn, generation=None):
    _ensure_contact_reports_schema(conn)
    params = []
    where_clauses = ["g.valid_game = 'valid'"]
    if generation is not None:
        where_clauses.append('g.generation = %s')
        params.append(generation)
    where = 'where ' + ' and '.join(where_clauses) + ' '

    rows = conn.execute(
        'select '
        'coalesce(cr.game_id, g.game_id) as game_id, '
        'coalesce(cr.version_group_id, g.version_group_id) as version_group_id, '
        'g.generation, '
        'coalesce(cr.game_name, g.name, \'Unknown\') as game_name, '
        'count(cr.report_id) as total_reports, '
        "sum(case when cr.report_type = 'general_contact' then 1 else 0 end) as general_count, "
        "sum(case when cr.report_type = 'bug' then 1 else 0 end) as bug_count, "
        "sum(case when cr.report_type = 'missing_information' then 1 else 0 end) as missing_count, "
        "sum(case when cr.report_type = 'incorrect_information' then 1 else 0 end) as incorrect_count "
        'from games g '
        'left join contact_reports cr on cr.game_id = g.game_id '
        f'{where}'
        'group by coalesce(cr.game_id, g.game_id), coalesce(cr.version_group_id, g.version_group_id), g.generation, coalesce(cr.game_name, g.name, \'Unknown\') '
        'order by g.generation asc, coalesce(cr.version_group_id, g.version_group_id) asc, coalesce(cr.game_id, g.game_id) asc',
        params
    ).fetchall()
    return [dict(row) for row in rows]

def update_contact_report(conn, report_id, status=None, priority=None, admin_notes=None):
    _ensure_contact_reports_schema(conn)
    allowed_statuses = {'open', 'reviewing', 'resolved', 'closed'}
    allowed_priorities = {'low', 'normal', 'high'}
    updates = ["updated_at = to_char(current_timestamp, 'YYYY-MM-DD HH24:MI:SS')"]
    params = []

    if status is not None:
        if status not in allowed_statuses:
            return {'success': False, 'error': 'Invalid status'}
        updates.append('status = %s')
        params.append(status)
        if status in {'resolved', 'closed'}:
            updates.append("resolved_at = coalesce(resolved_at, to_char(current_timestamp, 'YYYY-MM-DD HH24:MI:SS'))")
        else:
            updates.append('resolved_at = null')

    if priority is not None:
        if priority not in allowed_priorities:
            return {'success': False, 'error': 'Invalid priority'}
        updates.append('priority = %s')
        params.append(priority)

    if admin_notes is not None:
        updates.append('admin_notes = %s')
        params.append(admin_notes)

    params.append(report_id)
    row = conn.execute(
        f'update contact_reports set {", ".join(updates)} where report_id = %s returning report_id',
        params
    ).fetchone()
    conn.commit()
    if not row:
        return {'success': False, 'error': 'Report not found'}
    return {'success': True}

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
        'select user_id, email, display_name, created_at, account_type from users where supabase_id = %s',
        (supabase_id,)
    ).fetchone()
    if row:
        return _public_user(row)

    normalized_email = _normalize_email(email)

    # If this email already exists locally (legacy account), link it instead of inserting.
    if normalized_email:
        existing = conn.execute(
            'select user_id, email, display_name, created_at, supabase_id, account_type '
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
        'select user_id, email, display_name, created_at, account_type from users where supabase_id = %s',
        (supabase_id,)
    ).fetchone()

    if not row and normalized_email:
        row = conn.execute(
            'select user_id, email, display_name, created_at, account_type from users where lower(email) = %s',
            (normalized_email,)
        ).fetchone()
        if row:
            conn.execute(
                'update users set supabase_id = %s where user_id = %s',
                (supabase_id, row['user_id'])
            )
            conn.commit()
            row = conn.execute(
                'select user_id, email, display_name, created_at, account_type from users where supabase_id = %s',
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

def _get_attempt_badge_ids(conn, attempt_id, run_id=None, fallback_to_pokebank=False):
    _ensure_badge_schema(conn)
    rows = conn.execute(
        'select badge_id from attempt_badges where attempt_id = %s',
        (attempt_id,)
    ).fetchall()
    return {int(row['badge_id']) for row in rows}

def _set_attempt_badge_ids(conn, attempt_id, badge_ids):
    _ensure_badge_schema(conn)
    for badge_id in badge_ids:
        conn.execute(
            'insert into attempt_badges (attempt_id, badge_id) values (%s, %s) '
            'on conflict (attempt_id, badge_id) do nothing',
            (attempt_id, int(badge_id))
        )

def mark_trainer_victory(conn, run_id, attempt_number, trainer_id, event_id=None):
    _ensure_badge_schema(conn)
    row = conn.execute(
        'select attempt_id from attempts where run_id = %s and attempt_number = %s',
        (run_id, attempt_number)
    ).fetchone()
    if not row:
        return {'success': False, 'error': 'Attempt not found'}
    attempt_id = row['attempt_id']

    event_row = None
    if event_id is not None:
        event_row = conn.execute(
            'select eb.event_id, eb.badge_id, b.badge_name '
            'from event_bosses eb '
            'join runs r on r.run_id = %s '
            'join games g on nullif(g.game_id::text, \'\')::integer = nullif(r.game_id::text, \'\')::integer '
            'left join badges b on b.badge_id = eb.badge_id '
            'where eb.event_id = %s and eb.trainer_id = %s '
            'and eb.version_group_id = g.version_group_id '
            'and (eb.game_id is null or nullif(eb.game_id::text, \'\')::integer = nullif(r.game_id::text, \'\')::integer)',
            (run_id, event_id, trainer_id)
        ).fetchone()
        if not event_row:
            return {'success': False, 'error': 'Boss event not found for this run'}

    existing = conn.execute(
        'select 1 from trainers_defeated where run_id = %s and attempt_id = %s and trainer_id = %s limit 1',
        (run_id, attempt_id, trainer_id)
    ).fetchone()
    if not existing:
        conn.execute(
            'insert into trainers_defeated (run_id, attempt_id, trainer_id) values (%s, %s, %s)',
            (run_id, attempt_id, trainer_id)
        )

    victory_is_new = not existing
    badge_id = int(event_row['badge_id']) if event_row and event_row['badge_id'] is not None else None
    is_gym_leader = badge_id is not None
    badge_awarded = None
    updated_party_pokemon = 0

    has_trainers_defeated = _has_column(conn, 'pokebank', 'trainers_defeated')
    if not has_trainers_defeated:
        conn.execute('alter table pokebank add column trainers_defeated text')
        conn.commit()
        has_trainers_defeated = True

    if victory_is_new and has_trainers_defeated:
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

    if victory_is_new and badge_id is not None:
        inserted_badge = conn.execute(
            'insert into attempt_badges (attempt_id, badge_id, event_id) values (%s, %s, %s) '
            'on conflict (attempt_id, badge_id) do nothing returning badge_id',
            (attempt_id, badge_id, event_id)
        ).fetchone()
        if inserted_badge:
            badge_awarded = {
                'badge_id': badge_id,
                'badge_name': event_row['badge_name'] or f'Badge {badge_id}',
            }
            inserted_party_badges = conn.execute(
                'insert into pokemon_badges (pokemon_id, badge_id, event_id) '
                'select p.pokemon_id, %s, %s from party p where p.attempt_id = %s '
                'on conflict (pokemon_id, badge_id) do nothing',
                (badge_id, event_id, attempt_id)
            )
            updated_party_pokemon += inserted_party_badges.rowcount

    conn.commit()
    return {
        'success': True,
        'badge_awarded': badge_awarded,
        'is_gym_leader': is_gym_leader,
        'updated_party_pokemon': updated_party_pokemon,
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

    script = get_script(conn, starter, version_group_id=version_group_id, run_id=run_id, attempt_number=attempt_number, game_id=game_id)
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
    if attempt_row and location_ids and version_group_id is not None:
        placeholders = ','.join(['%s'] * len(location_ids))
        # Regular trainers (not rematch, not event) drive the progress counts;
        # rematch/event trainers count separately so venue rows (stadiums,
        # cruise, League rematches) still surface in the trainer filter.
        game_id_clause = "and (tp.game_id is null or tp.game_id = %s) " if game_id is not None else "and tp.game_id is null "
        game_id_param = [game_id] if game_id is not None else []
        special_case = (
            "case when lower(coalesce(tp.is_rematch::text, '')) in ('1', 'true', 't', 'yes') "
            "  or lower(coalesce(tp.is_event::text, '')) in ('1', 'true', 't', 'yes') then 1 else 0 end"
        )
        trainer_rows = conn.execute(
            f'select tp.canonical_location_id as location_id, '
            f"count(case when {special_case} = 0 then 1 end) as trainer_count, "
            f"count(case when {special_case} = 0 and td.trainer_id is null then 1 end) as available_trainer_count, "
            f"count(case when {special_case} = 1 then 1 end) as special_trainer_count "
            f'from trainer_pool tp '
            f'left join trainers_defeated td '
            f'on td.trainer_id = tp.trainer_id and td.run_id = %s and td.attempt_id = %s '
            f"where tp.canonical_location_id in ({placeholders}) "
            f"and tp.version_group_id = %s "
            f"{game_id_clause}"
            f"and not exists ("
            f"  select 1 from event_bosses eb "
            f"  where eb.trainer_id = tp.trainer_id "
            f"    and eb.version_group_id = tp.version_group_id"
            f") "
            f'group by tp.canonical_location_id',
            [run_id, attempt_row['attempt_id'], *location_ids, version_group_id, *game_id_param]
        ).fetchall()
        available_trainers_by_location = {
            int(row['location_id']): {
                'trainer_count': int(row['trainer_count'] or 0),
                'available_trainer_count': int(row['available_trainer_count'] or 0),
                'special_trainer_count': int(row['special_trainer_count'] or 0),
            }
            for row in trainer_rows
        }

    for row in script_list:
        if row['event_type'] != 'Location':
            continue
        # Bonus locations are extra encounter slots; they share the canonical
        # location id but must not inherit its trainer roster.
        trainer_meta = None if row['is_bonus_location'] else available_trainers_by_location.get(int(row['event_id']), None)
        row['trainer_count'] = trainer_meta['trainer_count'] if trainer_meta else 0
        row['available_trainer_count'] = trainer_meta['available_trainer_count'] if trainer_meta else 0
        row['special_trainer_count'] = trainer_meta['special_trainer_count'] if trainer_meta else 0
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

    attempt_info = conn.execute(
        'select attempt_number, outcome, ended_at, ended_by_trainer_id, death_note '
        'from attempts where run_id = %s and attempt_number = %s',
        (run_id, attempt_number)
    ).fetchone()

    return {
        'run': run_dict,
        'script': script_list,
        'pools': pools,
        'encounters': encounters,
        'attempt': dict(attempt_info) if attempt_info else None,
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
    conn.execute('insert into pokebank (run_id, attempt_id, species_id, canonical_location_id, nickname, status, shiny) values (%s,%s,%s,%s,%s,%s,%s)', (state['active_run_id'],state['active_attempt_id'],species_id, location_id, nickname, status, shiny))
    conn.commit()

def drop_pokemon(conn, pokemon_id):
    conn.execute(f'delete from pokebank where pokemon_id = {pokemon_id}')
    conn.commit()

def get_pokemon_name_from_id(conn, species_id):
    return conn.execute('select name from species where species_id = (%s)',(species_id,)).fetchone()[0]

def upsert_encounter(conn, run_id, attempt_number, location_id, species_id, nickname, nature, status, shiny, pokemon_id=None, bonus_location=0, gender=None):
    attempt_id = conn.execute(
        'select attempt_id from attempts where run_id = %s and attempt_number = %s',
        (run_id, attempt_number)
    ).fetchone()['attempt_id']
    if pokemon_id:
        conn.execute(
            'update pokebank set species_id=%s, canonical_location_id=%s, nickname=%s, nature=%s, status=%s, shiny=%s, bonus_location=%s, gender=%s where pokemon_id=%s',
            (species_id, location_id, nickname, nature, status, shiny, bonus_location, gender, pokemon_id)
        )
        conn.commit()
        return pokemon_id
    else:
        # Guard against duplicates: check for an existing record at this location
        existing = conn.execute(
            'select pokemon_id from pokebank where run_id=%s and attempt_id=%s and canonical_location_id=%s and coalesce(bonus_location,0)=%s limit 1',
            (run_id, attempt_id, location_id, bonus_location or 0)
        ).fetchone()
        if existing:
            existing_id = existing['pokemon_id']
            conn.execute(
                'update pokebank set species_id=%s, nickname=%s, nature=%s, status=%s, shiny=%s, bonus_location=%s, gender=%s where pokemon_id=%s',
                (species_id, nickname, nature, status, shiny, bonus_location, gender, existing_id)
            )
            conn.commit()
            return existing_id
        conn.execute(
            'insert into pokebank (run_id, attempt_id, species_id, canonical_location_id, nickname, nature, status, shiny, bonus_location, gender) values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)',
            (run_id, attempt_id, species_id, location_id, nickname, nature, status, shiny, bonus_location, gender)
        )
        conn.commit()
        return conn.execute(
            'select currval(pg_get_serial_sequence(%s, %s)) as next_id',
            ('pokebank', 'pokemon_id')
        ).fetchone()['next_id']

def delete_encounter(conn, pokemon_id):
    conn.execute('delete from pokebank where pokemon_id = %s', (pokemon_id,))
    conn.commit()
def get_script(conn, starter, version_group_id=None, run_id=None, attempt_number=None, game_id=None):
    _ensure_bonus_locations_schema(conn)
    _ensure_badge_schema(conn)
    boss_filter = ''
    game_filter = ''
    loc_filter = ''
    bonus_sql = ''
    params = [starter]

    if version_group_id is not None:
        boss_filter = 'and eb.version_group_id = %s '
        loc_filter = 'where el.version_group_id = %s '
        params.append(version_group_id)

    if game_id is not None:
        game_filter = 'and (eb.game_id is null or eb.game_id = %s) '
        params.append(game_id)
    else:
        game_filter = 'and eb.game_id is null '

    if version_group_id is not None:
        params.append(version_group_id)

    if run_id is not None and attempt_number is not None:
        attempt_row = _get_attempt_row(conn, run_id, attempt_number)
        if attempt_row:
            bonus_sql = (
                'union all '
                'select nullif(bl.canonical_location_id::text, \'\')::integer as event_id, bl.canonical_name as display_name, '
                'nullif(bl.sort_order::text, \'\')::double precision as sort_order, coalesce(nullif(bl.secondary_sort_order::text, \'\')::double precision, 0) as secondary_sort_order, '
                'bl.event_type, null, null, null, null, null, null::integer as version_group_id, 1 as is_bonus_location, '
                'null::integer as boss_event_id, null::integer as badge_id, null::text as type_focus, null::integer as level_cap, '
                'null::boolean as is_level_cap, null::text as battle_type '
                'from bonus_locations bl '
                'where bl.run_id = %s and bl.attempt_id = %s and bl.is_active = 1 '
            )
            params.append(run_id)
            params.append(attempt_row['attempt_id'])

    return conn.execute(
        'select nullif(eb.trainer_id::text, \'\')::integer as event_id, eb.encounter_title as display_name, nullif(eb.sort_order::text, \'\')::double precision as sort_order, 0::double precision as secondary_sort_order, eb.event_type, tp.encounter_name, tp.trainer_name, tp.trainer_class, tp.trainer_items, tp.trainer_pic, eb.version_group_id, 0::integer as is_bonus_location, eb.event_id as boss_event_id, eb.badge_id, eb.type_focus, '
        '(select max(nullif(t.lvl::text, \'\')::integer) from trainer_pokemon t where t.trainer_id = eb.trainer_id or (t.trainer_id is null and t.encounter_name = tp.encounter_name and (t.version_group_id is null or t.version_group_id = eb.version_group_id))) as level_cap, '
        'eb.is_level_cap, eb.battle_type '
        'from event_bosses eb left join trainer_pool tp on eb.trainer_id = tp.trainer_id '
        "where (eb.starter = (%s) or eb.starter is null or eb.starter = '') "
        f'{boss_filter}'
        f'{game_filter}'
        'union all '
        'select nullif(el.canonical_location_id::text, \'\')::integer as event_id, cl.canonical_location_name as display_name, nullif(el.sort_order::text, \'\')::double precision as sort_order, coalesce(nullif(el.secondary_sort_order::text, \'\')::double precision, 0) as secondary_sort_order, el.event_type, null, null, null, null, null, el.version_group_id, 0::integer as is_bonus_location, null::integer as boss_event_id, null::integer as badge_id, null::text as type_focus, null::integer as level_cap, '
        'null::boolean as is_level_cap, null::text as battle_type '
        'from event_locations el '
        'join canon_locations cl on nullif(cl.canonical_location_id::text, \'\')::integer = nullif(el.canonical_location_id::text, \'\')::integer '
        f'{loc_filter}'
        f'{bonus_sql}'
        # display_name breaks sort ties deterministically; without it,
        # same-sort rows (e.g. Route 12 / Giant Chasm, both 35) come back in
        # whatever order the planner chose that day.
        'order by sort_order asc, secondary_sort_order asc, display_name asc',
        tuple(params)).fetchall()

def get_location_by_id(conn, location_id):
    row = conn.execute(
        'select canonical_location_name as location_name '
        'from canon_locations where canonical_location_id = (%s) limit 1',
        (location_id,)
    ).fetchone()
    return row['location_name'] if row else None

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
    return conn.execute('select species_id, canonical_location_id as location_id from pokebank where run_id = (%s) and attempt_id = (%s)', (run_id, attempt_id)).fetchall()

def get_pokebank_with_stats(conn, run_id, attempt_number):
    _ensure_badge_schema(conn)
    has_trainers_defeated = conn.execute(
        "select 1 from information_schema.columns where table_name = 'pokebank' and column_name = 'trainers_defeated' limit 1"
    ).fetchone() is not None
    
    badges_select = ', ' + _pokemon_badges_text_expr('pb')
    trainers_defeated_select = ', pb.trainers_defeated' if has_trainers_defeated else ", '' as trainers_defeated"
    has_gender = _has_column(conn, 'pokebank', 'gender')
    gender_select = ', pb.gender' if has_gender else ", 'male' as gender"

    rows = conn.execute(
        f'select pb.pokemon_id, pb.species_id, s.name as species_name, pb.canonical_location_id as location_id, '
        f'cl.canonical_location_name as location_name, '
        f'pb.level_met, pb.nickname, pb.nature, pb.status, pb.shiny, '
        f'st.type1, st.type2, sa.ability1, sa.ability2, sa.ability3, ss.hp, ss.atk, ss.def, ss.spa, ss.spd, ss.spe, ss.bst'
        f'{badges_select}{trainers_defeated_select}{gender_select} '
        f'from pokebank pb '
        f'join attempts a on nullif(pb.attempt_id::text, \'\')::integer = nullif(a.attempt_id::text, \'\')::integer '
        f'join runs r on nullif(pb.run_id::text, \'\')::integer = nullif(r.run_id::text, \'\')::integer '
        f'join games g on nullif(r.game_id::text, \'\')::integer = nullif(g.game_id::text, \'\')::integer '
        f'left join species s on pb.species_id = s.species_id '
        f'left join canon_locations cl on nullif(cl.canonical_location_id::text, \'\')::integer = nullif(pb.canonical_location_id::text, \'\')::integer '
        + _build_generation_patch_join('species_stats', 'ss', 'pb.species_id', 'g.generation', 'g.version_group_id')
        + _build_generation_patch_join('species_types', 'st', 'pb.species_id', 'g.generation', 'g.version_group_id')
        + _build_generation_patch_join('species_abilities', 'sa', 'pb.species_id', 'g.generation', 'g.version_group_id')
        + f'where nullif(pb.run_id::text, \'\')::integer = %s and nullif(a.attempt_number::text, \'\')::integer = %s',
        (run_id, attempt_number)
    ).fetchall()
    return [dict(r) for r in rows]

def get_pokebank_for_attempt(conn, run_id, attempt_number):
    _ensure_badge_schema(conn)
    version_group_id = _get_run_version_group_id(conn, run_id)
    badges_col = _pokemon_badges_text_expr('pb')
    has_gender_col = _has_column(conn, 'pokebank', 'gender')
    gender_col = 'pb.gender' if has_gender_col else "'male' as gender"
    rows = conn.execute(
        'select pb.pokemon_id, pb.species_id, s.name as species_name, pb.canonical_location_id as location_id, '
        'case '
        '  when coalesce(pb.bonus_location, 0) > 0 then pb.bonus_location '
        '  else coalesce(el.secondary_sort_order, 0) '
        'end as secondary_sort_order, '
        f'pb.level_met, pb.nickname, pb.nature, pb.status, pb.shiny, {badges_col}, {gender_col} '
        'from pokebank pb '
        'join attempts a on pb.attempt_id = a.attempt_id '
        'left join species s on pb.species_id = s.species_id '
        'left join event_locations el on el.canonical_location_id = pb.canonical_location_id and el.version_group_id = %s '
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

def get_trainers_by_location(conn, location_id, run_id=None, attempt_number=None, version_group_id=None, game_id=None, include_rematches=False, include_events=False):
    attempt_id = None
    if run_id is not None and attempt_number is not None:
        attempt_row = conn.execute(
            'select attempt_id from attempts where run_id = %s and attempt_number = %s',
            (run_id, attempt_number)
        ).fetchone()
        attempt_id = attempt_row['attempt_id'] if attempt_row else None

    # Derive version_group_id and game_id from the run if not provided
    if (version_group_id is None or game_id is None) and run_id is not None:
        run_info = conn.execute(
            'select g.version_group_id, r.game_id from runs r join games g on nullif(r.game_id::text, \'\')::integer = nullif(g.game_id::text, \'\')::integer where nullif(r.run_id::text, \'\')::integer = %s',
            (run_id,)
        ).fetchone()
        if run_info:
            if version_group_id is None:
                version_group_id = run_info['version_group_id']
            if game_id is None:
                game_id = run_info['game_id']

    if version_group_id is None and game_id is not None:
        game_row = conn.execute(
            'select version_group_id from games where game_id = %s', (game_id,)
        ).fetchone()
        if game_row:
            version_group_id = game_row['version_group_id']

    if version_group_id is None:
        raise ValueError('version_group_id is required to fetch trainers for a location')

    params = []
    defeated_join = ''
    defeated_select = '0 as is_defeated '

    if run_id is not None and attempt_id is not None:
        defeated_join = (
            'left join trainers_defeated td '
            'on td.trainer_id = tp.trainer_id and td.run_id = %s and td.attempt_id = %s '
        )
        defeated_select = 'case when td.trainer_id is null then 0 else 1 end as is_defeated '
        params = [run_id, attempt_id]

    # Always filter by location_id and version_group_id
    where_clauses = ["tp.canonical_location_id = %s", "tp.version_group_id = %s"]
    params.append(location_id)
    params.append(version_group_id)
    # Filter by game_id: include shared rows (null) and rows for this specific game
    if game_id is not None:
        where_clauses.append("(tp.game_id is null or tp.game_id = %s)")
        params.append(game_id)
    else:
        where_clauses.append("tp.game_id is null")
    # Regular trainers by default; rematches and one-off event battles are
    # opt-in extras. Scripted bosses always stay out -- they render as their
    # own script rows.
    if not include_rematches:
        where_clauses.append("case when lower(coalesce(tp.is_rematch::text, '')) in ('1', 'true', 't', 'yes') then 1 else 0 end = 0")
    if not include_events:
        where_clauses.append("case when lower(coalesce(tp.is_event::text, '')) in ('1', 'true', 't', 'yes') then 1 else 0 end = 0")
    where_clauses.append(
        "not exists ("
        "select 1 from event_bosses eb "
        "where eb.trainer_id = tp.trainer_id "
        "and eb.version_group_id = tp.version_group_id"
        ")"
    )

    query = (
        'select tp.trainer_id, tp.encounter_name, tp.trainer_name, tp.trainer_class, tp.trainer_items, tp.trainer_pic, tp.version_group_id, '
        'tp.area_id, la.area_name, la.area_kind, la.sort_order as area_sort_order, '
        "case when lower(coalesce(tp.is_event::text, '')) in ('1', 'true', 't', 'yes') then 1 else 0 end as is_event, "
        "case when lower(coalesce(tp.is_rematch::text, '')) in ('1', 'true', 't', 'yes') then 1 else 0 end as is_rematch, "
        + defeated_select +
        'from trainer_pool tp '
        + defeated_join +
        'left join location_areas la on la.area_id = tp.area_id '
        'where ' + ' and '.join(where_clauses) + ' '
        # Trainers standing in the location itself sort before its sub-areas.
        "order by case when lower(coalesce(tp.is_event::text, '')) in ('1', 'true', 't', 'yes') then 1 else 0 end asc, "
        'case when tp.area_id is null then 0 else 1 end asc, '
        'la.sort_order asc nulls last, la.area_name asc nulls last, tp.trainer_id asc'
    )
    return conn.execute(query, params).fetchall()

def get_placement_summary(conn):
    """Per-version-group placement progress for the admin surface.

    An unplaced trainer is only a real gap when it is neither excluded by
    curation (unused ROM data) nor attached to a scripted boss event
    (those display through the boss skeleton, never a location panel).
    """
    # No join against trainer_placement_suggestions: its grain is one row per
    # (trainer, candidate location, source), which would fan out every count.
    return conn.execute(
        'select tp.version_group_id, '
        'count(*) as total_trainers, '
        'count(*) filter (where tp.canonical_location_id is not null) as placed, '
        'count(*) filter (where tp.canonical_location_id is null) as unplaced, '
        "count(*) filter (where tp.canonical_location_id is null and c.status = 'excluded') as excluded, "
        'count(*) filter (where tp.canonical_location_id is null '
        "  and coalesce(c.status, '') <> 'excluded' "
        '  and exists (select 1 from event_bosses eb where eb.trainer_id = tp.trainer_id)'
        ') as boss_linked, '
        'count(*) filter (where tp.canonical_location_id is null '
        "  and coalesce(c.status, '') <> 'excluded' "
        '  and not exists (select 1 from event_bosses eb where eb.trainer_id = tp.trainer_id)'
        ') as actionable_gaps, '
        'count(*) filter (where tp.canonical_location_id is null '
        '  and exists (select 1 from trainer_placement_suggestions s '
        '    where s.version_group_id = tp.version_group_id and s.trainer_key = tp.encounter_name)'
        ') as unplaced_with_suggestions, '
        'count(c.trainer_key) as curated '
        'from trainer_pool tp '
        'left join curated_trainer_placements c '
        '  on c.version_group_id = tp.version_group_id and c.trainer_key = tp.encounter_name '
        'where tp.version_group_id is not null '
        'group by tp.version_group_id order by tp.version_group_id'
    ).fetchall()

def get_unplaced_trainers(conn, version_group_id, limit=100, offset=0, only_suggested=False):
    """Unplaced trainers for one version group, with their suggestions."""
    suggested_filter = (
        'and exists (select 1 from trainer_placement_suggestions s '
        'where s.version_group_id = tp.version_group_id and s.trainer_key = tp.encounter_name) '
    ) if only_suggested else ''
    trainers = conn.execute(
        'select tp.trainer_id, tp.encounter_name, tp.trainer_name, tp.trainer_class, tp.details, '
        "case when lower(coalesce(tp.is_rematch::text, '')) in ('1','true','t','yes') then 1 else 0 end as is_rematch "
        'from trainer_pool tp '
        'where tp.version_group_id = %s and tp.canonical_location_id is null '
        + suggested_filter +
        'order by tp.encounter_name asc limit %s offset %s',
        (version_group_id, limit, offset)
    ).fetchall()
    trainer_list = [dict(t) for t in trainers]
    if not trainer_list:
        return trainer_list

    keys = [t['encounter_name'] for t in trainer_list]
    placeholders = ','.join(['%s'] * len(keys))
    suggestion_rows = conn.execute(
        'select s.trainer_key, s.canonical_location_id, cl.canonical_location_name, '
        's.area_name, s.source, s.detail, '
        'exists (select 1 from event_locations el '
        '  where el.canonical_location_id = s.canonical_location_id '
        '  and el.version_group_id = s.version_group_id) as in_script '
        'from trainer_placement_suggestions s '
        'join canon_locations cl on cl.canonical_location_id = s.canonical_location_id '
        f'where s.version_group_id = %s and s.trainer_key in ({placeholders}) '
        'order by s.trainer_key, s.source, cl.canonical_location_name',
        (version_group_id, *keys)
    ).fetchall()
    by_key = {}
    for row in suggestion_rows:
        by_key.setdefault(row['trainer_key'], []).append({
            'canonical_location_id': row['canonical_location_id'],
            'location_name': row['canonical_location_name'],
            'area_name': row['area_name'],
            'source': row['source'],
            'detail': row['detail'],
            'in_script': bool(row['in_script']),
        })
    for trainer in trainer_list:
        trainer['suggestions'] = by_key.get(trainer['encounter_name'], [])
    return trainer_list

def apply_trainer_placements(conn, version_group_id, placements):
    """Apply admin placement decisions.

    Each placement: {trainer_key, canonical_location_id, area_id | area_name}.
    Writes trainer_pool AND curated_trainer_placements, so re-extraction
    re-applies the decision. Returns per-placement results.
    """
    results = []
    for placement in placements:
        trainer_key = placement.get('trainer_key')
        location_id = placement.get('canonical_location_id')
        if not trainer_key or location_id is None:
            raise ValueError('Each placement needs trainer_key and canonical_location_id')
        location = conn.execute(
            'select canonical_location_id from canon_locations where canonical_location_id = %s',
            (location_id,)
        ).fetchone()
        if not location:
            raise ValueError(f'Unknown canonical_location_id {location_id}')

        area_id = placement.get('area_id')
        area_name = (placement.get('area_name') or '').strip()
        if area_id is None and area_name:
            existing = conn.execute(
                'select area_id from location_areas '
                'where canonical_location_id = %s and coalesce(version_group_id, -1) = %s and area_name = %s',
                (location_id, version_group_id, area_name)
            ).fetchone()
            if existing:
                area_id = existing['area_id']
            else:
                area_kind = 'gym' if 'gym' in area_name.lower() else 'interior'
                area_id = conn.execute(
                    'insert into location_areas (canonical_location_id, version_group_id, area_name, area_kind) '
                    'values (%s, %s, %s, %s) returning area_id',
                    (location_id, version_group_id, area_name, area_kind)
                ).fetchone()['area_id']

        updated = conn.execute(
            'update trainer_pool set canonical_location_id = %s, area_id = %s '
            'where version_group_id = %s and encounter_name = %s '
            'returning trainer_id',
            (location_id, area_id, version_group_id, trainer_key)
        ).fetchall()
        if not updated:
            raise ValueError(f'No trainer matches {trainer_key} in version group {version_group_id}')
        conn.execute(
            'insert into curated_trainer_placements '
            '(version_group_id, trainer_key, canonical_location_id, area_id, decided_at) '
            'values (%s, %s, %s, %s, current_timestamp) '
            'on conflict (version_group_id, trainer_key) do update set '
            'canonical_location_id = excluded.canonical_location_id, '
            'area_id = excluded.area_id, decided_at = excluded.decided_at',
            (version_group_id, trainer_key, location_id, area_id)
        )
        results.append({
            'trainer_key': trainer_key,
            'canonical_location_id': location_id,
            'area_id': area_id,
            'trainers_updated': len(updated),
        })
    conn.commit()
    return results

def _normalize_move_constant(move_token):
    token = (move_token or '').strip()
    if token.startswith('MOVE_'):
        token = token[5:]
    # Handles decomp constants (MOVE_QUICK_ATTACK) and display names
    # (Quick Attack) alike; the lookup compares hyphenated slugs.
    return token.lower().replace('_', '-').replace(' ', '-')

def _format_label(value):
    if value is None:
        return None
    return str(value).replace('_', ' ').replace('-', ' ').title()

def _moveset_version_group_for(conn, version_group_id):
    """The version group to resolve movesets and move data against.

    ROM hacks live in the reserved 1000+ range, and the move resolvers assume
    chronologically ordered vanilla ids -- a raw hack id would select the
    newest vanilla learnset and modern move stats instead of the base game's.
    Hacks therefore resolve against their base game's version group.
    """
    if version_group_id is None:
        return None
    try:
        vg = int(version_group_id)
    except (TypeError, ValueError):
        return version_group_id
    if vg < 1000:
        return vg
    row = conn.execute(
        'select base.version_group_id from games g '
        'join games base on base.game_id = g.base_game_id '
        'where g.version_group_id = %s and base.version_group_id is not null limit 1',
        (vg,)
    ).fetchone()
    return row['version_group_id'] if row else vg

def _resolve_move_details(conn, move_id, version_group_id):
    if move_id is None:
        return None

    default = None
    future_candidates = []
    exact_override = None

    rows = conn.execute(
        'select move_id, move_name, type, damage_class, power, accuracy, version_group_id '
        'from moves where move_id = %s order by version_group_id asc',
        (move_id,)
    ).fetchall()

    # A hack's rebalanced move row (stored at its reserved 1000+ version
    # group) wins outright; otherwise hacks resolve past-values against
    # their base game's chronology. Vanilla targets never treat a same-vg
    # past-value row as an override -- a row keyed at vg X records the
    # change AT X, which games at or after X do not use.
    try:
        raw_target = int(version_group_id) if version_group_id is not None else None
    except (TypeError, ValueError):
        raw_target = None
    hack_target = raw_target if raw_target is not None and raw_target >= 1000 else None
    version_group_id = _moveset_version_group_for(conn, version_group_id)

    for row in rows:
        r = dict(row)
        vg = r.get('version_group_id')
        if hack_target is not None and vg == hack_target:
            exact_override = r
        if not vg:  # NULL or 0 both treated as the default/fallback row
            default = r
        elif vg < 1000 and version_group_id is not None and vg > version_group_id:
            # Reserved-range (hack) rows never act as vanilla past-values.
            future_candidates.append(r)

    # moves.past_values are stored keyed by the version group where the change happened;
    # for an older game, pick the nearest change row above the target version group.
    if exact_override is not None:
        selected = exact_override
    elif future_candidates:
        selected = min(future_candidates, key=lambda x: x['version_group_id'])
    else:
        selected = default
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
        'debug_selected_row_type': 'versioned' if selected.get('version_group_id') else 'default',
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
            'order by case when coalesce(version_group_id, 0) = 0 then 1 else 0 end, version_group_id desc limit 1',
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
        # No game context means vanilla: reserved-range (hack) learnsets
        # must never win the "newest available" pick.
        vanilla_values = [v for v in values if v < 1000]
        return max(vanilla_values) if vanilla_values else max(values)

    # A hack's own learnset rows (loaded at its reserved version group) win
    # outright; species the hack left unchanged fall back to the BASE game's
    # chronology -- raw hack ids (1000+) would otherwise select the newest
    # vanilla learnset instead of the base game's.
    target = int(target_version_group_id)
    if target in values:
        return target
    target = _moveset_version_group_for(conn, target)

    eligible = [v for v in values if v <= target]
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

    if version_group_id is not None:
        tp_vg_filter = 'and (t.version_group_id is null or t.version_group_id = %s) '
        tp_params = (version_group_id, game_generation, version_group_id, game_generation,
                     version_group_id, game_generation, trainer_name, version_group_id)
    else:
        tp_vg_filter = 'and t.version_group_id is null '
        tp_params = (None, game_generation, None, game_generation,
                     None, game_generation, trainer_name)

    rows = conn.execute(
        'select sp.species_id, t.species_name, st.type1, st.type2, '
        'coalesce(t.ability, sa.ability1) as ability1, ss.bst, ss.hp, ss.atk, ss.def, ss.spa, ss.spd, ss.spe, '
        't.iv, t.lvl, t.moves, t.held_item '
        'from trainer_pokemon t '
        'left join species sp on t.species_name = sp.name '
        + _build_generation_patch_join('species_stats', 'ss', 'sp.species_id', '%s', '%s')
        + _build_generation_patch_join('species_types', 'st', 'sp.species_id', '%s', '%s')
        + _build_generation_patch_join('species_abilities', 'sa', 'sp.species_id', '%s', '%s')
        + f'where encounter_name = (%s) {tp_vg_filter}',
        tp_params
    ).fetchall()

    return _assemble_trainer_party(conn, rows, version_group_id)

def _assemble_trainer_party(conn, rows, version_group_id):
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

def _attach_observed_moves(conn, party, trainer_version_group_id, trainer_key, display_version_group_id):
    """Attach admin-observed moves to party members.

    curated_trainer_moves is keyed by the stable ETL identity (trainer's own
    version group + encounter name + slot); a row only attaches when its
    recorded species still occupies the slot, so a re-extraction that
    reshuffles a party silently drops stale observations instead of
    mislabeling the new occupant. Details resolve through the same machinery
    as explicit trainer moves, in the display game's context.
    """
    for pokemon in party:
        pokemon['observed_moves'] = []
    if trainer_version_group_id is None or not trainer_key:
        return party
    rows = conn.execute(
        'select slot, species_name, move_name from curated_trainer_moves '
        'where version_group_id = %s and trainer_key = %s '
        'order by slot asc, noted_at asc',
        (trainer_version_group_id, trainer_key)
    ).fetchall()
    if not rows:
        return party
    by_slot = {}
    for row in rows:
        by_slot.setdefault(row['slot'], []).append(row)
    for pokemon in party:
        matches = [
            r for r in by_slot.get(pokemon.get('slot'), [])
            if (r['species_name'] or '').upper() == (pokemon.get('species_name') or '').upper()
        ]
        for match in matches:
            details = _resolve_explicit_moves(conn, match['move_name'], display_version_group_id)
            if details:
                pokemon['observed_moves'].append(details[0])
            else:
                pokemon['observed_moves'].append({'move_name': match['move_name']})
    return party

def add_observed_move(conn, trainer_id, slot, move_name):
    """Record a move an opponent was seen using. Returns the attached
    move details, or raises ValueError on bad identity or unknown move."""
    move_name = (move_name or '').strip()
    if not move_name:
        raise ValueError('move_name is required')
    if ',' in move_name:
        raise ValueError('One move at a time')
    trainer = conn.execute(
        'select encounter_name, version_group_id from trainer_pool where trainer_id = %s',
        (trainer_id,)
    ).fetchone()
    if not trainer or trainer['version_group_id'] is None:
        raise ValueError(f'Unknown trainer {trainer_id}')
    slot_row = conn.execute(
        'select species_name from trainer_pokemon where trainer_id = %s and slot = %s',
        (trainer_id, slot)
    ).fetchone()
    if not slot_row:
        raise ValueError(f'Trainer {trainer_id} has no party slot {slot}')
    resolved = _resolve_explicit_moves(conn, move_name, trainer['version_group_id'])
    if not resolved:
        raise ValueError(f'Unknown move {move_name!r}')
    canonical_name = resolved[0]['move_name']
    # Re-observing after a re-extraction changed the slot's species must
    # revive the row, not silently no-op against the stale one.
    conn.execute(
        'insert into curated_trainer_moves '
        '(version_group_id, trainer_key, slot, species_name, move_name) '
        'values (%s, %s, %s, %s, %s) '
        'on conflict (version_group_id, trainer_key, slot, move_name) do update '
        'set species_name = excluded.species_name, noted_at = current_timestamp',
        (trainer['version_group_id'], trainer['encounter_name'], slot,
         slot_row['species_name'], canonical_name)
    )
    conn.commit()
    return resolved[0]

def delete_observed_move(conn, trainer_id, slot, move_name):
    """Remove an observed-move record. Returns the number of rows removed."""
    trainer = conn.execute(
        'select encounter_name, version_group_id from trainer_pool where trainer_id = %s',
        (trainer_id,)
    ).fetchone()
    if not trainer:
        raise ValueError(f'Unknown trainer {trainer_id}')
    # Compare by the same slug the add path canonicalizes through, so a
    # caller can delete with any accepted spelling of the name.
    result = conn.execute(
        'delete from curated_trainer_moves '
        'where version_group_id = %s and trainer_key = %s and slot = %s '
        "and lower(replace(replace(move_name, '_', '-'), ' ', '-')) = %s",
        (trainer['version_group_id'], trainer['encounter_name'], slot,
         _normalize_move_constant(move_name))
    )
    conn.commit()
    return result.rowcount

def search_move_names(conn, query, limit=15):
    """Distinct move names for the admin autocomplete."""
    q = (query or '').strip()[:80]
    if not q:
        return []
    escaped = q.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')
    rows = conn.execute(
        'select distinct move_name from moves where move_name ilike %s '
        'order by move_name asc limit %s',
        (f'%{escaped}%', limit)
    ).fetchall()
    return [r['move_name'] for r in rows]

def get_trainer_party_by_id(conn, trainer_id, game_id=None):
    """Party for one trainer_pool row, keyed by trainer_id.

    Returns None when the trainer does not exist. Falls back to the legacy
    encounter-name match (scoped to the trainer's own version group) for party
    rows whose trainer_id could not be backfilled.
    """
    trainer = conn.execute(
        'select trainer_id, encounter_name, version_group_id from trainer_pool where trainer_id = %s',
        (trainer_id,)
    ).fetchone()
    if not trainer:
        return None

    game_generation = _get_game_generation(conn, game_id=game_id)
    version_group_id = trainer['version_group_id']
    if game_id is not None:
        game_row = conn.execute('select version_group_id from games where game_id = %s', (game_id,)).fetchone()
        if game_row and game_row['version_group_id'] is not None:
            version_group_id = game_row['version_group_id']

    select_sql = (
        'select sp.species_id, t.species_name, st.type1, st.type2, '
        'coalesce(t.ability, sa.ability1) as ability1, ss.bst, ss.hp, ss.atk, ss.def, ss.spa, ss.spd, ss.spe, '
        't.iv, t.lvl, t.moves, t.held_item, t.slot, t.ability as trainer_ability, t.nature as trainer_nature '
        'from trainer_pokemon t '
        'left join species sp on t.species_name = sp.name '
        + _build_generation_patch_join('species_stats', 'ss', 'sp.species_id', '%s', '%s')
        + _build_generation_patch_join('species_types', 'st', 'sp.species_id', '%s', '%s')
        + _build_generation_patch_join('species_abilities', 'sa', 'sp.species_id', '%s', '%s')
    )
    join_params = (version_group_id, game_generation, version_group_id, game_generation,
                   version_group_id, game_generation)
    rows = conn.execute(
        select_sql + 'where t.trainer_id = %s order by t.slot asc nulls last, t.pk_id asc',
        (*join_params, trainer_id)
    ).fetchall()

    if not rows:
        rows = conn.execute(
            select_sql +
            'where t.trainer_id is null and t.encounter_name = %s '
            'and (t.version_group_id is null or t.version_group_id = %s) '
            'order by t.slot asc nulls last, t.pk_id asc',
            (*join_params, trainer['encounter_name'], trainer['version_group_id'])
        ).fetchall()

    party = _assemble_trainer_party(conn, rows, version_group_id)
    return _attach_observed_moves(
        conn, party, trainer['version_group_id'], trainer['encounter_name'], version_group_id)

def get_pokemon_trainers_and_badges(conn, run_id, attempt_number, pokemon_id):
    """Get trainers defeated and badges earned for a specific pokemon in a run/attempt."""
    _ensure_badge_schema(conn)
    has_trainers_defeated = conn.execute(
        "select 1 from information_schema.columns where table_name = 'pokebank' and column_name = 'trainers_defeated' limit 1"
    ).fetchone() is not None
    
    trainers_defeated_select = 'pb.trainers_defeated' if has_trainers_defeated else "'' as trainers_defeated"
    
    pokemon = conn.execute(
        f'select pb.pokemon_id, pb.species_id, pb.run_id, pb.attempt_id, {trainers_defeated_select} '
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
    run_row = conn.execute('select game_id from runs where run_id = %s', (run_id,)).fetchone()
    run_game_id = run_row['game_id'] if run_row else None

    if defeated_trainer_ids:
        placeholders = ','.join(['%s'] * len(defeated_trainer_ids))
        if run_game_id is not None:
            boss_rows = conn.execute(
                f'select trainer_id, event_type from event_bosses where trainer_id in ({placeholders}) and (game_id is null or game_id = %s)',
                defeated_trainer_ids + [run_game_id]
            ).fetchall()
        else:
            boss_rows = conn.execute(
                f'select trainer_id, event_type from event_bosses where trainer_id in ({placeholders}) and game_id is null',
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
    
    badge_rows = conn.execute(
        'select b.badge_id, b.badge_name, pb.earned_at, tp.trainer_name '
        'from pokemon_badges pb '
        'join badges b on b.badge_id = pb.badge_id '
        'left join event_bosses eb on eb.event_id = pb.event_id '
        'left join trainer_pool tp on tp.trainer_id = eb.trainer_id '
        'where pb.pokemon_id = %s order by pb.earned_at, b.badge_id',
        (pokemon_id,)
    ).fetchall()
    badges = [dict(badge) for badge in badge_rows]
    
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
    _ensure_badge_schema(conn)
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
