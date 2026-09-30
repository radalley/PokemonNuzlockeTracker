import { describe, expect, it } from 'vitest'
import {
  buildEncounterView, bwSeasonForDate, conditionLabel, conditionSeasons, methodMeta, visibleOverlays, visibleTables,
} from './encounterTables'

const METHODS = [
  { key: 'grass', label: 'Tall grass', group: 'grass', is_rare: false, sort_order: 10 },
  { key: 'dark-grass', label: 'Dark grass', group: 'grass', is_rare: false, sort_order: 20 },
  { key: 'grass-spots', label: 'Shaking grass', group: 'grass', is_rare: true, sort_order: 30 },
  { key: 'cave', label: 'Cave floor', group: 'cave', is_rare: false, sort_order: 50 },
  { key: 'surf-spots', label: 'Rippling water', group: 'water', is_rare: true, sort_order: 130 },
  { key: 'static', label: 'Static encounter', group: 'special', is_rare: false, sort_order: 160 },
]

const row = (over) => ({
  species_id: 1, name: 'X', method: 'grass', area: null, area_sort: 0, condition: null,
  slot_kind: 'slot', tag: null, rate: 20, min_level: null, max_level: null, note: null, ...over,
})

describe('conditions', () => {
  it('reads seasons out of a condition and labels them', () => {
    expect(conditionSeasons(null)).toEqual(['spring', 'summer', 'autumn', 'winter'])
    expect(conditionSeasons('season:winter')).toEqual(['winter'])
    expect(conditionSeasons('season:spring,summer,autumn')).toEqual(['spring', 'summer', 'autumn'])
    expect(conditionLabel(null)).toBe('All seasons')
    expect(conditionLabel('season:winter')).toBe('Winter')
    expect(conditionLabel('season:spring,summer,autumn')).toBe('Spring / Summer / Autumn')
  })

  it('maps the calendar month onto the Black/White season cycle', () => {
    expect(bwSeasonForDate(new Date(2026, 0, 10))).toBe('spring')   // January
    expect(bwSeasonForDate(new Date(2026, 3, 10))).toBe('winter')   // April
    expect(bwSeasonForDate(new Date(2026, 8, 16))).toBe('spring')   // September
    expect(bwSeasonForDate(new Date(2026, 11, 1))).toBe('winter')   // December
  })
})

describe('methodMeta', () => {
  it('falls back to a readable label for an unknown key', () => {
    expect(methodMeta(METHODS, 'grass').label).toBe('Tall grass')
    expect(methodMeta(METHODS, 'rocky-grass')).toMatchObject({ key: 'rocky-grass', label: 'rocky grass', group: 'other' })
  })
})

describe('buildEncounterView', () => {
  const rows = [
    row({ species_id: 1, name: 'Sandile', method: 'grass', area: '1F', area_sort: 1, rate: 60 }),
    row({ species_id: 2, name: 'Sandshrew', method: 'grass', area: '1F', area_sort: 1, rate: 40 }),
    row({ species_id: 3, name: 'Krokorok', method: 'grass', area: 'B2F, B3F', area_sort: 2, rate: 100 }),
    row({ species_id: 4, name: 'Regirock', method: 'grass', area: 'B2F, B3F', area_sort: 2, rate: 1, slot_kind: 'overlay', tag: 'legendary', min_level: 50, max_level: 50, note: 'deep' }),
    // the server orders a room's overlay (cave) before its static
    row({ species_id: 6, name: 'Regigigas', method: 'cave', area: 'Volcarona Room', area_sort: 3, rate: 1, slot_kind: 'overlay', tag: 'legendary', min_level: 70, max_level: 70 }),
    row({ species_id: 5, name: 'Volcarona', method: 'static', area: 'Volcarona Room', area_sort: 3, rate: null, slot_kind: 'static', tag: 'special', min_level: 75, max_level: 75 }),
  ]

  it('groups slots into tables per area and method, in doc order', () => {
    const view = buildEncounterView(rows, METHODS)
    expect(view.areas.map(a => [a.key, a.sort])).toEqual([['1F', 1], ['B2F, B3F', 2], ['Volcarona Room', 3]])
    expect(view.tables.map(t => [t.area, t.method, t.rows.length, t.overlays.length])).toEqual([
      ['1F', 'grass', 2, 0],
      ['B2F, B3F', 'grass', 1, 1],
      ['Volcarona Room', 'cave', 0, 1],   // a room no table lists: overlay-only card
    ])
    expect(view.tables[1].overlays[0].name).toBe('Regirock')
    expect(view.rare.map(r => r.name)).toEqual(['Regirock', 'Regigigas', 'Volcarona'])
    expect(view.hasSeasons).toBe(false)
  })

  it('orders tables by the registry and puts all-seasons tables before conditioned ones', () => {
    const view = buildEncounterView([
      row({ species_id: 1, method: 'surf-spots', rate: 100 }),
      row({ species_id: 2, method: 'grass', rate: 100, condition: 'season:winter' }),
      row({ species_id: 3, method: 'grass', rate: 100, condition: 'season:spring,summer,autumn' }),
      row({ species_id: 4, method: 'dark-grass', rate: 100 }),
    ], METHODS)
    expect(view.tables.map(t => [t.method, t.condition])).toEqual([
      ['dark-grass', null], ['surf-spots', null],
      ['grass', 'season:winter'], ['grass', 'season:spring,summer,autumn'],
    ])
    expect(view.hasSeasons).toBe(true)
  })

  it('attaches a seasonal overlay to the table whose seasons cover it and keeps its own season', () => {
    const view = buildEncounterView([
      row({ species_id: 1, method: 'dark-grass', area: 'Outside', area_sort: 1, condition: 'season:spring,summer,autumn', rate: 100 }),
      row({ species_id: 2, method: 'dark-grass', area: 'Outside', area_sort: 1, condition: 'season:winter', rate: 100 }),
      row({ species_id: 3, name: 'Articuno', method: 'dark-grass', area: 'Outside', area_sort: 1, condition: 'season:winter', rate: 1, slot_kind: 'overlay', tag: 'legendary' }),
      row({ species_id: 4, method: 'surf-spots', rate: 100 }),
      row({ species_id: 5, name: 'Kyogre', method: 'surf-spots', condition: 'season:summer', rate: 1, slot_kind: 'overlay', tag: 'legendary' }),
    ], METHODS)
    const winter = view.tables.find(t => t.method === 'dark-grass' && t.condition === 'season:winter')
    const warm = view.tables.find(t => t.method === 'dark-grass' && t.condition !== 'season:winter')
    expect(winter.overlays.map(o => o.name)).toEqual(['Articuno'])
    expect(warm.overlays).toEqual([])
    const surf = view.tables.find(t => t.method === 'surf-spots')
    expect(surf.overlays.map(o => o.name)).toEqual(['Kyogre'])
    // visible in summer, hidden in winter, while the table itself always shows
    expect(visibleOverlays(surf, 'summer').map(o => o.name)).toEqual(['Kyogre'])
    expect(visibleOverlays(surf, 'winter')).toEqual([])
    expect(visibleTables(view, 'Outside', 'winter').map(t => t.condition)).toEqual(['season:winter'])
    expect(visibleTables(view, '', 'winter').map(t => t.method)).toEqual(['surf-spots'])
  })

  it('handles an empty or missing list', () => {
    expect(buildEncounterView(undefined, METHODS)).toEqual({ areas: [], hasSeasons: false, tables: [], rare: [] })
  })
})
