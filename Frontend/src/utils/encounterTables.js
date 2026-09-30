// Grouping a location's flat encounter rows (from pool_tables) into the
// tables the encounter panel renders. Pure functions; the component and
// LocationRow own the selection state.

export const SEASONS = ['spring', 'summer', 'autumn', 'winter']

// One hue per method group, kept clear of the status colours (caught
// green, missed amber, dead red).
export const GROUP_HUES = {
  grass: '#7fb069',
  cave: '#b08968',
  ground: '#c9a227',
  indoor: '#b085f5',
  bridge: '#9aa4b5',
  water: '#4d8fe8',
  fishing: '#7ec8e3',
  special: '#e6c15c',
  other: '#9aa4b5',
}
const SEASON_LABELS = { spring: 'Spring', summer: 'Summer', autumn: 'Autumn', winter: 'Winter' }

/** The seasons a condition covers; no condition means every season. */
export function conditionSeasons(condition) {
  if (!condition || !String(condition).startsWith('season:')) return SEASONS.slice()
  return String(condition).slice('season:'.length).split(',').filter(Boolean)
}

export function conditionLabel(condition) {
  if (!condition) return 'All seasons'
  const seasons = conditionSeasons(condition)
  if (seasons.length >= SEASONS.length) return 'All seasons'
  return seasons.map(s => SEASON_LABELS[s] || s).join(' / ')
}

export function seasonLabel(season) {
  return SEASON_LABELS[season] || season
}

// Black/White seasons follow the calendar month: January is Spring,
// February Summer, March Autumn, April Winter, and round again.
export function bwSeasonForDate(date = new Date()) {
  return SEASONS[date.getMonth() % 4]
}

// The season switch: the DS clock follows the calendar, so today's
// Black/White season is the default, and a manual pick is remembered per run.
const seasonStorageKey = (runId) => `lockley:season:${runId}`

export function rememberedSeason(runId, date = new Date()) {
  try {
    const stored = localStorage.getItem(seasonStorageKey(runId))
    if (SEASONS.includes(stored)) return stored
  } catch { /* storage blocked */ }
  return bwSeasonForDate(date)
}

export function rememberSeason(runId, season) {
  if (!SEASONS.includes(season)) return
  try { localStorage.setItem(seasonStorageKey(runId), season) } catch { /* storage blocked */ }
}

/**
 * A stable identity for one selectable entry (a table slot, an overlay, a
 * static, a plain-pool or search pick), so the highlighted row survives
 * re-renders, tab switches and a return from Undo.
 */
export function slotKey(row) {
  if (!row || row.species_id == null) return null
  return [
    row.source || 'table', row.slot_kind || 'slot', row.method || '', row.area || '', row.condition || '',
    row.species_id, row.rate ?? '', row.min_level ?? '',
  ].join('|')
}

const FALLBACK_META = { label: null, group: 'other', is_rare: false, sort_order: 999, description: '' }

export function methodMeta(methods, key) {
  const found = (methods || []).find(m => m.key === key)
  if (found) return found
  return { ...FALLBACK_META, key, label: key ? String(key).replace(/-/g, ' ') : 'Encounters' }
}

const KIND_ORDER = { slot: 0, overlay: 1, static: 2 }

function areaKey(area) {
  return area || ''
}

/**
 * rows: flat pool_tables rows for one location (already ordered by the
 * server). Returns:
 *   areas   — [{ key, label, sort }] in doc order; key '' is the whole location
 *   hasSeasons — true when any table is season-specific
 *   tables  — [{ key, area, condition, method, meta, rows, overlays }]
 *   rare    — every overlay and static row, in row order (for the strip)
 */
export function buildEncounterView(rows, methods) {
  const list = Array.isArray(rows) ? rows : []
  const areas = []
  const areaSeen = new Map()
  const tables = []
  const tableIndex = new Map()
  const rare = []

  const registerArea = (row) => {
    const key = areaKey(row.area)
    if (!areaSeen.has(key)) {
      areaSeen.set(key, true)
      areas.push({ key, label: row.area || null, sort: Number(row.area_sort) || 0 })
    }
  }

  const tableKey = (area, condition, method) => `${areaKey(area)}|${condition || ''}|${method}`
  const ensureTable = (area, condition, method) => {
    const key = tableKey(area, condition, method)
    if (!tableIndex.has(key)) {
      const table = { key, area: area || null, condition: condition || null, method, meta: methodMeta(methods, method), rows: [], overlays: [] }
      tableIndex.set(key, table)
      tables.push(table)
    }
    return tableIndex.get(key)
  }

  for (const row of list) {
    if (!row || row.slot_kind === 'static') continue
    registerArea(row)
    if (row.slot_kind === 'slot') ensureTable(row.area, row.condition, row.method).rows.push(row)
  }
  for (const row of list) {
    if (!row) continue
    if (row.slot_kind === 'overlay') {
      // An overlay joins the table of its method and area whose seasons
      // cover its own (an all-seasons table covers everything); a room no
      // table lists gets an overlay-only card.
      const wanted = conditionSeasons(row.condition)
      const candidates = tables.filter(t => areaKey(t.area) === areaKey(row.area) && t.method === row.method)
      const covering = candidates.find(t => wanted.every(s => conditionSeasons(t.condition).includes(s)))
      const target = covering || candidates.find(t => !t.condition) || ensureTable(row.area, row.condition, row.method)
      target.overlays.push(row)
      rare.push(row)
    } else if (row.slot_kind === 'static') {
      registerArea(row)
      rare.push(row)
    }
  }

  areas.sort((a, b) => a.sort - b.sort)
  tables.sort((a, b) => {
    const areaA = areaSeen.get(areaKey(a.area)) ? areas.findIndex(x => x.key === areaKey(a.area)) : 0
    const areaB = areaSeen.get(areaKey(b.area)) ? areas.findIndex(x => x.key === areaKey(b.area)) : 0
    if (areaA !== areaB) return areaA - areaB
    const condA = a.condition ? 1 : 0
    const condB = b.condition ? 1 : 0
    if (condA !== condB) return condA - condB
    return (a.meta.sort_order ?? 999) - (b.meta.sort_order ?? 999)
  })
  for (const table of tables) {
    table.overlays.sort((a, b) => (KIND_ORDER[a.slot_kind] - KIND_ORDER[b.slot_kind]) || ((Number(b.rate) || 0) - (Number(a.rate) || 0)))
  }
  const hasSeasons = tables.some(t => t.condition) || rare.some(r => r.condition)
  return { areas, hasSeasons, tables, rare }
}

/** The tables to show for one area and season; all-seasons tables always show. */
export function visibleTables(view, area, season) {
  const key = areaKey(area)
  return view.tables.filter(t => areaKey(t.area) === key && (!t.condition || conditionSeasons(t.condition).includes(season)))
}

/** The overlays of a table that apply in the chosen season. */
export function visibleOverlays(table, season) {
  return table.overlays.filter(o => !o.condition || conditionSeasons(o.condition).includes(season))
}
