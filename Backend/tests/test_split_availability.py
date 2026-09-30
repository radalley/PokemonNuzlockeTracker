"""Split availability: the pure resolver over a Blaze Black-shaped script,
the migration's seed, the page payload decoration, and the admin routes."""
from pathlib import Path

import pytest

import api
import backend as backend_module
import split_availability as sa

MIGRATION_SQL = (Path(__file__).parents[1] / 'migrations' / '20260925_split_availability.sql').read_text(encoding='utf-8')


def loc(event_id, name, sort, secondary=1, bonus=False):
    return {'event_id': event_id, 'display_name': name, 'sort_order': sort, 'secondary_sort_order': secondary,
            'event_type': 'Location', 'boss_event_id': None, 'is_bonus_location': bonus, 'badge_id': None}


def boss(trainer_id, name, sort, *, badge=None, title=None, cap=None, event_type=None, key=None, type_focus=None, battle_type=None, level_cap_flag=True):
    return {'event_id': trainer_id, 'display_name': title or name, 'sort_order': sort, 'secondary_sort_order': 0,
            'event_type': event_type, 'boss_event_id': trainer_id * 10, 'badge_id': badge, 'trainer_name': name,
            'encounter_name': key or f'TRAINER_BB_{name}', 'type_focus': type_focus, 'battle_type': battle_type,
            'level_cap': cap, 'is_level_cap': level_cap_flag, 'is_bonus_location': False}


SCRIPT = [
    loc(1, 'Starter', 0), loc(3, 'Route 1', 1), loc(233, 'Striaton City', 3),
    boss(500, 'CRESS', '3.2', badge=33, title='Striaton City Gym', cap=14, type_focus='Water', battle_type='rotation'),
    loc(234, 'Dreamyard', 4), loc(8, 'Route 3', 5), loc(235, 'Wellspring Cave', 6),
    boss(501, 'LENORA', '7.1', badge=34, title='Nacrene City Gym', cap=20, type_focus='Normal', battle_type='double'),
    loc(237, 'Pinwheel Forest', 8),
    boss(502, 'BURGH', '9.1', badge=35, title='Castelia City Gym', cap=30, type_focus='Bug'),
    loc(9, 'Route 4', 10), loc(300, 'Victory Road', 32),
    boss(510, 'SHAUNTAL', '32.1', title='Elite Four - W', cap=73),
    boss(511, 'GRIMSLEY', '32.2', title='Elite Four - E', cap=73),
    boss(512, 'N', '32.5', title="N's Castle", cap=74, level_cap_flag=False),
    boss(513, 'GHETSIS', '32.6', title="N's Castle", cap=75, level_cap_flag=False),
    loc(301, 'Route 11', 33),
    boss(520, 'ALDER', '46.1', title='Champion', cap=100),
]

TABLES = {
    3: [
        {'species_id': 16, 'name': 'PIDGEY', 'method': 'grass', 'rate': 20, 'slot_kind': 'slot'},
        {'species_id': 531, 'name': 'AUDINO', 'method': 'grass-spots', 'rate': 80, 'slot_kind': 'slot'},
        {'species_id': 118, 'name': 'GOLDEEN', 'method': 'fish', 'rate': 60, 'slot_kind': 'slot'},
        {'species_id': 507, 'name': 'HERDIER', 'method': 'dark-grass', 'rate': 20, 'slot_kind': 'slot'},
        {'species_id': 550, 'name': 'BASCULIN', 'method': 'surf', 'rate': 60, 'slot_kind': 'slot'},
    ],
    234: [
        {'species_id': 517, 'name': 'MUNNA', 'method': 'grass', 'rate': 20, 'slot_kind': 'slot'},
        {'species_id': 531, 'name': 'AUDINO', 'method': 'grass-spots', 'rate': 40, 'slot_kind': 'slot'},
        {'species_id': 385, 'name': 'JIRACHI', 'method': 'grass-spots', 'rate': 1, 'slot_kind': 'overlay', 'tag': 'legendary'},
    ],
    237: [
        {'species_id': 532, 'name': 'TIMBURR', 'method': 'grass', 'rate': 20, 'slot_kind': 'slot', 'area': 'Outside', 'area_sort': 0},
        {'species_id': 546, 'name': 'COTTONEE', 'method': 'grass', 'rate': 20, 'slot_kind': 'slot', 'area': 'Inside', 'area_sort': 1},
        {'species_id': 640, 'name': 'VIRIZION', 'method': 'static', 'slot_kind': 'static', 'area': 'Rumination Field', 'area_sort': 2},
    ],
}

GATES = [
    {'gate_key': 'shaking-grass', 'label': 'Shaking grass', 'opens_in': 'badge:34', 'default_methods': ['grass-spots', 'cave-spots'], 'sort_order': 10},
    {'gate_key': 'fishing', 'label': 'Super Rod', 'opens_in': 'badge:34', 'default_methods': ['fish', 'fish-spots'], 'sort_order': 20},
    {'gate_key': 'surf', 'label': 'Surf', 'opens_in': None, 'default_methods': ['surf', 'surf-spots'], 'sort_order': 30},
]

RULES = [
    {'subject_kind': 'table', 'subject_key': '3||dark-grass|', 'opens_in': None, 'gate_key': 'surf', 'note': 'behind water'},
    {'subject_kind': 'area', 'subject_key': '237|Outside', 'opens_in': 'badge:34', 'gate_key': None, 'note': None},
    {'subject_kind': 'area', 'subject_key': '237|Inside', 'opens_in': 'badge:35', 'gate_key': None, 'note': None},
    {'subject_kind': 'location', 'subject_key': '234', 'opens_in': 'badge:33', 'gate_key': None, 'note': None},
    {'subject_kind': 'trainer', 'subject_key': 'GRUNT_1', 'opens_in': 'badge:34', 'gate_key': None, 'note': None},
    {'subject_kind': 'trainer', 'subject_key': 'GRUNT_2', 'opens_in': 'badge:34', 'gate_key': None, 'note': None},
    {'subject_kind': 'location', 'subject_key': '9', 'opens_in': 'badge:35', 'gate_key': None, 'note': None},
]

TRAINERS = [
    {'trainer_id': 1, 'encounter_name': 'ERI', 'trainer_name': 'ERI', 'trainer_class': 'LASS', 'canonical_location_id': 234, 'max_level': 10},
    {'trainer_id': 2, 'encounter_name': 'GRUNT_1', 'trainer_name': 'PLASMA GRUNT', 'trainer_class': 'PLASMA_GRUNT', 'canonical_location_id': 234, 'max_level': 15},
    {'trainer_id': 3, 'encounter_name': 'GRUNT_2', 'trainer_name': 'PLASMA GRUNT', 'trainer_class': 'PLASMA_GRUNT', 'canonical_location_id': 234, 'max_level': 15},
    {'trainer_id': 4, 'encounter_name': 'REMATCH', 'canonical_location_id': 234, 'is_rematch': 'true', 'max_level': 40},
    {'trainer_id': 5, 'encounter_name': 'GYM_TRAINER', 'canonical_location_id': 237, 'area_name': 'Inside', 'max_level': 18},
    {'trainer_id': 6, 'encounter_name': 'RANGER', 'canonical_location_id': 237, 'max_level': 17},
]


def test_sections_follow_gyms_then_league_then_hidden_postgame():
    sections = sa.build_sections(SCRIPT)
    assert [s['split_key'] for s in sections] == ['badge:33', 'badge:34', 'badge:35', 'league', 'postgame']
    assert [s['ordinal'] for s in sections] == [0, 1, 2, 3, 4]
    cress, lenora, _, league, postgame = sections
    assert (cress['label'], cress['level_cap'], cress['battle_type'], cress['type_focus']) == ('Cress', 14, 'rotation', 'Water')
    assert lenora['final_trainer_id'] == 501 and lenora['boss_event_ids'] == [5010]
    # The League runs from the first Elite Four member to the story finale.
    assert league['final_trainer_id'] == 513 and league['trainer_ids'] == [510, 511, 512, 513]
    assert league['level_cap'] == 73 and league['sort_to'] == 32.6
    # Alder is a post-game fight; Postgame waits for Ghetsis.
    assert postgame['trainer_ids'] == [520] and postgame['final_trainer_id'] == 520
    assert postgame['level_cap'] == 100 and postgame['reveal_after'] == 'league'


def test_locations_default_to_story_order_and_rules_override():
    result = sa.resolve(SCRIPT, TABLES, TRAINERS, GATES, RULES)
    homes = {lid: info['home_split'] for lid, info in result['locations'].items()}
    assert homes[1] == 'badge:33' and homes[3] == 'badge:33' and homes[233] == 'badge:33'
    assert homes[8] == 'badge:34' and homes[235] == 'badge:34'
    assert homes[234] == 'badge:33'        # rule: Dreamyard before the gym
    assert homes[9] == 'badge:35'          # rule: Route 4 before Burgh (story order says Elesa)
    assert homes[237] == 'badge:34'        # min over its areas: Outside opens in Lenora's split
    assert homes[300] == 'league' and homes[301] == 'postgame'
    assert result['bosses'] == {500: 'badge:33', 501: 'badge:34', 502: 'badge:35', 510: 'league', 511: 'league',
                                512: 'league', 513: 'league', 520: 'postgame'}


def test_tables_open_at_the_later_of_area_and_method_gate():
    result = sa.resolve(SCRIPT, TABLES, TRAINERS, GATES, RULES)
    tables = result['tables']
    assert tables['3||grass|']['opens_in'] == 'badge:33'
    assert tables['3||grass-spots|'] == {**tables['3||grass-spots|'], 'opens_in': 'badge:34', 'gate_key': 'shaking-grass', 'unknown': False}
    assert tables['3||fish|']['opens_in'] == 'badge:34'
    # A gate without a decided split is unknown, never guessed; the rule is kept for the editor.
    dark = tables['3||dark-grass|']
    assert dark['unknown'] and dark['gate_key'] == 'surf' and dark['opens_in'] is None and dark['rule']['note'] == 'behind water'
    surf = tables['3||surf|']
    assert surf['unknown'] and surf['gate_key'] == 'surf' and surf['rule'] is None
    # Areas: Outside in Lenora's split, Inside in Burgh's; the static inherits its own area (none) -> location default.
    assert tables['237|Outside|grass|']['opens_in'] == 'badge:34'
    assert tables['237|Inside|grass|']['opens_in'] == 'badge:35'
    assert tables['237|Rumination Field|static|']['opens_in'] == 'badge:35'
    # Dreamyard's shaking grass (home Cress) opens with the gate in Lenora's split.
    assert tables['234||grass-spots|']['opens_in'] == 'badge:34'


def test_revisits_list_later_tables_areas_and_trainers_per_split():
    result = sa.resolve(SCRIPT, TABLES, TRAINERS, GATES, RULES)
    route1 = result['locations'][3]['revisits']
    assert [r['split_key'] for r in route1] == ['badge:34']
    assert sorted(t['method'] for t in route1[0]['tables']) == ['fish', 'grass-spots']
    assert route1[0]['trainers'] == [] and route1[0]['areas'] == []
    dreamyard = result['locations'][234]
    assert [r['split_key'] for r in dreamyard['revisits']] == ['badge:34']
    revisit = dreamyard['revisits'][0]
    assert [t['trainer_id'] for t in revisit['trainers']] == [2, 3]
    assert revisit['trainers'][0]['max_level'] == 15
    assert revisit['tables'][0]['method'] == 'grass-spots'
    assert revisit['tables'][0]['rare'] == [{'species_id': 385, 'name': 'JIRACHI', 'rate': 1, 'slot_kind': 'overlay'}]
    assert dreamyard['trainer_splits'] == {'badge:34': 2}
    # Regular trainers in the home split and rematches are never revisits.
    assert result['trainers'][1]['opens_in'] == 'badge:33' and result['trainers'][4]['opens_in'] == 'badge:33'
    pinwheel = result['locations'][237]['revisits']
    assert [r['split_key'] for r in pinwheel] == ['badge:35']
    # Inside by rule; the static's field inherits the location's story-order
    # default (Burgh), which is later than the Outside home.
    assert pinwheel[0]['areas'] == ['Inside', 'Rumination Field']
    assert [t['area'] for t in pinwheel[0]['tables']] == ['Inside', 'Rumination Field']
    # A trainer inherits the area rule that shares its area name; one with no
    # area sits with its row (the home split), not the story-order default.
    assert result['trainers'][5]['opens_in'] == 'badge:35' and [t['trainer_id'] for t in pinwheel[0]['trainers']] == [5]
    assert result['trainers'][6]['opens_in'] == 'badge:34'


def test_unknown_keys_and_no_rules_degrade_safely():
    result = sa.resolve(SCRIPT, TABLES, TRAINERS, [], [
        {'subject_kind': 'location', 'subject_key': '3', 'opens_in': 'badge:999', 'gate_key': None},
    ])
    route1 = result['locations'][3]
    assert route1['own']['unknown'] and route1['home_split'] == 'badge:33'
    assert result['tables']['3||surf|']['opens_in'] == 'badge:33'   # no gates: the table inherits its location
    assert sa.resolve([], {}, [], [], [])['splits'][0]['split_key'] == 'postgame'


def test_payload_decoration_writes_public_fields():
    payload = {'script': [dict(r) for r in SCRIPT], 'pool_tables': {3: [dict(r) for r in TABLES[3]]}}
    sa.apply_to_payload(payload, sa.resolve(payload['script'], payload['pool_tables'], TRAINERS, GATES, RULES), GATES)
    assert [s['split_key'] for s in payload['splits']] == ['badge:33', 'badge:34', 'badge:35', 'league', 'postgame']
    assert payload['splits'][-1]['sort_to'] is None
    assert payload['split_gates'][2] == {'gate_key': 'surf', 'label': 'Surf', 'opens_in': None, 'default_methods': ['surf', 'surf-spots'], 'note': None}
    route1 = next(r for r in payload['script'] if r['event_id'] == 3)
    assert route1['home_split'] == 'badge:33' and route1['opens_in'] == 'badge:33' and route1['opens_rule'] is None
    dreamyard = next(r for r in payload['script'] if r['event_id'] == 234)
    assert dreamyard['opens_rule'] == {'opens_in': 'badge:33', 'gate_key': None, 'note': None}
    ghetsis = next(r for r in payload['script'] if r['event_id'] == 513)
    assert ghetsis['home_split'] == 'league'
    rows = {r['method']: r for r in payload['pool_tables'][3]}
    assert rows['grass-spots']['opens_in'] == 'badge:34' and rows['grass-spots']['opens_gate'] == 'shaking-grass'
    assert rows['dark-grass']['opens_unknown'] and rows['dark-grass']['opens_rule']['gate_key'] == 'surf'
    assert rows['grass']['opens_unknown'] is False


# --- database ---------------------------------------------------------------

def seed_world(conn):
    conn.execute(MIGRATION_SQL)
    conn.execute(MIGRATION_SQL)   # idempotent
    backend_module._ensure_badge_schema(conn)
    conn.execute("insert into badges (badge_id, badge_name) values (33, 'Trio Badge'), (34, 'Basic Badge') on conflict do nothing")
    conn.execute("insert into games (game_id, name, game_tag, generation, version_group_id) values (1001, 'Blaze Black', 'BB', 5, 1001), (17, 'Black', 'B', 5, 11)")
    conn.execute("insert into canon_locations (canonical_location_id, canonical_location_name) values (3, 'Route 1'), (234, 'Dreamyard'), (233, 'Striaton City')")
    for vg in (1001, 11):
        conn.execute("insert into event_locations (canonical_location_id, version_group_id, sort_order, secondary_sort_order, event_type) "
                     "values (3, %s, 1, 1, 'Location'), (233, %s, 3, 1, 'Location'), (234, %s, 4, 1, 'Location')", (vg, vg, vg))
        cress = conn.execute("insert into trainer_pool (encounter_name, trainer_name, version_group_id) values ('BB_CRESS', 'CRESS', %s) returning trainer_id", (vg,)).fetchone()['trainer_id']
        lenora = conn.execute("insert into trainer_pool (encounter_name, trainer_name, version_group_id) values ('BB_LENORA', 'LENORA', %s) returning trainer_id", (vg,)).fetchone()['trainer_id']
        conn.execute("insert into event_bosses (trainer_id, version_group_id, encounter_title, sort_order, badge_id, is_level_cap) values (%s, %s, 'Striaton City Gym', '3.2', 33, true), (%s, %s, 'Nacrene City Gym', '7.1', 34, true)", (cress, vg, lenora, vg))
    conn.execute("insert into trainer_pool (encounter_name, trainer_name, trainer_class, version_group_id, canonical_location_id) values "
                 "('TRAINER_BB_LASS_ERI', 'ERI', 'TRAINER_CLASS_LASS', 1001, 234), "
                 "('TRAINER_BB_PLASMA_GRUNT_PLASMA_GRUNT', 'PLASMA GRUNT', 'TRAINER_CLASS_PLASMA_GRUNT', 1001, 234)")
    conn.execute("insert into species (species_id, name) values (16, 'PIDGEY'), (531, 'AUDINO'), (507, 'HERDIER')")
    for species, method, rate in ((16, 'grass', 20), (531, 'grass-spots', 80), (507, 'dark-grass', 20)):
        conn.execute("insert into encounter_pool (game_id, canonical_location_id, species_id, method, enounter_rate) values ('1001', 3, %s, %s, %s)", (species, method, rate))
    conn.commit()


def make_run(conn, game_id):
    run_id = conn.execute("insert into runs (game_id, name, user_id) values (%s, 'Run', 1) returning run_id", (game_id,)).fetchone()['run_id']
    conn.execute("insert into attempts (run_id, attempt_number, starter) values (%s, 1, 'Fire')", (run_id,))
    conn.commit()
    return run_id


def test_migration_seeds_blaze_black_once(db_conn):
    seed_world(db_conn)
    gates = {g['gate_key']: g for g in sa.load_gates(db_conn, 1001)}
    assert gates['surf']['opens_in'] is None and gates['fishing']['opens_in'] == 'badge:34'
    assert gates['shaking-grass']['default_methods'] == ['grass-spots', 'cave-spots']
    rules = {(r['subject_kind'], r['subject_key']): r for r in sa.load_rules(db_conn, 1001)}
    assert rules[('table', '3||dark-grass|')]['gate_key'] == 'surf'
    assert rules[('location', '9')]['opens_in'] == 'badge:35'
    assert rules[('trainer', 'TRAINER_BB_PLASMA_GRUNT_PLASMA_GRUNT')]['opens_in'] == 'badge:34'
    assert db_conn.execute("select count(*) n from schema_migrations where migration_name = 'split_availability_v1'").fetchone()['n'] == 1
    assert sa.load_gates(db_conn, 11) == []


def test_page_and_guest_payloads_carry_splits_only_for_split_layout_games(db_conn, client, monkeypatch):
    seed_world(db_conn)
    run_id = make_run(db_conn, 1001)
    grunt = db_conn.execute("select trainer_id from trainer_pool where encounter_name = 'TRAINER_BB_PLASMA_GRUNT_PLASMA_GRUNT'").fetchone()['trainer_id']
    db_conn.execute('insert into trainers_defeated (run_id, attempt_id, trainer_id) select %s, attempt_id, %s from attempts where run_id = %s', (run_id, grunt, run_id))
    db_conn.commit()
    page = backend_module.get_attempt_page_data(db_conn, run_id, 1)
    assert [s['split_key'] for s in page['splits']] == ['badge:33', 'badge:34', 'postgame']
    assert page['split_gates'][0]['gate_key'] == 'shaking-grass'
    dreamyard = next(r for r in page['script'] if r['event_id'] == 234 and r['event_type'] == 'Location')
    assert dreamyard['home_split'] == 'badge:33'
    assert dreamyard['revisits'][0]['trainers'][0]['trainer_name'] == 'PLASMA GRUNT'
    assert dreamyard['revisits'][0]['trainers'][0]['is_defeated'] is True
    assert dreamyard['trainer_splits'] == {'badge:34': 1}
    rows = {r['method']: r for r in page['pool_tables'][3]}
    assert rows['grass-spots']['opens_in'] == 'badge:34' and rows['dark-grass']['opens_unknown']
    vanilla = backend_module.get_attempt_page_data(db_conn, make_run(db_conn, 17), 1)
    assert 'splits' not in vanilla and 'home_split' not in vanilla['script'][0]

    monkeypatch.setattr(api, 'get_db', lambda: db_conn)
    guest = client.get('/api/guest-script?game_id=1001&version_group_id=1001&starter=Fire').get_json()
    assert [s['split_key'] for s in guest['splits']] == ['badge:33', 'badge:34', 'postgame']
    assert next(r for r in guest['script'] if r['event_id'] == 234 and r['event_type'] == 'Location')['home_split'] == 'badge:33'
    trainers = client.get('/api/trainer-list/234?game_id=1001&version_group_id=1001').get_json()
    assert {t['trainer_name']: t['opens_in'] for t in trainers} == {'ERI': 'badge:33', 'PLASMA GRUNT': 'badge:34'}


def test_admin_rule_and_gate_writes(db_conn, client, monkeypatch):
    seed_world(db_conn)
    monkeypatch.setattr(api, 'get_db', lambda: db_conn)
    monkeypatch.setattr(api, 'get_current_user', lambda: {'user_id': 1, 'account_type': 'user'})
    assert client.post('/api/admin/availability', json={}).status_code == 403
    assert client.patch('/api/admin/gates', json={}).status_code == 403
    monkeypatch.setattr(api, 'get_current_user', lambda: {'user_id': 1, 'account_type': 'admin'})
    bad = client.post('/api/admin/availability', json={'game_id': 1001, 'subject_kind': 'location', 'subject_key': '3', 'opens_in': 'badge:99'})
    assert bad.status_code == 400 and 'Unknown split' in bad.get_json()['error']
    assert client.post('/api/admin/availability', json={'game_id': 1001, 'subject_kind': 'location', 'subject_key': '3', 'opens_in': 'badge:34', 'gate_key': 'surf'}).status_code == 400
    ok = client.post('/api/admin/availability', json={'game_id': 1001, 'subject_kind': 'location', 'subject_key': '3', 'opens_in': 'badge:34', 'note': 'test'})
    assert ok.status_code == 200 and ok.get_json()['opens_in'] == 'badge:34'
    page = backend_module.get_attempt_page_data(db_conn, make_run(db_conn, 1001), 1)
    assert next(r for r in page['script'] if r['event_id'] == 3 and r['event_type'] == 'Location')['home_split'] == 'badge:34'
    assert client.delete('/api/admin/availability', json={'game_id': 1001, 'subject_kind': 'location', 'subject_key': '3'}).get_json() == {'success': True}
    assert sa.load_rules(db_conn, 1001) and not any(r['subject_key'] == '3' for r in sa.load_rules(db_conn, 1001))

    gate = client.patch('/api/admin/gates', json={'game_id': 1001, 'gate_key': 'surf', 'opens_in': 'badge:34'})
    assert gate.status_code == 200 and gate.get_json()['opens_in'] == 'badge:34'
    page = backend_module.get_attempt_page_data(db_conn, make_run(db_conn, 1001), 1)
    dark = next(r for r in page['pool_tables'][3] if r['method'] == 'dark-grass')
    assert dark['opens_in'] == 'badge:34' and not dark['opens_unknown']
    assert client.patch('/api/admin/gates', json={'game_id': 1001, 'gate_key': 'surf', 'opens_in': None}).get_json()['opens_in'] is None
    assert client.patch('/api/admin/gates', json={'game_id': 1001, 'gate_key': 'nope', 'opens_in': None}).status_code == 400


PINWHEEL_SQL = (Path(__file__).parents[1] / 'migrations' / '20260925_bb_pinwheel_inside.sql').read_text(encoding='utf-8')


def test_pinwheel_interior_becomes_its_own_row(db_conn):
    seed_world(db_conn)
    c = db_conn
    c.execute("insert into canon_locations (canonical_location_id, canonical_location_name) values (237, 'Pinwheel Forest')")
    c.execute("insert into event_locations (canonical_location_id, version_group_id, sort_order, secondary_sort_order, event_type) values (237, 1001, 8, 1, 'Location')")
    c.execute("insert into badges (badge_id, badge_name) values (35, 'Insect Badge') on conflict do nothing")
    burgh = c.execute("insert into trainer_pool (encounter_name, trainer_name, version_group_id) values ('BB_BURGH', 'BURGH', 1001) returning trainer_id").fetchone()['trainer_id']
    c.execute("insert into event_bosses (trainer_id, version_group_id, encounter_title, sort_order, badge_id, is_level_cap) values (%s, 1001, 'Castelia City Gym', '9.1', 35, true)", (burgh,))
    c.execute("insert into species (species_id, name) values (532, 'TIMBURR'), (546, 'COTTONEE'), (640, 'VIRIZION'), (252, 'TREECKO'), (253, 'GROVYLE')")
    c.execute("create table if not exists evolutions (from_species_id integer, to_species_id integer, method text, detail text)")
    c.execute("insert into evolutions (from_species_id, to_species_id) values (252, 253)")
    for game in ('1001', '1002'):
        c.execute("insert into encounter_pool (game_id, canonical_location_id, species_id, method, enounter_rate, area, area_sort) values "
                  "(%s, 237, 532, 'grass', 20, 'Outside', 0), (%s, 237, 546, 'grass', 20, 'Inside', 1), (%s, 237, 252, 'grass-spots', 5, 'Inside', 1)", (game, game, game))
        c.execute("insert into encounter_pool (game_id, canonical_location_id, species_id, method, area, area_sort, slot_kind) values (%s, 237, 640, 'static', 'Rumination Field', 2, 'static')", (game,))
    c.execute("insert into trainer_pool (encounter_name, trainer_name, version_group_id, canonical_location_id) values "
              "('TRAINER_BB_YOUNGSTER_KEITA', 'KEITA', 1001, 237), ('TRAINER_BB_LASS_EVA', 'EVA', 1001, 237), ('TRAINER_BB_TEAM_PLASMA_GRUNT_TEAM_PLASMA_GRUNT', 'GRUNT', 1001, 237)")
    run_id = make_run(c, 1001)
    attempt = c.execute('select attempt_id from attempts where run_id = %s', (run_id,)).fetchone()['attempt_id']
    backend_module._ensure_bonus_locations_schema(c)
    c.execute("insert into bonus_locations (run_id, attempt_id, canonical_location_id, canonical_name, sort_order, secondary_sort_order, is_active, version_group_id) "
              "values (%s, %s, 237, 'Pinwheel Forest - Bonus', 8, 2, 1, 1001)", (run_id, attempt))
    c.execute("insert into pokebank (run_id, attempt_id, species_id, canonical_location_id, bonus_location, status) values (%s, %s, 532, 237, 1, 'Captured'), (%s, %s, 253, 237, 2, 'Dead')", (run_id, attempt, run_id, attempt))
    c.commit()

    c.execute(PINWHEEL_SQL)
    c.execute(PINWHEEL_SQL)   # idempotent
    c.commit()

    assert c.execute("select canonical_location_name from canon_locations where canonical_location_id = 504").fetchone()['canonical_location_name'] == 'Pinwheel Forest (Inside)'
    assert c.execute("select count(*) n from event_locations where canonical_location_id = 504 and version_group_id = 1001").fetchone()['n'] == 1
    rows = c.execute("select canonical_location_id lid, area, count(*) n from encounter_pool where game_id = '1001' and canonical_location_id in (237, 504) group by 1, 2 order by 1, 2 nulls first").fetchall()
    assert [(r['lid'], r['area'], r['n']) for r in rows] == [(237, None, 1), (504, None, 2), (504, 'Rumination Field', 1)]
    placed = {r['encounter_name']: r['canonical_location_id'] for r in c.execute("select encounter_name, canonical_location_id from trainer_pool where version_group_id = 1001 and encounter_name like 'TRAINER_BB_%'").fetchall()}
    assert placed['TRAINER_BB_YOUNGSTER_KEITA'] == 504 and placed['TRAINER_BB_TEAM_PLASMA_GRUNT_TEAM_PLASMA_GRUNT'] == 504 and placed['TRAINER_BB_LASS_EVA'] == 237
    assert c.execute("select canonical_location_id from curated_trainer_placements where version_group_id = 1001 and trainer_key = 'TRAINER_BB_YOUNGSTER_KEITA'").fetchone()['canonical_location_id'] == 504
    rules = {(r['subject_kind'], r['subject_key']): r['opens_in'] for r in sa.load_rules(c, 1001)}
    assert rules[('location', '237')] == 'badge:34' and rules[('location', '504')] == 'badge:35'
    assert ('area', '237|Inside') not in rules and ('area', '237|Outside') not in rules
    # The Grovyle from the extra slot is now the interior row's encounter; the Timburr stays outside.
    moved = c.execute("select species_id, canonical_location_id, bonus_location from pokebank where attempt_id = %s order by species_id", (attempt,)).fetchall()
    assert [(r['species_id'], r['canonical_location_id'], r['bonus_location']) for r in moved] == [(253, 504, 1), (532, 237, 1)]
    assert c.execute("select is_active from bonus_locations where attempt_id = %s", (attempt,)).fetchone()['is_active'] == 0

    page = backend_module.get_attempt_page_data(c, run_id, 1)
    names = {r['display_name']: r for r in page['script'] if r['event_type'] == 'Location'}
    assert names['Pinwheel Forest']['home_split'] == 'badge:34'
    assert names['Pinwheel Forest (Inside)']['home_split'] == 'badge:35'
    assert names['Pinwheel Forest']['revisits'] == []
    assert page['encounters']['504:1']['species_id'] == 253
