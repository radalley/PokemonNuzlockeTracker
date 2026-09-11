// Bridge to the Smogon damage calculator that Lockley serves at /calc/
// (a verbatim mirror of calc.pokemonshowdown.com — see
// public/calc/LOCKLEY-README.md).
//
// The calculator merges localStorage.customsets into its set index on
// every page load. Because the mirror is same-origin, the battle modal
// can write both teams there and open it: every mon of yours and the
// trainer's is then one species pick away, preloaded with level, nature,
// ability, item, IVs, and moves. No paste, no import step.

// game_id -> calc settings. Only listed games get a live Calc button;
// adding a game here is the entire enablement step.
export const DAMAGE_CALCS = {
  1001: { gen: 5 }, // Blaze Black
  1002: { gen: 5 }, // Volt White
}

export function getDamageCalc(gameId) {
  return DAMAGE_CALCS[Number(gameId)] || null
}

// Species spellings where the calculator's dex differs from our species
// table (which stores uppercase names; the calc is case-sensitive).
const EXPORT_NAME_FIXES = {
  'NIDORAN M': 'Nidoran-M',
  'NIDORAN F': 'Nidoran-F',
  'MR-MIME': 'Mr. Mime',
  'MIME-JR': 'Mime Jr.',
  'FARFETCHD': "Farfetch'd",
  'HO-OH': 'Ho-Oh',
  'PORYGON-Z': 'Porygon-Z',
}

export function exportSpeciesName(name) {
  const trimmed = String(name || '').trim()
  const key = trimmed.toUpperCase()
  if (EXPORT_NAME_FIXES[key]) return EXPORT_NAME_FIXES[key]
  return trimmed === key
    ? trimmed.toLowerCase().replace(/(^|[\s-])\w/g, c => c.toUpperCase())
    : trimmed
}

const titleCase = (s) => String(s || '').toLowerCase().replace(/(^|[\s-])\w/g, c => c.toUpperCase())

function formatAbilityName(raw) {
  if (!raw) return undefined
  return titleCase(String(raw).replace(/^ABILITY_/i, '').replace(/_/g, ' '))
}

// Item display names the generic cleanup can't reach: the data carries
// compressed pre-gen-6 spellings, the calc's dex uses spaced ones.
const ITEM_NAME_FIXES = {
  twistedspoon: 'Twisted Spoon',
  nevermeltice: 'Never-Melt Ice',
  blackglasses: 'Black Glasses',
  brightpowder: 'Bright Powder',
  silverpowder: 'Silver Powder',
  deepseatooth: 'Deep Sea Tooth',
  deepseascale: 'Deep Sea Scale',
}

function formatItemName(raw) {
  const token = String(raw || '').trim()
    .replace(/^[\s{[("']+/, '')
    .replace(/[\s})\]*("']+$/, '')
    .replace(/^ITEM_/i, '')
  if (!token || /^(none|null|no_item|no item)$/i.test(token)) return undefined
  const fixed = ITEM_NAME_FIXES[token.toLowerCase().replace(/[^a-z0-9]/g, '')]
  if (fixed) return fixed
  // 'ITEM_ORAN_BERRY' -> 'Oran Berry'; 'FlameOrb' -> 'Flame Orb'
  return titleCase(token.replace(/([a-z])([A-Z])/g, '$1 $2').replace(/_/g, ' '))
}

const IV_KEYS = ['hp', 'atk', 'def', 'spa', 'spd', 'spe']

function recordedIvs(ivs) {
  const out = {}
  for (const key of IV_KEYS) {
    const value = Number(ivs?.[key])
    if (ivs?.[key] !== null && ivs?.[key] !== undefined && Number.isFinite(value)) out[key] = value
  }
  return out
}

/**
 * The four moves a trainer mon is displayed with: confirmed sightings
 * claim their slots first, estimates fill the rest (the trainer card's
 * rule).
 */
export function opponentMoveNames(mon) {
  const observed = (mon?.observed_moves || []).map(m => m.move_name).filter(Boolean)
  const seen = new Set(observed.map(n => n.toLowerCase()))
  const inferred = (mon?.resolved_moves || [])
    .map(m => (typeof m === 'object' && m ? m.move_name : m))
    .filter(n => n && !seen.has(String(n).toLowerCase()))
    .slice(0, Math.max(0, 4 - observed.length))
  return [...observed, ...inferred].map(n => titleCase(String(n).replace(/_/g, ' ')))
}

/**
 * Both teams as the calculator's customsets shape:
 * { Species: { 'Set name': { level, nature, ability, item, ivs, moves } } }
 * Player sets are tagged "(yours)"; trainer sets carry the trainer's name
 * and each mon's real level.
 */
export function buildCustomSets(playerParty, opponentParty, trainerName, playerLevel) {
  const sets = {}
  const put = (speciesName, setName, set) => {
    const species = exportSpeciesName(speciesName)
    if (!species) return
    sets[species] = sets[species] || {}
    sets[species][setName] = { ...set, isCustomSet: true }
  }

  for (const mon of playerParty || []) {
    if (!mon?.species_name) continue
    const set = {
      level: Number(playerLevel) > 0 ? Math.min(100, Number(playerLevel)) : 50,
      ivs: recordedIvs(mon.ivs),
      moves: [],
    }
    if (mon.nature) set.nature = titleCase(mon.nature)
    const ability = formatAbilityName(mon.chosen_ability)
    if (ability) set.ability = ability
    if (mon.gender === 'female') set.gender = 'F'
    if (mon.gender === 'male') set.gender = 'M'
    const label = (mon.nickname || '').trim()
    put(mon.species_name, `${label || exportSpeciesName(mon.species_name)} (yours)`, set)
  }

  for (const mon of opponentParty || []) {
    if (!mon?.species_name) continue
    const set = {
      level: Number(mon.lvl) > 0 ? Number(mon.lvl) : 50,
      ivs: {},
      moves: opponentMoveNames(mon),
    }
    const ability = formatAbilityName(mon.ability1)
    if (ability) set.ability = ability
    const item = formatItemName(mon.held_item)
    if (item) set.item = item
    put(mon.species_name, `${trainerName || 'Trainer'} Lv${set.level}`, set)
  }
  return sets
}

/**
 * Write both teams into the calculator's storage and open it.
 * Lockley-written sets from earlier battles are replaced wholesale;
 * sets the user imported inside the calc themselves are preserved.
 */
export function openCalcWithTeams(playerParty, opponentParty, trainerName, playerLevel, gen) {
  const fresh = buildCustomSets(playerParty, opponentParty, trainerName, playerLevel)
  let existing = {}
  try {
    existing = JSON.parse(localStorage.getItem('customsets') || '{}') || {}
  } catch {
    existing = {}
  }
  // Drop our previous seeding (recognizable set names), keep the user's own.
  const isOurs = (setName) => / \(yours\)$/.test(setName) || / Lv\d+$/.test(setName)
  const merged = {}
  for (const [species, bySet] of Object.entries(existing)) {
    for (const [setName, set] of Object.entries(bySet || {})) {
      if (isOurs(setName)) continue
      merged[species] = merged[species] || {}
      merged[species][setName] = set
    }
  }
  for (const [species, bySet] of Object.entries(fresh)) {
    merged[species] = merged[species] || {}
    Object.assign(merged[species], bySet)
  }
  try {
    localStorage.setItem('customsets', JSON.stringify(merged))
  } catch {
    return false
  }
  window.open(`/calc/index.html?gen=${Number(gen) || 5}`, '_blank', 'noopener')
  return true
}
