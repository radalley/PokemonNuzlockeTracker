// Lockley's own damage calculator.
//
// The math comes from @smogon/calc, the MIT-licensed engine behind the
// Pokemon Showdown damage calculator; the data comes from our own
// database, which already carries every hack's modified base stats,
// types, abilities, movesets, and the run's recorded party facts. Base
// stats and types are always passed as overrides so hack changes apply;
// move power/type/category likewise come from our rows, so a hack-buffed
// move computes with its buffed numbers even though the engine's dex is
// vanilla.
//
// The engine bundles dex data for every generation, so it loads lazily —
// only when a battle modal actually needs numbers.

import { exportSpeciesName } from './damageCalc'

// Rollout gate: Blaze Black / Volt White first. Adding a game here is the
// entire enablement step (the data path is identical for every game).
const CALC_GAMES = new Set([1001, 1002])

export function damagePanelEnabled(gameId) {
  return CALC_GAMES.has(Number(gameId))
}

let enginePromise = null
export function loadCalcEngine() {
  if (!enginePromise) {
    // Drop the cache on failure so a later mount retries instead of
    // re-receiving the same rejected promise for the whole session.
    enginePromise = import('@smogon/calc').catch(err => {
      enginePromise = null
      throw err
    })
  }
  return enginePromise
}

const titleCase = (s) => String(s || '').toLowerCase().replace(/(^|[\s-])\w/g, c => c.toUpperCase())

function formatAbilityName(raw) {
  if (!raw) return undefined
  return titleCase(String(raw).replace(/^ABILITY_/i, '').replace(/_/g, ' '))
}

// Showdown-style id: lowercase, alphanumerics only. Collapses every
// spelling variant ('TwistedSpoon', 'ITEM_TWISTED_SPOON', 'Twisted Spoon')
// onto the engine dex's own key space.
const toDexId = (name) => String(name || '').toLowerCase().replace(/[^a-z0-9]+/g, '')

const itemNameCache = new Map()
function canonicalItemName(gen, raw) {
  const token = String(raw || '').trim()
    .replace(/^[\s{[("']+/, '')
    .replace(/[\s})\]*("']+$/, '')
    .replace(/^ITEM_/i, '')
  if (!token || /^(none|null|no_item|no item)$/i.test(token)) return undefined
  // The engine's item boosts match exact display names ('Twisted Spoon',
  // 'Never-Melt Ice'), so resolve through its own dex by id.
  let byId = itemNameCache.get(gen.num)
  if (!byId) {
    byId = new Map()
    for (const item of gen.items) byId.set(toDexId(item.name), item.name)
    itemNameCache.set(gen.num, byId)
  }
  return byId.get(toDexId(token))
}

const STAT_KEYS = ['hp', 'atk', 'def', 'spa', 'spd', 'spe']

function baseStatsFromRow(row) {
  const stats = {}
  for (const key of STAT_KEYS) {
    const value = Number(row[key])
    if (!Number.isFinite(value) || value <= 0) return null
    stats[key] = value
  }
  return stats
}

function typesFromRow(row) {
  const t1 = row.type1 ? titleCase(String(row.type1).replace(/_/g, ' ')) : null
  const t2 = row.type2 ? titleCase(String(row.type2).replace(/_/g, ' ')) : null
  if (!t1) return null
  // The engine merges override arrays index-wise into the dex species, so a
  // one-element override would keep the dex's second type alive. Pad the
  // mono case with the neutral '???' type (1x from everything, never STAB)
  // to genuinely overwrite both slots. Never pad by duplicating t1: gen 5
  // multiplies per-type effectiveness, which would square it.
  return t2 && t2 !== t1 ? [t1, t2] : [t1, '???']
}

function fullIvs(recorded) {
  const ivs = { hp: 31, atk: 31, def: 31, spa: 31, spd: 31, spe: 31 }
  for (const key of STAT_KEYS) {
    const value = Number(recorded?.[key])
    if (recorded?.[key] !== null && recorded?.[key] !== undefined && Number.isFinite(value)) {
      ivs[key] = value
    }
  }
  return ivs
}

/**
 * Our party row -> engine Pokemon. Returns null when the species can't be
 * built (unknown to the dex and no stats to override with).
 */
export function toCalcPokemon(engine, gen, row, { level, isPlayer }) {
  const name = exportSpeciesName(row.species_name)
  const overrides = {}
  const baseStats = baseStatsFromRow(row)
  if (baseStats) overrides.baseStats = baseStats
  const types = typesFromRow(row)
  if (types) overrides.types = types

  const options = {
    level: Math.max(1, Math.min(100, Number(level) || 50)),
    overrides,
    ivs: fullIvs(isPlayer ? row.ivs : null),
  }
  if (isPlayer) {
    if (row.nature) options.nature = titleCase(row.nature)
    const ability = formatAbilityName(row.chosen_ability)
    if (ability) options.ability = ability
    // Rivalry (1.25x same gender / 0.75x opposite) reads gender; the engine
    // defaults everything to male, so pass the recorded one.
    const gender = row.gender === 'female' ? 'F' : row.gender === 'male' ? 'M' : undefined
    if (gender) options.gender = gender
  } else {
    const ability = formatAbilityName(row.ability1)
    if (ability) options.ability = ability
    const item = canonicalItemName(gen, row.held_item)
    if (item) options.item = item
  }

  try {
    return new engine.Pokemon(gen, name, options)
  } catch {
    try {
      delete options.item
      return new engine.Pokemon(gen, name, options)
    } catch {
      return null
    }
  }
}

// The engine's dex uses modernized move names; period-correct gen-5
// spellings from our data resolve through these renames.
const MOVE_RENAMES = {
  hijumpkick: 'High Jump Kick',
  faintattack: 'Feint Attack',
  vicegrip: 'Vise Grip',
  smellingsalt: 'Smelling Salts',
}

/**
 * Our move row ({move_name, type, damage_class, power}) -> engine Move.
 * Status moves return {status: true}. Names the engine's dex doesn't know
 * (custom hack moves) fall back to a Tackle stand-in fully driven by our
 * numbers — an unknown name constructs without flags and crashes
 * calculate(), so the decision is dex membership, not construction.
 */
export function toCalcMove(engine, gen, moveRow, attackerAbility) {
  const rawName = titleCase(String(moveRow.move_name || '').replace(/_/g, ' '))
  const dexEntry = gen.moves.get(toDexId(MOVE_RENAMES[toDexId(rawName)] || rawName))
  const name = dexEntry ? dexEntry.name : rawName

  // Nature Power is 'status' in our data but the gen-5 engine computes it
  // as Earthquake; hand it over bare so its own mechanic applies.
  if (dexEntry && dexEntry.name === 'Nature Power') {
    try {
      return { name, move: new engine.Move(gen, name, { ability: attackerAbility }) }
    } catch {
      return { name, status: true }
    }
  }

  const damageClass = String(moveRow.damage_class || '').toLowerCase()
  if (damageClass === 'status') return { name, status: true }

  const overrides = {}
  if (damageClass === 'physical') overrides.category = 'Physical'
  if (damageClass === 'special') overrides.category = 'Special'
  if (moveRow.type) overrides.type = titleCase(String(moveRow.type).replace(/_/g, ' '))
  const power = Number(moveRow.power)
  if (Number.isFinite(power) && power > 0) overrides.basePower = power

  // ability rides along because the engine resolves Skill Link's 5-hit
  // count at Move construction, not from the attacker Pokemon.
  const options = { ability: attackerAbility, overrides }
  let move = null
  try {
    move = new engine.Move(gen, dexEntry ? name : 'Tackle', options)
  } catch {
    move = null
  }
  if (!move) return { name, status: true }
  return { name, move }
}

/**
 * Damage for every damaging move in moveRows, attacker -> defender.
 * Returns [{name, status?, seen?, learnLevel?, minPct, maxPct, koText}].
 */
export function calcMatchup(engine, gen, attacker, defender, moveRows) {
  const results = []
  for (const moveRow of moveRows || []) {
    const built = toCalcMove(engine, gen, moveRow, attacker?.ability)
    const entry = {
      name: built.name,
      seen: Boolean(moveRow.seen),
      learnLevel: moveRow.learn_level ?? null,
    }
    if (built.status || !attacker || !defender) {
      results.push({ ...entry, status: true })
      continue
    }
    try {
      const result = engine.calculate(gen, attacker, defender, built.move)
      const [min, max] = result.range()
      const maxHP = defender.maxHP()
      entry.minPct = maxHP > 0 ? Math.round((min / maxHP) * 1000) / 10 : 0
      entry.maxPct = maxHP > 0 ? Math.round((max / maxHP) * 1000) / 10 : 0
      try {
        entry.koText = result.kochance().text
      } catch {
        entry.koText = ''
      }
      results.push(entry)
    } catch {
      results.push({ ...entry, status: true })
    }
  }
  return results
}

/**
 * The four moves a trainer mon is displayed with: confirmed sightings
 * claim their slots first, estimates fill what remains (the same rule
 * as the trainer card).
 */
export function opponentMoveRows(opponentMon) {
  const observed = (opponentMon?.observed_moves || []).map(m => ({ ...m, seen: true }))
  const observedNames = new Set(observed.map(m => String(m.move_name || '').toLowerCase()))
  const inferred = (opponentMon?.resolved_moves || [])
    .filter(m => typeof m === 'object' && m && !observedNames.has(String(m.move_name || '').toLowerCase()))
    .slice(0, Math.max(0, 4 - observed.length))
  return [...observed, ...inferred]
}
