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
  'FARFETCHD': 'Farfetch’d', // the calc dex keys the curly apostrophe
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

// The calculator's dex uses modernized move names; period-correct gen-5
// spellings from our data resolve through these renames.
const MOVE_RENAMES = {
  'hijumpkick': 'High Jump Kick',
  'faintattack': 'Feint Attack',
  'vicegrip': 'Vise Grip',
  'smellingsalt': 'Smelling Salts',
}

export function calcMoveName(raw) {
  const name = titleCase(String(raw || '').replace(/_/g, ' '))
  return MOVE_RENAMES[name.toLowerCase().replace(/[^a-z0-9]/g, '')] || name
}

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
  return [...observed, ...inferred].map(calcMoveName)
}

/**
 * The hack's dex modifications, formatted for the calculator's data
 * structures ({Species: {bs, types, ability}}, {Move: {bp, type,
 * category}}). Vanilla games produce an empty patch.
 */
export function formatDexPatch(serverPatch) {
  const patch = { generation: Number(serverPatch?.generation) || 5, species: {}, moves: {} }
  for (const [rawName, entry] of Object.entries(serverPatch?.species || {})) {
    const name = exportSpeciesName(rawName)
    if (!name || !entry) continue
    const out = {}
    if (entry.stats) {
      out.bs = {
        hp: entry.stats.hp, at: entry.stats.atk, df: entry.stats.def,
        sa: entry.stats.spa, sd: entry.stats.spd, sp: entry.stats.spe,
      }
    }
    if (Array.isArray(entry.types) && entry.types.length > 0) {
      out.types = entry.types.map(t => titleCase(t))
    }
    if (entry.ability) out.ability = titleCase(entry.ability)
    if (Object.keys(out).length > 0) patch.species[name] = out
  }
  for (const [rawName, entry] of Object.entries(serverPatch?.moves || {})) {
    const name = calcMoveName(rawName)
    if (!name || !entry) continue
    const damageClass = String(entry.damage_class || '').toLowerCase()
    patch.moves[name] = {
      bp: Number(entry.power) > 0 ? Number(entry.power) : 0,
      type: entry.type ? titleCase(entry.type) : undefined,
      category: damageClass === 'physical' ? 'Physical' : damageClass === 'special' ? 'Special' : 'Status',
    }
  }
  return patch
}

// Warm the cache when the battle modal opens, so the click handler's
// await resolves instantly and window.open stays inside the browser's
// user-activation window.
export function prefetchDexPatch(gameId) {
  if (gameId == null) return
  fetchDexPatch(gameId).catch(() => {})
}

const dexPatchCache = new Map()
async function fetchDexPatch(gameId) {
  if (dexPatchCache.has(gameId)) return dexPatchCache.get(gameId)
  const res = await fetch(`/api/games/${gameId}/calc-dex-patch`)
  if (!res.ok) throw new Error(`dex patch failed (${res.status})`)
  const patch = formatDexPatch(await res.json())
  dexPatchCache.set(gameId, patch)
  return patch
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
 * Write both teams (and the game's dex modifications) into the
 * calculator's storage and open it. Lockley-written sets from earlier
 * battles are replaced wholesale; sets the user imported inside the calc
 * themselves are preserved. The dex patch is best-effort: if it cannot
 * be fetched the calc still opens with its stock data.
 */
export async function openCalcWithTeams(playerParty, opponentParty, trainerName, playerLevel, gen, gameId) {
  let patched = false
  try {
    const patch = await fetchDexPatch(gameId)
    if (Object.keys(patch.species).length > 0 || Object.keys(patch.moves).length > 0) {
      localStorage.setItem('lockleyDexPatch', JSON.stringify(patch))
      patched = true
    } else {
      localStorage.removeItem('lockleyDexPatch')
    }
  } catch {
    localStorage.removeItem('lockleyDexPatch')
  }
  const opened = seedTeamsAndOpen(playerParty, opponentParty, trainerName, playerLevel, gen)
  return opened && { patched }
}

function seedTeamsAndOpen(playerParty, opponentParty, trainerName, playerLevel, gen) {
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
