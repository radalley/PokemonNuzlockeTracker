"""One-off import of the personal Blaze Black tracking sheet.

Reads the gitignored workbook (imports/Dalley - Nerd.xlsx, sheet
'Blaze Black Nuzlocke') and brings two datasets into Lockley WITHOUT
touching any trainer data:

1. The right-hand attempt history (runs 5..17): appended to the FRONT of
   the given run. Existing attempts are renumbered upward (their in-play
   attempt keeps its identity, just a higher number), imported attempts
   arrive as dead attempts with the sheet's death notes, and each carries
   its per-location Captured/Missed encounters (nickname + species),
   including the sheet's two bonus columns as bonus locations.
2. The left-hand trainer intel: observed moves recorded per party slot,
   inserted through backend.add_observed_move (the admin move editor's
   path -- canonicalized, validated, idempotent). Ability notes are
   recognized against the ability vocabulary and skipped; bosses are
   skipped (their doc movesets are already exact).

Dry run by default: prints the full resolution report (species/move/
trainer matches incl. fuzzy corrections) and writes nothing.

    python -m etl.pipelines.import_bb_sheet "..\\imports\\Dalley - Nerd.xlsx" --run-id 61
    python -m etl.pipelines.import_bb_sheet "..\\imports\\Dalley - Nerd.xlsx" --run-id 61 --apply
"""
import argparse
import difflib
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

SHEET = 'Blaze Black Nuzlocke'
VERSION_GROUP_ID = 1001

# Right block: (nickname_col, species_col) -> location. 'bonus_of' entries
# become per-attempt bonus locations under their canonical parent.
RUN_COLUMNS = [
    ('J', 'K', {'canon': 1, 'name': 'Starter'}),
    ('L', 'M', {'canon': 3, 'name': 'Route 1'}),
    ('N', 'O', {'canon': 6, 'name': 'Route 2'}),
    ('P', 'Q', {'canon': 234, 'name': 'Dreamyard - Gift', 'bonus_of': 234}),
    ('R', 'S', {'canon': 234, 'name': 'Dreamyard'}),
    ('T', 'U', {'canon': 235, 'name': 'Wellspring Cave'}),
    ('V', 'W', {'canon': 8, 'name': 'Route 3'}),
    ('X', 'Y', {'canon': 233, 'name': 'Striaton City'}),
    ('Z', 'AA', {'canon': 237, 'name': 'Pinwheel Forest'}),
    ('AB', 'AC', {'canon': 237, 'name': 'Inner Pinwheel Forest', 'bonus_of': 237}),
]

STARTER_BRANCH = {'TEPIG': 'Fire', 'SNIVY': 'Grass', 'OSHAWOTT': 'Water'}

# Left block section header -> canonical location (vg 1001 script ids).
SECTION_CANON = {
    'nuvema town': 496, 'route 1': 3, 'accumula town': 497, 'route 2': 6,
    'dreamyard': 234, 'striation city': 233, 'striaton city': 233,
    'route 3': 8, 'double battle': 8, 'wellspring cave': 235,
    'nacrene city': 236, 'pinwheel forest': 237,
    'pinwheel forest interior': 237, 'castelia city': 238, 'route 4': 9,
    'desert resort': 239, 'relic castle': 240, 'nimbasa city': 492,
    'route 16': 29, 'route 5': 14, 'cold storage': 242,
    'driftveil city': 241, 'route 6': 15, 'chargestone cave': 244,
    'route 7': 25, 'celestial tower': 246, 'mistralton city': 493,
    'route 17': 30, 'route 18': 31, 'mistralton cave': 243,
    'twist mountain': 247, 'icirrus city': 498, 'route 8': 24,
    'moor of icirrus': 499, 'dragonspiral tower': 249,
    'tubeline bridge': 500, 'route 9': 19, 'opelucid city': 494,
    'route 10': 20, 'victory road': 48,
}

PARTY_CELL = re.compile(r'^\s*(?P<species>[A-Za-z][A-Za-z .\'♀♂-]*?)\s*L\s*(?P<level>\d+)\s*$')
MISSED_CELL = re.compile(r'^\s*missed\s+(?P<species>[A-Za-z\'♀♂ .-]+?)\s*(\((?P<why>[^)]*)\))?\s*$', re.IGNORECASE)


def norm(text):
    return re.sub(r'[^a-z0-9]', '', str(text or '').lower())


class Resolver:
    def __init__(self, conn):
        self.conn = conn
        rows = conn.execute('select species_id, name from species').fetchall()
        self.species_by_norm = {norm(r['name']): (r['species_id'], r['name']) for r in rows}
        self.species_norms = list(self.species_by_norm.keys())
        move_rows = conn.execute('select distinct move_name from moves').fetchall()
        self.moves_by_norm = {norm(r['move_name']): r['move_name'] for r in move_rows}
        self.move_norms = list(self.moves_by_norm.keys())
        ability_rows = conn.execute(
            'select distinct ability from ('
            '  select ability1 as ability from species_abilities union '
            '  select ability2 from species_abilities union '
            '  select ability3 from species_abilities) x where ability is not null'
        ).fetchall()
        self.ability_norms = {norm(r['ability']) for r in ability_rows}
        self.species_fuzzy, self.move_fuzzy = [], []
        self.species_fail, self.move_fail = [], []

    def species(self, raw):
        key = norm(raw)
        if not key:
            return None
        if key in self.species_by_norm:
            return self.species_by_norm[key]
        close = difflib.get_close_matches(key, self.species_norms, n=1, cutoff=0.8)
        if close:
            hit = self.species_by_norm[close[0]]
            self.species_fuzzy.append((str(raw).strip(), hit[1]))
            return hit
        self.species_fail.append(str(raw).strip())
        return None

    def classify_cell(self, raw):
        """'ability' | ('move', canonical) | None (unresolved)."""
        key = norm(raw)
        if not key:
            return None
        if key in self.moves_by_norm:
            return ('move', self.moves_by_norm[key])
        if key in self.ability_norms:
            return 'ability'
        close = difflib.get_close_matches(key, self.move_norms, n=1, cutoff=0.85)
        if close:
            self.move_fuzzy.append((str(raw).strip(), self.moves_by_norm[close[0]]))
            return ('move', self.moves_by_norm[close[0]])
        if difflib.get_close_matches(key, list(self.ability_norms), n=1, cutoff=0.85):
            return 'ability'
        self.move_fail.append(str(raw).strip())
        return None


def parse_attempts(ws, resolver):
    attempts = []
    for r in range(4, 60):
        run_no = ws.cell(r, 9).value
        if run_no in (None, ''):
            continue
        note = ws.cell(r, 8).value
        entry = {'sheet_run': int(float(run_no)), 'note': (str(note).strip() if note else None),
                 'starter_branch': None, 'encounters': []}
        for nick_col, spec_col, loc in RUN_COLUMNS:
            nick = ws[f'{nick_col}{r}'].value
            spec = ws[f'{spec_col}{r}'].value
            nick = str(nick).strip() if nick not in (None, '') else None
            spec = str(spec).strip() if spec not in (None, '') else None
            if not nick and not spec:
                continue
            missed = MISSED_CELL.match(nick or '')
            if missed:
                hit = resolver.species(missed.group('species'))
                if hit:
                    entry['encounters'].append({'loc': loc, 'status': 'Missed',
                                                'species_id': hit[0], 'species_name': hit[1],
                                                'nickname': None})
                continue
            if not spec:
                resolver.species_fail.append(f'run {entry["sheet_run"]} {loc["name"]}: nickname {nick!r} without species')
                continue
            hit = resolver.species(spec)
            if not hit:
                continue
            if loc['name'] == 'Starter':
                entry['starter_branch'] = STARTER_BRANCH.get(hit[1].upper(), 'Fire')
            entry['encounters'].append({'loc': loc, 'status': 'Captured',
                                        'species_id': hit[0], 'species_name': hit[1],
                                        'nickname': nick})
        attempts.append(entry)
    return attempts


def parse_trainer_moves(ws, resolver):
    """[{section, canon, name, party: {col: (species norm, level)}, moves: {col: [move]}}]"""
    trainers = []
    current_section = None
    current = None
    for r in range(4, 620):
        a = ws.cell(r, 1).value
        a_text = str(a).strip() if a not in (None, '') else ''
        row_party = {}
        for c in range(2, 8):
            v = ws.cell(r, c).value
            if v in (None, ''):
                continue
            m = PARTY_CELL.match(str(v))
            if m:
                row_party[c] = (m.group('species').strip(), int(m.group('level')))
        low = a_text.lower().rstrip()
        if low in SECTION_CANON:
            current_section = (a_text, SECTION_CANON[low])
            current = None
            continue
        if a_text and row_party and current_section:
            name = a_text.split(':')[0].strip()
            if name.startswith('*') or a_text.strip() == '---':
                current = None  # bosses: doc-exact movesets already
                continue
            current = {'section': current_section[0], 'canon': current_section[1],
                       'name': name, 'party': dict(row_party), 'cells': {c: [] for c in row_party}}
            trainers.append(current)
            continue
        if a_text in ('---',) or (a_text and not row_party):
            if a_text.split(':')[0].strip().startswith('*'):
                current = None
            elif a_text and ':' in a_text and current_section:
                current = None  # inline party-only lines without B..G cells
            elif a_text and re.match(r'^(Item|Ability|Move)', a_text):
                current = None  # labeled boss grid
            elif a_text:
                current = None
            continue
        if current and not a_text:
            for c in range(2, 8):
                v = ws.cell(r, c).value
                if v in (None, ''):
                    continue
                if c in current['cells']:
                    current['cells'][c].append(str(v).strip())
    return trainers


def match_trainers(conn, trainers, resolver):
    matched, unmatched, ambiguous = [], [], []
    party_select = (
        'select tp.trainer_id, tp.trainer_name, tp.trainer_class, '
        "(select string_agg(tpk.species_name || '|' || tpk.slot, ',' order by tpk.slot) "
        ' from trainer_pokemon tpk where tpk.trainer_id = tp.trainer_id) as party '
        'from trainer_pool tp ')
    for t in trainers:
        rows = conn.execute(
            party_select + 'where tp.version_group_id = %s and tp.canonical_location_id = %s',
            (VERSION_GROUP_ID, t['canon'])
        ).fetchall()
        # A section can span neighbouring venues (the sheet's "Double Battle"
        # block mixes Route 3 and Nacrene Gym): fall back to a name match
        # across the whole roster, still verified by party overlap below.
        sheet_last_name = t['name'].split()[-1].upper()
        name_rows = conn.execute(
            party_select + 'where tp.version_group_id = %s and upper(tp.trainer_name) = %s',
            (VERSION_GROUP_ID, sheet_last_name)
        ).fetchall()
        seen_ids = {r['trainer_id'] for r in rows}
        rows = list(rows) + [r for r in name_rows if r['trainer_id'] not in seen_ids]
        sheet_species = [norm(sp) for sp, _ in t['party'].values()]
        best = []
        for row in rows:
            db_party = {}
            for token in (row['party'] or '').split(','):
                if '|' in token:
                    sp, slot = token.rsplit('|', 1)
                    db_party[norm(sp)] = int(slot)
            overlap = sum(1 for sp in sheet_species if sp in db_party)
            if overlap and overlap >= max(1, len(sheet_species) - 1):
                best.append((overlap, row, db_party))
        best.sort(key=lambda x: -x[0])
        if not best:
            unmatched.append(f"{t['section']}: {t['name']} ({', '.join(sp for sp, _ in t['party'].values())})")
            continue
        if len(best) > 1 and best[0][0] == best[1][0] and best[0][1]['trainer_id'] != best[1][1]['trainer_id']:
            names = {b[1]['trainer_name'] for b in best if b[0] == best[0][0]}
            sheet_last = t['name'].split()[-1].upper()
            exact = [b for b in best if b[0] == best[0][0] and (b[1]['trainer_name'] or '').upper() == sheet_last]
            if len(exact) == 1:
                best = exact
            else:
                ambiguous.append(f"{t['section']}: {t['name']} -> {sorted(names)}")
                continue
        _, row, db_party = best[0]
        moves = []
        for col, cells in t['cells'].items():
            sheet_sp = norm(t['party'][col][0])
            slot = db_party.get(sheet_sp)
            if slot is None:
                continue
            for cell in cells:
                kind = resolver.classify_cell(cell)
                if isinstance(kind, tuple):
                    moves.append({'slot': slot, 'move': kind[1], 'species': t['party'][col][0]})
        if moves:
            matched.append({'trainer_id': row['trainer_id'], 'label': f"{t['name']} ({row['trainer_name']})",
                            'section': t['section'], 'moves': moves})
    return matched, unmatched, ambiguous


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('xlsx')
    parser.add_argument('--run-id', type=int, required=True)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()

    from openpyxl import load_workbook
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), '..', '..', '.env'))
    import psycopg2
    import backend

    conn = backend.wrap_conn(psycopg2.connect(os.environ['DATABASE_URL']))
    run = conn.execute(
        'select r.run_id, g.version_group_id from runs r '
        'join games g on nullif(r.game_id::text, \'\')::integer = g.game_id where r.run_id = %s',
        (args.run_id,)).fetchone()
    if not run or run['version_group_id'] != VERSION_GROUP_ID:
        print(f'run {args.run_id} is not a Blaze Black run', file=sys.stderr)
        raise SystemExit(1)

    ws = load_workbook(args.xlsx, data_only=True)[SHEET]
    resolver = Resolver(conn)
    attempts = parse_attempts(ws, resolver)
    trainers = parse_trainer_moves(ws, resolver)
    matched, unmatched, ambiguous = match_trainers(conn, trainers, resolver)

    print(f'=== ATTEMPTS: {len(attempts)} (sheet runs {attempts[0]["sheet_run"]}..{attempts[-1]["sheet_run"]}) ===')
    for a in attempts:
        caught = sum(1 for e in a['encounters'] if e['status'] == 'Captured')
        missed = sum(1 for e in a['encounters'] if e['status'] == 'Missed')
        print(f"  sheet run {a['sheet_run']}: starter={a['starter_branch']} caught={caught} missed={missed}"
              + (f" note={a['note']!r}" if a['note'] else ''))
    total_moves = sum(len(m['moves']) for m in matched)
    print(f'\n=== OBSERVED MOVES: {total_moves} moves across {len(matched)} matched trainers ===')
    for m in matched:
        print(f"  {m['section']}: {m['label']}: " + ', '.join(f"{x['move']} (slot {x['slot']})" for x in m['moves']))
    if unmatched:
        print(f'\n-- unmatched trainers ({len(unmatched)}):')
        for u in unmatched:
            print('   ', u)
    if ambiguous:
        print(f'\n-- ambiguous trainers ({len(ambiguous)}):')
        for u in ambiguous:
            print('   ', u)
    if resolver.species_fuzzy:
        print(f'\n-- species fuzzy-corrected: {sorted(set(resolver.species_fuzzy))}')
    if resolver.species_fail:
        print(f'-- species UNRESOLVED: {sorted(set(resolver.species_fail))}')
    if resolver.move_fuzzy:
        print(f'-- moves fuzzy-corrected: {sorted(set(resolver.move_fuzzy))}')
    if resolver.move_fail:
        print(f'-- move/ability cells UNRESOLVED (skipped): {sorted(set(resolver.move_fail))}')

    if not args.apply:
        print('\nDRY RUN: nothing written. Re-run with --apply.')
        return

    shift = len(attempts)
    cur = conn.execute('select attempt_number from attempts where run_id = %s order by attempt_number desc',
                       (args.run_id,)).fetchall()
    for row in cur:  # descending: no transient collisions
        conn.execute('update attempts set attempt_number = %s where run_id = %s and attempt_number = %s',
                     (row['attempt_number'] + shift, args.run_id, row['attempt_number']))
    conn.execute('update runs set last_opened_attempt_number = last_opened_attempt_number + %s where run_id = %s',
                 (shift, args.run_id))

    for idx, a in enumerate(attempts, start=1):
        note = a['note'] or ''
        note = (note + f" [sheet run {a['sheet_run']}]").strip()
        conn.execute(
            'insert into attempts (run_id, attempt_number, starter, outcome, death_note, started_at) '
            "values (%s, %s, %s, 'dead', %s, null)",
            (args.run_id, idx, a['starter_branch'] or 'Fire', note))
        attempt_id = conn.execute('select attempt_id from attempts where run_id = %s and attempt_number = %s',
                                  (args.run_id, idx)).fetchone()['attempt_id']
        bonus_secondaries = {}
        for e in a['encounters']:
            loc = e['loc']
            bonus = 0
            if 'bonus_of' in loc:
                key = (loc['bonus_of'], loc['name'])
                if key not in bonus_secondaries:
                    base = conn.execute(
                        'select coalesce(max(el.secondary_sort_order), 0) as s from event_locations el '
                        'where el.canonical_location_id = %s and el.version_group_id = %s',
                        (loc['bonus_of'], VERSION_GROUP_ID)).fetchone()['s']
                    existing = conn.execute(
                        'select coalesce(max(secondary_sort_order), 0) as s from bonus_locations '
                        'where run_id = %s and attempt_id = %s and canonical_location_id = %s',
                        (args.run_id, attempt_id, loc['bonus_of'])).fetchone()['s']
                    secondary = max(int(base), int(existing)) + 1
                    conn.execute(
                        'insert into bonus_locations (run_id, attempt_id, canonical_location_id, secondary_sort_order, canonical_name) '
                        'values (%s, %s, %s, %s, %s)',
                        (args.run_id, attempt_id, loc['bonus_of'], secondary, loc['name']))
                    bonus_secondaries[key] = secondary
                bonus = bonus_secondaries[key]
            conn.execute(
                'insert into pokebank (run_id, attempt_id, species_id, canonical_location_id, nickname, status, bonus_location) '
                'values (%s, %s, %s, %s, %s, %s, %s)',
                (args.run_id, attempt_id, e['species_id'], loc['canon'], e['nickname'], e['status'], bonus))
    conn.commit()

    added = skipped = 0
    for m in matched:
        for x in m['moves']:
            try:
                backend.add_observed_move(conn, m['trainer_id'], x['slot'], x['move'])
                added += 1
            except ValueError as exc:
                print(f"  move skipped: {m['label']} slot {x['slot']} {x['move']}: {exc}")
                skipped += 1
    print(f'\nAPPLIED: {len(attempts)} attempts (existing shifted +{shift}), '
          f'{added} observed moves ({skipped} skipped).')
    conn.close()


if __name__ == '__main__':
    main()
