// Bridge to the hzla Dynamic-Calc damage calculators.
//
// The calc's Import box takes Showdown-export text: pasting it registers each
// mon as a custom "My Box" set (species, nickname, gender, level, nature,
// ability, IVs) that persists in the calc's own storage. We build that text
// from the attempt's party, copy it to the clipboard, and open the game's
// calculator; the user pastes once into the Import box.

// game_id -> the calculator that carries this game's data. Only games listed
// here get a live Damage Calc button; everything else shows it greyed out.
// The #import-1_wrapper fragment lands the page scrolled to the Import box
// (it otherwise sits ~2000px below the fold and looks like there is no
// import at all).
export const DAMAGE_CALCS = {
  1001: { // Blaze Black
    label: 'Blaze Black/Volt White Calculator',
    url: 'https://hzla.github.io/Dynamic-Calc-Decomps/?data=9aa37533b7c000992d92&gen=5&types=5&view=calculator#import-1_wrapper',
  },
  1002: { // Volt White
    label: 'Blaze Black/Volt White Calculator',
    url: 'https://hzla.github.io/Dynamic-Calc-Decomps/?data=9aa37533b7c000992d92&gen=5&types=5&view=calculator#import-1_wrapper',
  },
}

export function getDamageCalc(gameId) {
  return DAMAGE_CALCS[Number(gameId)] || null
}

// Species spellings where the calc differs from our species table.
const EXPORT_NAME_FIXES = {
  'NIDORAN M': 'Nidoran-M',
  'NIDORAN F': 'Nidoran-F',
  'MR-MIME': 'Mr. Mime',
  'MIME-JR': 'Mime Jr.',
  'FARFETCHD': "Farfetch'd",
  'HO-OH': 'Ho-Oh',
  'PORYGON-Z': 'Porygon-Z',
}

function exportSpeciesName(name) {
  const trimmed = String(name || '').trim()
  const key = trimmed.toUpperCase()
  if (EXPORT_NAME_FIXES[key]) return EXPORT_NAME_FIXES[key]
  // Our species table stores names uppercase, but the calc's import parser
  // is case-sensitive ('SNIVY' silently fails, 'Snivy' imports).
  return trimmed === key
    ? trimmed.toLowerCase().replace(/(^|[\s-])\w/g, c => c.toUpperCase())
    : trimmed
}

function formatAbilityName(ability) {
  if (!ability) return null
  return String(ability)
    .replace(/^ABILITY_/i, '')
    .replace(/_/g, ' ')
    .toLowerCase()
    .replace(/\b\w/g, c => c.toUpperCase())
}

const IV_LABELS = [
  ['hp', 'HP'],
  ['atk', 'Atk'],
  ['def', 'Def'],
  ['spa', 'SpA'],
  ['spd', 'SpD'],
  ['spe', 'Spe'],
]

/**
 * Showdown-export text for one party. `level` applies to every mon (Lockley
 * does not track current levels; the battle's level cap is the Nuzlocke
 * default). Unrecorded IV slots are omitted so the calc keeps its 31 default.
 */
export function buildCalcExport(party, level) {
  const blocks = []
  for (const mon of party || []) {
    if (!mon || !mon.species_name) continue
    const species = exportSpeciesName(mon.species_name)
    const nickname = (mon.nickname || '').trim()
    const gender = mon.gender === 'female' ? 'F' : mon.gender === 'male' ? 'M' : ''
    let header = nickname && nickname.toLowerCase() !== species.toLowerCase()
      ? `${nickname} (${species})`
      : species
    if (gender) header += ` (${gender})`

    const lines = [header]
    const numericLevel = Number(level)
    if (Number.isFinite(numericLevel) && numericLevel > 0) lines.push(`Level: ${Math.min(100, numericLevel)}`)
    if (mon.nature) lines.push(`${String(mon.nature).charAt(0).toUpperCase()}${String(mon.nature).slice(1).toLowerCase()} Nature`)
    const ability = formatAbilityName(mon.chosen_ability)
    if (ability) lines.push(`Ability: ${ability}`)
    const ivs = mon.ivs || {}
    const ivParts = IV_LABELS
      .filter(([key]) => Number.isFinite(Number(ivs[key])) && ivs[key] !== null && ivs[key] !== '')
      .map(([key, label]) => `${Number(ivs[key])} ${label}`)
    if (ivParts.length > 0) lines.push(`IVs: ${ivParts.join(' / ')}`)

    blocks.push(lines.join('\n'))
  }
  return blocks.join('\n\n')
}
