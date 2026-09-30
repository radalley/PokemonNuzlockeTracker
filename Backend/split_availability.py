"""Split availability: the split in which a location, an encounter area, one
wild table or a trainer becomes reachable.

Nothing in the ETL sources says when content opens, so availability is
curated data (split_gates, curated_availability) resolved over story-order
defaults. `resolve` is pure: it takes the attempt page's script, its pool
tables, the trainer roster and the two rule sets, and returns every
resolved value. Only the loaders and admin writes touch the database.

Sections (the page's chapters) come from the script's boss rows: one per
gym split, then one League section (Elite Four through the story finale),
then Postgame. Locations default to the first section whose boss follows
them in story order; areas inherit their location; a table inherits its
area but never opens before the gate its method needs (Surf, the rod);
trainers inherit their area or location. A gate without a decided split
resolves to "unknown" and is reported as such, never guessed.
"""
import math

from split_timeline import split_key, split_kind

SPLIT_LAYOUT_VERSION_GROUPS = {1001}
LEAGUE = 'league'
POSTGAME = 'postgame'
SUBJECT_KINDS = ('location', 'area', 'table', 'trainer')
_INF = float('inf')


def _num(value):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _title(text):
    words = str(text or '').replace('_', ' ').strip().lower().split()
    return ' '.join(word[:1].upper() + word[1:] for word in words)


def _truthy(value):
    return str(value or '').strip().lower() in ('1', 'true', 't', 'yes')


def _is_boss(row):
    # Boss rows carry their event_bosses id; Blaze Black's have no
    # event_type at all, so the type string is only a fallback.
    if row.get('is_bonus_location'):
        return False
    if row.get('boss_event_id') is not None:
        return True
    event_type = row.get('event_type')
    return event_type is not None and str(event_type) != 'Location'


def _is_location(row):
    return not _is_boss(row) and row.get('event_id') is not None


def _boss_identity(row):
    kind = split_kind({'event_type': row.get('event_type'), 'encounter_title': row.get('display_name'), 'badge_id': row.get('badge_id')})
    key = split_key({'badge_id': row.get('badge_id'), 'encounter_name': row.get('encounter_name')})
    return kind, key


def build_sections(script):
    """The page's sections, in order, from the starter-filtered script.

    Each carries `split_key` (a gym's `badge:<id>` / `boss:<name>`, then
    `league`, then `postgame`), `ordinal`, `sort_to` (the boss sort_order
    that closes it), the leader's display fields, `final_trainer_id` (the
    fight that completes it), and the trainer/boss event ids inside it.
    The League closes with the last boss sharing the Elite Four's integer
    sort slot (Blaze Black: N 32.5 and Ghetsis 32.6 after the E4 at 32.x);
    Postgame is revealed once the League's final fight is won.
    """
    bosses = [row for row in script if _is_boss(row)]
    bosses.sort(key=lambda r: _num(r.get('sort_order')) if _num(r.get('sort_order')) is not None else _INF)
    sections, seen = [], set()
    for row in bosses:
        kind, key = _boss_identity(row)
        if kind != 'gym' or not key or key in seen:
            continue
        seen.add(key)
        sections.append({
            'split_key': key, 'kind': 'gym', 'sort_to': _num(row.get('sort_order')) or 0.0,
            'label': _title(row.get('trainer_name') or row.get('display_name')),
            'title': row.get('display_name'), 'type_focus': row.get('type_focus'),
            'badge_id': row.get('badge_id'), 'battle_type': row.get('battle_type'),
            'level_cap': row.get('level_cap'), 'final_trainer_id': row.get('event_id'),
            'trainer_ids': [], 'boss_event_ids': [], 'reveal_after': None,
        })
    league_anchor = None
    for row in bosses:
        kind, _ = _boss_identity(row)
        if kind == 'elite_four':
            league_anchor = row
    if league_anchor is None:
        league_anchor = next((row for row in bosses if _boss_identity(row)[0] == 'champion'), None)
    last_gym_sort = sections[-1]['sort_to'] if sections else -_INF
    if league_anchor is not None and (_num(league_anchor.get('sort_order')) or 0.0) > last_gym_sort:
        slot = math.floor(_num(league_anchor.get('sort_order')) or 0.0)
        in_slot = [row for row in bosses
                   if (_num(row.get('sort_order')) or 0.0) > last_gym_sort
                   and math.floor(_num(row.get('sort_order')) or 0.0) <= slot]
        final = in_slot[-1]
        e4_caps = [row.get('level_cap') for row in in_slot if _boss_identity(row)[0] == 'elite_four' and row.get('level_cap') is not None]
        sections.append({
            'split_key': LEAGUE, 'kind': LEAGUE, 'sort_to': _num(final.get('sort_order')) or 0.0,
            'label': 'Pokémon League', 'title': 'Pokémon League', 'type_focus': None,
            'badge_id': None, 'battle_type': None,
            'level_cap': max(e4_caps) if e4_caps else final.get('level_cap'),
            'final_trainer_id': final.get('event_id'),
            'trainer_ids': [], 'boss_event_ids': [], 'reveal_after': None,
        })
    sections.append({
        'split_key': POSTGAME, 'kind': POSTGAME, 'sort_to': _INF,
        'label': 'Postgame', 'title': 'Postgame', 'type_focus': None,
        'badge_id': None, 'battle_type': None, 'level_cap': None, 'final_trainer_id': None,
        'trainer_ids': [], 'boss_event_ids': [],
        'reveal_after': sections[-1]['split_key'] if sections else None,
    })
    for index, section in enumerate(sections):
        section['ordinal'] = index
    for row in bosses:
        section = section_for_sort(sections, _num(row.get('sort_order')))
        if row.get('event_id') is not None:
            section['trainer_ids'].append(row['event_id'])
        if row.get('boss_event_id') is not None:
            section['boss_event_ids'].append(row['boss_event_id'])
        if section['kind'] == POSTGAME and row.get('is_level_cap') and row.get('level_cap') is not None:
            section['level_cap'] = max(section['level_cap'] or 0, row['level_cap'])
            if _boss_identity(row)[0] == 'champion':
                section['final_trainer_id'] = row.get('event_id')
    return sections


def section_for_sort(sections, sort_order):
    value = sort_order if sort_order is not None else 0.0
    for section in sections:
        if section['sort_to'] >= value:
            return section
    return sections[-1]


def _resolved(opens_in=None, gate_key=None, ordinal=None, unknown=False, rule=None):
    return {'opens_in': opens_in, 'gate_key': gate_key, 'ordinal': ordinal, 'unknown': unknown, 'rule': rule}


def table_key(location_id, area, method, condition):
    return f"{int(location_id)}|{area or ''}|{method or ''}|{condition or ''}"


def area_key(location_id, area):
    return f"{int(location_id)}|{area}"


class _Resolver:
    def __init__(self, sections, gates, rules):
        self.sections = sections
        self.ordinal_of = {s['split_key']: s['ordinal'] for s in sections}
        self.gates = {g['gate_key']: g for g in gates}
        self.gate_for_method = {}
        for gate in sorted(gates, key=lambda g: (g.get('sort_order') or 0, g['gate_key'])):
            for method in gate.get('default_methods') or []:
                self.gate_for_method.setdefault(method, gate['gate_key'])
        self.rules = {(r['subject_kind'], r['subject_key']): r for r in rules}

    def register_boss_keys(self, script):
        for row in script:
            if not _is_boss(row):
                continue
            _, key = _boss_identity(row)
            if key and key not in self.ordinal_of:
                self.ordinal_of[key] = section_for_sort(self.sections, _num(row.get('sort_order')))['ordinal']

    def from_key(self, opens_in, rule=None):
        ordinal = self.ordinal_of.get(opens_in)
        if ordinal is None:
            return _resolved(unknown=True, rule=rule)
        return _resolved(opens_in=opens_in, ordinal=ordinal, rule=rule)

    def from_gate(self, gate_key, rule=None):
        gate = self.gates.get(gate_key)
        if not gate or not gate.get('opens_in') or gate['opens_in'] not in self.ordinal_of:
            return _resolved(gate_key=gate_key, unknown=True, rule=rule)
        return _resolved(opens_in=gate['opens_in'], gate_key=gate_key, ordinal=self.ordinal_of[gate['opens_in']], rule=rule)

    def from_rule(self, rule):
        if rule.get('gate_key'):
            return self.from_gate(rule['gate_key'], rule)
        return self.from_key(rule.get('opens_in'), rule)

    def rule_for(self, kind, key):
        return self.rules.get((kind, key))

    def later(self, base, other):
        """The later of two resolutions; an unknown side wins (still unknown)."""
        if other['unknown']:
            return _resolved(gate_key=other['gate_key'], unknown=True)
        if base['unknown']:
            return base
        return other if other['ordinal'] > base['ordinal'] else base


def resolve(script, tables_by_location, trainers, gates, rules):
    """Pure resolution. Returns splits, per-location results (home split,
    own availability, areas, revisits, trainer counts per later split),
    per-table and per-trainer results, and each boss's split."""
    sections = build_sections(script)
    resolver = _Resolver(sections, gates, rules)
    resolver.register_boss_keys(script)
    # Canonical rows first: a bonus row shares its base location's id and
    # sort, so it never decides the location's default on its own.
    location_sort = {}
    for row in script:
        if _is_location(row) and not row.get('is_bonus_location'):
            location_sort.setdefault(int(row['event_id']), _num(row.get('sort_order')))
    for row in script:
        if _is_location(row):
            location_sort.setdefault(int(row['event_id']), _num(row.get('sort_order')))

    locations, tables, trainer_results = {}, {}, {}
    for lid, sort_order in location_sort.items():
        default = section_for_sort(sections, sort_order)
        rule = resolver.rule_for('location', str(lid))
        own = resolver.from_rule(rule) if rule else _resolved(opens_in=default['split_key'], ordinal=default['ordinal'])
        base = own if not own['unknown'] else _resolved(opens_in=default['split_key'], ordinal=default['ordinal'])
        areas = {}
        for row in tables_by_location.get(lid) or tables_by_location.get(str(lid)) or []:
            area = row.get('area') or None
            if area is not None and area not in areas:
                area_rule = resolver.rule_for('area', area_key(lid, area))
                areas[area] = resolver.from_rule(area_rule) if area_rule else base
        table_rows = {}
        for row in tables_by_location.get(lid) or tables_by_location.get(str(lid)) or []:
            key = table_key(lid, row.get('area'), row.get('method'), row.get('condition'))
            if key in table_rows:
                continue
            table_rule = resolver.rule_for('table', key)
            if table_rule:
                result = resolver.from_rule(table_rule)
            else:
                parent = areas.get(row.get('area') or None, base)
                gate_key = resolver.gate_for_method.get(row.get('method'))
                result = resolver.later(parent, resolver.from_gate(gate_key)) if gate_key else parent
            table_rows[key] = result
            tables[key] = result
        known = [r['ordinal'] for r in [own, *areas.values()] if not r['unknown']]
        home_ordinal = min(known) if known else default['ordinal']
        locations[lid] = {
            'home_split': sections[home_ordinal]['split_key'], 'home_ordinal': home_ordinal,
            'own': own, 'areas': areas, 'tables': table_rows,
            'revisits': {}, 'trainer_splits': {},
        }

    for trainer in trainers:
        lid = trainer.get('canonical_location_id')
        if lid is None:
            continue
        lid = int(lid)
        info = locations.get(lid)
        if info is None:
            continue
        # A trainer's own rule, else the rule of the encounter area sharing
        # its area name, else the split its location row lives in (the home
        # split, the earliest access), so an uncurated roster is shown with
        # its row rather than listed as a return in a later section.
        rule = resolver.rule_for('trainer', trainer.get('encounter_name') or '')
        if rule:
            result = resolver.from_rule(rule)
        else:
            area_name = trainer.get('area_name')
            area_rule = resolver.rule_for('area', area_key(lid, area_name)) if area_name else None
            result = resolver.from_rule(area_rule) if area_rule else _resolved(opens_in=info['home_split'], ordinal=info['home_ordinal'])
        trainer_results[int(trainer['trainer_id'])] = result
        special = _truthy(trainer.get('is_event')) or _truthy(trainer.get('is_rematch'))
        if not result['unknown'] and result['ordinal'] > info['home_ordinal'] and not special:
            key = sections[result['ordinal']]['split_key']
            info['trainer_splits'][key] = info['trainer_splits'].get(key, 0) + 1
            info['revisits'].setdefault(key, {'split_key': key, 'tables': [], 'areas': [], 'trainers': []})['trainers'].append({
                'trainer_id': trainer['trainer_id'], 'encounter_name': trainer.get('encounter_name'),
                'trainer_name': trainer.get('trainer_name'), 'trainer_class': trainer.get('trainer_class'),
                'max_level': trainer.get('max_level'),
            })

    for lid, info in locations.items():
        rows = tables_by_location.get(lid) or tables_by_location.get(str(lid)) or []
        seen_tables = set()
        for area, result in info['areas'].items():
            if not result['unknown'] and result['ordinal'] > info['home_ordinal']:
                key = sections[result['ordinal']]['split_key']
                info['revisits'].setdefault(key, {'split_key': key, 'tables': [], 'areas': [], 'trainers': []})['areas'].append(area)
        for row in rows:
            key = table_key(lid, row.get('area'), row.get('method'), row.get('condition'))
            if key in seen_tables:
                continue
            seen_tables.add(key)
            result = info['tables'][key]
            if result['unknown'] or result['ordinal'] <= info['home_ordinal']:
                continue
            split = sections[result['ordinal']]['split_key']
            entry = info['revisits'].setdefault(split, {'split_key': split, 'tables': [], 'areas': [], 'trainers': []})
            rare = [{'species_id': r.get('species_id'), 'name': r.get('name'), 'rate': r.get('rate'), 'slot_kind': r.get('slot_kind')}
                    for r in rows if table_key(lid, r.get('area'), r.get('method'), r.get('condition')) == key and r.get('slot_kind') in ('overlay', 'static')]
            entry['tables'].append({'area': row.get('area'), 'method': row.get('method'), 'condition': row.get('condition'), 'rare': rare})
        info['revisits'] = sorted(info['revisits'].values(), key=lambda e: resolver.ordinal_of[e['split_key']])

    bosses = {}
    for row in script:
        if _is_boss(row) and row.get('event_id') is not None:
            bosses[int(row['event_id'])] = section_for_sort(sections, _num(row.get('sort_order')))['split_key']
    return {'splits': sections, 'locations': locations, 'tables': tables, 'trainers': trainer_results, 'bosses': bosses}


def _public(result):
    return {
        'opens_in': result['opens_in'], 'opens_gate': result['gate_key'],
        'opens_unknown': bool(result['unknown']), 'opens_rule': _public_rule(result['rule']),
    }


def _public_rule(rule):
    if not rule:
        return None
    return {'opens_in': rule.get('opens_in'), 'gate_key': rule.get('gate_key'), 'note': rule.get('note')}


def _public_section(section):
    public = {k: v for k, v in section.items() if k != 'sort_to'}
    public['sort_to'] = None if section['sort_to'] == _INF else section['sort_to']
    return public


def apply_to_payload(payload, result, gates):
    """Write the resolution onto a page payload (script rows, pool tables)."""
    payload['splits'] = [_public_section(s) for s in result['splits']]
    payload['split_gates'] = [
        {'gate_key': g['gate_key'], 'label': g['label'], 'opens_in': g.get('opens_in'),
         'default_methods': list(g.get('default_methods') or []), 'note': g.get('note')}
        for g in sorted(gates, key=lambda g: (g.get('sort_order') or 0, g['gate_key']))
    ]
    for row in payload.get('script') or []:
        if _is_boss(row):
            row['home_split'] = result['bosses'].get(int(row['event_id'])) if row.get('event_id') is not None else None
            continue
        if not _is_location(row):
            continue
        info = result['locations'].get(int(row['event_id']))
        if not info:
            continue
        row['home_split'] = info['home_split']
        row.update(_public(info['own']))
        row['areas'] = [{'area': area, **_public(res)} for area, res in info['areas'].items()]
        row['revisits'] = info['revisits']
        row['trainer_splits'] = info['trainer_splits']
    for lid, rows in (payload.get('pool_tables') or {}).items():
        for row in rows:
            res = result['tables'].get(table_key(lid, row.get('area'), row.get('method'), row.get('condition')))
            if res:
                row.update(_public(res))
    return payload


def apply_to_trainers(rows, result):
    out = []
    for row in rows:
        item = dict(row)
        res = result['trainers'].get(int(item['trainer_id'])) if item.get('trainer_id') is not None else None
        if res:
            item.update(_public(res))
        out.append(item)
    return out


# --- database ---------------------------------------------------------------

def _tables_ready(conn):
    return conn.execute(
        "select to_regclass('public.split_gates') is not null and to_regclass('public.curated_availability') is not null as ready"
    ).fetchone()['ready']


def load_gates(conn, version_group_id):
    if version_group_id is None or not _tables_ready(conn):
        return []
    return [dict(r) for r in conn.execute(
        'select * from split_gates where version_group_id = %s order by sort_order, gate_key', (version_group_id,)
    ).fetchall()]


def load_rules(conn, version_group_id):
    if version_group_id is None or not _tables_ready(conn):
        return []
    return [dict(r) for r in conn.execute(
        'select * from curated_availability where version_group_id = %s', (version_group_id,)
    ).fetchall()]


def load_trainers(conn, version_group_id, game_id, location_ids):
    """The regular roster (bosses excluded) with each trainer's top level."""
    ids = sorted({int(x) for x in location_ids if x is not None})
    if not ids or version_group_id is None:
        return []
    placeholders = ','.join(['%s'] * len(ids))
    game_clause = 'and (tp.game_id is null or tp.game_id = %s) ' if game_id is not None else 'and tp.game_id is null '
    params = [*ids, version_group_id, *([game_id] if game_id is not None else [])]
    return [dict(r) for r in conn.execute(
        'select tp.trainer_id, tp.encounter_name, tp.trainer_name, tp.trainer_class, tp.canonical_location_id, '
        'tp.is_event, tp.is_rematch, la.area_name, '
        '(select max(nullif(t.lvl::text, \'\')::integer) from trainer_pokemon t where t.trainer_id = tp.trainer_id) as max_level '
        'from trainer_pool tp left join location_areas la on la.area_id = tp.area_id '
        f'where tp.canonical_location_id in ({placeholders}) and tp.version_group_id = %s '
        f'{game_clause}'
        'and not exists (select 1 from event_bosses eb where eb.trainer_id = tp.trainer_id and eb.version_group_id = tp.version_group_id) '
        'order by tp.trainer_id', params
    ).fetchall()]


def decorate_page(conn, payload, game_id, version_group_id, starter=None, defeated_ids=None):
    """Attach splits and availability to an attempt page (or guest) payload
    for split-layout games; every other game's payload is returned as is.
    `defeated_ids` marks returning trainers already beaten (guests mark
    theirs client-side)."""
    if version_group_id is None or int(version_group_id) not in SPLIT_LAYOUT_VERSION_GROUPS:
        return payload
    script = payload.get('script') or []
    location_ids = {int(r['event_id']) for r in script if _is_location(r)}
    gates = load_gates(conn, version_group_id)
    rules = load_rules(conn, version_group_id)
    trainers = load_trainers(conn, version_group_id, game_id, location_ids)
    result = resolve(script, payload.get('pool_tables') or {}, trainers, gates, rules)
    defeated = {int(x) for x in (defeated_ids or [])}
    for info in result['locations'].values():
        for revisit in info['revisits']:
            for trainer in revisit['trainers']:
                trainer['is_defeated'] = int(trainer['trainer_id']) in defeated
    return apply_to_payload(payload, result, gates)


def annotate_trainers(conn, rows, location_id, game_id, version_group_id, starter=None):
    """opens_in for a location's trainer list (the /api/trainer-list route).
    The list rows carry no location id of their own; the route's is used."""
    if version_group_id is None or int(version_group_id) not in SPLIT_LAYOUT_VERSION_GROUPS or not rows:
        return [dict(r) for r in rows]
    from backend import get_script  # backend imports this module; bind late
    script = [dict(r) for r in get_script(conn, starter or 'Fire', version_group_id=version_group_id, game_id=game_id)]
    trainers = [{**dict(r), 'canonical_location_id': location_id} for r in rows]
    result = resolve(script, {}, trainers, load_gates(conn, version_group_id), load_rules(conn, version_group_id))
    return apply_to_trainers(rows, result)


def valid_split_keys(conn, game_id):
    """Every key opens_in may name for a game: each section, each boss key."""
    from backend import get_script
    game = conn.execute('select version_group_id from games where game_id = %s', (game_id,)).fetchone()
    if not game:
        raise ValueError('Game not found')
    keys = set()
    for starter in ('Fire', 'Grass', 'Water'):
        script = [dict(r) for r in get_script(conn, starter, version_group_id=game['version_group_id'], game_id=game_id)]
        for section in build_sections(script):
            keys.add(section['split_key'])
        for row in script:
            if _is_boss(row):
                _, key = _boss_identity(row)
                if key:
                    keys.add(key)
    return keys, game['version_group_id']


def _check_subject(kind, key):
    if kind not in SUBJECT_KINDS:
        raise ValueError('Unknown subject kind')
    if not isinstance(key, str) or not 1 <= len(key) <= 240:
        raise ValueError('Subject key must be 1-240 characters')
    parts = key.split('|')
    expected = {'location': 1, 'area': 2, 'table': 4, 'trainer': 1}[kind]
    if len(parts) != expected:
        raise ValueError(f'A {kind} key has {expected} part(s)')
    if kind in ('location', 'area', 'table'):
        int(parts[0])


def save_rule(conn, game_id, subject_kind, subject_key, opens_in=None, gate_key=None, note=None):
    _check_subject(subject_kind, subject_key)
    if bool(opens_in) == bool(gate_key):
        raise ValueError('Choose either a split or a gate')
    keys, version_group_id = valid_split_keys(conn, game_id)
    if opens_in and opens_in not in keys:
        raise ValueError('Unknown split for this game')
    if gate_key and gate_key not in {g['gate_key'] for g in load_gates(conn, version_group_id)}:
        raise ValueError('Unknown gate for this game')
    row = conn.execute(
        'insert into curated_availability(version_group_id, subject_kind, subject_key, opens_in, gate_key, note, source) '
        "values (%s, %s, %s, %s, %s, %s, 'admin') "
        'on conflict (version_group_id, subject_kind, subject_key) do update set opens_in = excluded.opens_in, '
        'gate_key = excluded.gate_key, note = excluded.note, source = excluded.source, decided_at = current_timestamp '
        'returning *',
        (version_group_id, subject_kind, subject_key, opens_in or None, gate_key or None, (note or '').strip()[:500] or None),
    ).fetchone()
    conn.commit()
    return dict(row)


def delete_rule(conn, game_id, subject_kind, subject_key):
    _check_subject(subject_kind, subject_key)
    _, version_group_id = valid_split_keys(conn, game_id)
    conn.execute(
        'delete from curated_availability where version_group_id = %s and subject_kind = %s and subject_key = %s',
        (version_group_id, subject_kind, subject_key),
    )
    conn.commit()


def save_gate(conn, game_id, gate_key, opens_in=None, note=None):
    keys, version_group_id = valid_split_keys(conn, game_id)
    if opens_in and opens_in not in keys:
        raise ValueError('Unknown split for this game')
    row = conn.execute(
        'update split_gates set opens_in = %s, note = coalesce(%s, note) where version_group_id = %s and gate_key = %s returning *',
        (opens_in or None, (note or '').strip()[:500] or None, version_group_id, gate_key),
    ).fetchone()
    if not row:
        raise ValueError('Unknown gate for this game')
    conn.commit()
    return dict(row)
