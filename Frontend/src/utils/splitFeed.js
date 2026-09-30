// The split layout's pure model: the page payload's `splits` and the
// script rows (each carrying `home_split` and `revisits`) become sections,
// each with its rows in story order, the leader pinned last, and the
// "New encounters / New trainers" jump lists gathered from earlier areas.
// Progress is derived from boss defeats on the script; nothing is stored.
import TYPE_COLORS from '../components/typeColors'

export const LEAGUE_COLOR = '#c084fc'
export const POSTGAME_COLOR = '#e6c15c'
const NEUTRAL_COLOR = '#9aa4b5'

/** Whether a payload asked for the split layout (Blaze Black today). */
export function isSplitLayout(data) {
  return Array.isArray(data?.splits) && data.splits.length > 0
}

export function splitColor(split) {
  if (!split) return NEUTRAL_COLOR
  if (split.kind === 'league') return LEAGUE_COLOR
  if (split.kind === 'postgame') return POSTGAME_COLOR
  const type = String(split.type_focus || '')
  const key = type.charAt(0).toUpperCase() + type.slice(1).toLowerCase()
  return TYPE_COLORS[key]?.[0] || NEUTRAL_COLOR
}

/** A medallion's letters: the leader's initial, E4 for the League, PG after. */
export function splitInitial(split) {
  if (!split) return '?'
  if (split.kind === 'league') return 'E4'
  if (split.kind === 'postgame') return 'PG'
  return String(split.label || '?').charAt(0).toUpperCase()
}

/** split_key -> the split with its ordinal and colour. */
export function splitIndexFrom(splits) {
  const index = new Map()
  for (const split of splits || []) {
    index.set(split.split_key, { ...split, color: splitColor(split) })
  }
  return index
}

/** "Lenora's split", "the League", "the Postgame". */
export function splitPhrase(split) {
  if (!split) return 'a later split'
  if (split.kind === 'league') return 'the League'
  if (split.kind === 'postgame') return 'the Postgame'
  return `${split.label}'s split`
}

export function formatTrainerClass(value) {
  return String(value || '').replace(/^TRAINER_CLASS_/i, '').replace(/_/g, ' ').toLowerCase().replace(/\b\w/g, c => c.toUpperCase())
}

/**
 * A table row's availability against the run's progress:
 *   open     — reachable now (or nothing known about it)
 *   future   — opens in a later split (`split`)
 *   unknown  — behind a gate whose split is not set (`gate`)
 */
export function tableAvailability(row, index, currentOrdinal) {
  if (!row) return { state: 'open', split: null, gate: null }
  if (row.opens_unknown) return { state: 'unknown', split: null, gate: row.opens_gate || null }
  const split = row.opens_in ? index.get(row.opens_in) : null
  if (!split) return { state: 'open', split: null, gate: row.opens_gate || null }
  return { state: split.ordinal > currentOrdinal ? 'future' : 'open', split, gate: row.opens_gate || null }
}

/** How many of a location's regular trainers are not reachable yet. */
export function lockedTrainerCount(row, index, currentOrdinal) {
  let locked = 0
  for (const [key, count] of Object.entries(row?.trainer_splits || {})) {
    const split = index.get(key)
    if (split && split.ordinal > currentOrdinal) locked += Number(count) || 0
  }
  return locked
}

function isBoss(row) {
  return row?.boss_event_id != null && !row.is_bonus_location
}

// One entry per method across a revisit's tables, rare slots merged.
function methodsOf(tables) {
  const seen = new Map()
  for (const table of tables || []) {
    const entry = seen.get(table.method) || { method: table.method, areas: [], rare: [] }
    if (table.area && !entry.areas.includes(table.area)) entry.areas.push(table.area)
    for (const rare of table.rare || []) {
      if (!entry.rare.some(r => r.species_id === rare.species_id)) entry.rare.push(rare)
    }
    seen.set(table.method, entry)
  }
  return [...seen.values()]
}

/**
 * script: the page's script rows; splits: the payload's sections;
 * savedEncounters: encounter_key -> stored encounter (for used/open).
 */
export function buildSplitFeed(script, splits, savedEncounters = {}) {
  const index = splitIndexFrom(splits)
  const defeatedBosses = new Set(
    (script || []).filter(row => isBoss(row) && row.is_defeated).map(row => Number(row.event_id))
  )
  const sections = (splits || []).map(split => ({
    key: split.split_key,
    ordinal: split.ordinal,
    split,
    color: splitColor(split),
    rows: [],
    leaderRow: null,
    newEncounters: [],
    newTrainers: [],
    done: split.final_trainer_id != null && defeatedBosses.has(Number(split.final_trainer_id)),
    hidden: false,
    state: 'future',
  }))
  if (sections.length === 0) return { sections, current: null, currentOrdinal: 0, index }
  const byKey = new Map(sections.map(section => [section.key, section]))

  for (const row of script || []) {
    const section = byKey.get(row.home_split) || sections[0]
    section.rows.push(row)
  }
  for (const section of sections) {
    const gate = section.split.reveal_after ? byKey.get(section.split.reveal_after) : null
    section.hidden = Boolean(gate) && !gate.done
  }
  const current = sections.find(section => !section.hidden && !section.done) || null
  const currentOrdinal = current ? current.ordinal : Number.POSITIVE_INFINITY
  for (const section of sections) {
    section.state = section.done ? 'done' : section === current ? 'current' : 'future'
    const finalId = section.split.final_trainer_id
    if (finalId != null) {
      const at = section.rows.findIndex(row => isBoss(row) && Number(row.event_id) === Number(finalId))
      if (at >= 0) {
        const [leader] = section.rows.splice(at, 1)
        section.rows.push(leader)
        section.leaderRow = leader
      }
    }
  }

  for (const row of script || []) {
    if (isBoss(row) || row.is_bonus_location || !Array.isArray(row.revisits)) continue
    const saved = savedEncounters[row.encounter_key]
    const encounterUsed = Boolean(saved?.status)
    for (const revisit of row.revisits) {
      const target = byKey.get(revisit.split_key)
      if (!target) continue
      if (revisit.tables?.length || revisit.areas?.length) {
        target.newEncounters.push({
          row,
          encounterKey: row.encounter_key,
          name: row.display_name,
          homeSplit: index.get(row.home_split) || null,
          encounterUsed,
          encounterName: saved?.nickname || saved?.species_name || null,
          areas: revisit.areas || [],
          methods: methodsOf(revisit.tables),
        })
      }
      if (revisit.trainers?.length) {
        target.newTrainers.push({
          row,
          encounterKey: row.encounter_key,
          name: row.display_name,
          homeSplit: index.get(row.home_split) || null,
          trainers: revisit.trainers,
          trainerIds: revisit.trainers.map(t => Number(t.trainer_id)),
          beaten: revisit.trainers.filter(t => t.is_defeated).length,
        })
      }
    }
  }
  for (const section of sections) {
    // Areas whose encounter is still open first: they are the ones to act on.
    section.newEncounters.sort((a, b) => Number(a.encounterUsed) - Number(b.encounterUsed))
  }
  return { sections, current, currentOrdinal, index }
}
