import { describe, expect, it } from 'vitest'
import { buildSplitFeed, isSplitLayout, lockedTrainerCount, splitColor, splitInitial, splitPhrase, tableAvailability } from './splitFeed'

const splits = [
  { split_key: 'badge:33', ordinal: 0, kind: 'gym', label: 'Cress', type_focus: 'Water', final_trainer_id: 500, reveal_after: null },
  { split_key: 'badge:34', ordinal: 1, kind: 'gym', label: 'Lenora', type_focus: 'Normal', final_trainer_id: 501, reveal_after: null },
  { split_key: 'league', ordinal: 2, kind: 'league', label: 'Pokémon League', final_trainer_id: 513, reveal_after: null },
  { split_key: 'postgame', ordinal: 3, kind: 'postgame', label: 'Postgame', final_trainer_id: 520, reveal_after: 'league' },
]

const loc = (id, name, home, extra = {}) => ({
  event_id: id, display_name: name, event_type: 'Location', boss_event_id: null, encounter_key: `${id}:0`,
  home_split: home, revisits: [], trainer_splits: {}, ...extra,
})
const boss = (id, name, home, defeated = false) => ({
  event_id: id, display_name: name, event_type: null, boss_event_id: id * 10, home_split: home, is_defeated: defeated,
})

const script = [
  loc(3, 'Route 1', 'badge:33', { revisits: [{ split_key: 'badge:34', tables: [{ area: null, method: 'grass-spots', rare: [] }, { area: null, method: 'fish', rare: [] }], areas: [], trainers: [] }] }),
  loc(234, 'Dreamyard', 'badge:33', {
    trainer_splits: { 'badge:34': 2 },
    revisits: [{ split_key: 'badge:34', tables: [{ area: null, method: 'grass-spots', rare: [{ species_id: 385, name: 'JIRACHI', rate: 1 }] }], areas: [], trainers: [
      { trainer_id: 2, trainer_name: 'PLASMA GRUNT', trainer_class: 'TRAINER_CLASS_PLASMA_GRUNT', max_level: 15, is_defeated: true },
      { trainer_id: 3, trainer_name: 'PLASMA GRUNT', trainer_class: 'TRAINER_CLASS_PLASMA_GRUNT', max_level: 15, is_defeated: false },
    ] }],
  }),
  boss(500, 'Striaton City Gym', 'badge:33', true),
  loc(8, 'Route 3', 'badge:34'),
  boss(501, 'Nacrene City Gym', 'badge:34'),
  loc(9, 'Route 4', 'badge:34'),
  boss(513, "N's Castle", 'league'),
  loc(301, 'Route 11', 'postgame'),
  boss(520, 'Champion', 'postgame'),
]

describe('buildSplitFeed', () => {
  it('groups rows by home split, pins the leader last and derives progress', () => {
    const feed = buildSplitFeed(script, splits, {})
    expect(feed.sections.map(s => [s.key, s.state, s.hidden])).toEqual([
      ['badge:33', 'done', false], ['badge:34', 'current', false], ['league', 'future', false], ['postgame', 'future', true],
    ])
    expect(feed.current.key).toBe('badge:34')
    expect(feed.currentOrdinal).toBe(1)
    const lenora = feed.sections[1]
    // Route 4 sorts after the gym in story order but the leader stays last.
    expect(lenora.rows.map(r => r.display_name)).toEqual(['Route 3', 'Route 4', 'Nacrene City Gym'])
    expect(lenora.leaderRow.event_id).toBe(501)
  })

  it('lists returning encounters (open first) and trainers per area', () => {
    const feed = buildSplitFeed(script, splits, { '3:0': { status: 'Captured', nickname: 'Coo', species_name: 'PIDOVE' } })
    const lenora = feed.sections[1]
    expect(lenora.newEncounters.map(e => [e.name, e.encounterUsed])).toEqual([['Dreamyard', false], ['Route 1', true]])
    expect(lenora.newEncounters[1].encounterName).toBe('Coo')
    expect(lenora.newEncounters[1].methods.map(m => m.method)).toEqual(['grass-spots', 'fish'])
    expect(lenora.newEncounters[0].methods[0].rare[0].name).toBe('JIRACHI')
    expect(lenora.newTrainers).toHaveLength(1)
    expect(lenora.newTrainers[0]).toMatchObject({ name: 'Dreamyard', trainerIds: [2, 3], beaten: 1 })
    expect(lenora.newTrainers[0].homeSplit.split_key).toBe('badge:33')
    expect(feed.sections[0].newEncounters).toEqual([])
  })

  it('reveals the postgame once the league is beaten and moves on past the last split', () => {
    const beaten = script.map(row => (row.boss_event_id != null ? { ...row, is_defeated: true } : row))
    const feed = buildSplitFeed(beaten, splits, {})
    expect(feed.sections.map(s => [s.state, s.hidden])).toEqual([['done', false], ['done', false], ['done', false], ['done', false]])
    expect(feed.current).toBeNull()
    expect(feed.currentOrdinal).toBe(Number.POSITIVE_INFINITY)
    const midway = script.map(row => (row.event_id === 513 || row.event_id === 500 || row.event_id === 501 ? { ...row, is_defeated: true } : row))
    expect(buildSplitFeed(midway, splits, {}).sections[3]).toMatchObject({ state: 'current', hidden: false })
  })

  it('handles rows with no split and an empty catalogue', () => {
    const feed = buildSplitFeed([loc(3, 'Route 1', null)], splits, {})
    expect(feed.sections[0].rows).toHaveLength(1)
    expect(buildSplitFeed(script, [], {})).toMatchObject({ sections: [], current: null, currentOrdinal: 0 })
  })
})

describe('availability helpers', () => {
  const { index } = buildSplitFeed(script, splits, {})

  it('classifies a table row against the current split', () => {
    expect(tableAvailability({ opens_in: 'badge:33' }, index, 1).state).toBe('open')
    expect(tableAvailability({ opens_in: 'badge:34' }, index, 1).state).toBe('open')
    expect(tableAvailability({ opens_in: 'league', opens_gate: 'surf' }, index, 1)).toMatchObject({ state: 'future', gate: 'surf' })
    expect(tableAvailability({ opens_in: null, opens_unknown: true, opens_gate: 'surf' }, index, 1)).toMatchObject({ state: 'unknown', gate: 'surf' })
    expect(tableAvailability({}, index, 1).state).toBe('open')
    expect(tableAvailability({ opens_in: 'badge:99' }, index, 1).state).toBe('open')
  })

  it('counts locked trainers and formats split names', () => {
    expect(lockedTrainerCount({ trainer_splits: { 'badge:34': 2, league: 3 } }, index, 1)).toBe(3)
    expect(lockedTrainerCount({ trainer_splits: { 'badge:34': 2, league: 3 } }, index, 0)).toBe(5)
    expect(lockedTrainerCount({}, index, 0)).toBe(0)
    expect(splitPhrase(index.get('badge:34'))).toBe("Lenora's split")
    expect(splitPhrase(index.get('league'))).toBe('the League')
    expect(splitInitial(index.get('badge:34'))).toBe('L')
    expect(splitInitial(index.get('league'))).toBe('E4')
    expect(splitColor(index.get('badge:33'))).toBe('#399CFF')
    expect(splitColor(index.get('postgame'))).toBe('#e6c15c')
    expect(isSplitLayout({ splits })).toBe(true)
    expect(isSplitLayout({ splits: [] })).toBe(false)
    expect(isSplitLayout({})).toBe(false)
  })
})
