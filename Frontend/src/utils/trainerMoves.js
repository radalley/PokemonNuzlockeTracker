// Which four moves a trainer's Pokémon shows, everywhere Lockley lists
// them: the trainer card, the battle modal, and the damage calc export.
//
// A Pokémon holds four moves. Moves seen in play (admin-observed) claim
// their slots first; estimates from the learnset only fill what remains,
// and no move name appears twice.

function titleCaseMove(raw) {
  return String(raw)
    .trim()
    .replace(/^MOVE_/, '')
    .replace(/_/g, ' ')
    .toLowerCase()
    .replace(/\b\w/g, c => c.toUpperCase())
}

function asMove(entry) {
  if (!entry) return null
  if (typeof entry === 'string') {
    const move_name = entry.trim()
    return move_name ? { move_name } : null
  }
  if (typeof entry === 'object' && entry.move_name) return entry
  return null
}

// The raw trainer_pokemon.moves column, for rows the server has not
// resolved into move details.
function movesFromCsv(csv) {
  if (!csv || typeof csv !== 'string') return []
  return csv.split(',').map(titleCaseMove).filter(Boolean)
}

/**
 * The move slots to display for a trainer's Pokémon, in order, each
 * tagged with `seen` (true for observed moves, false for estimates).
 */
export function battleMoveSlots(mon, cap = 4) {
  const seen = new Set()
  const observed = []
  for (const entry of mon?.observed_moves || []) {
    const move = asMove(entry)
    if (!move) continue
    const key = move.move_name.toLowerCase()
    if (seen.has(key)) continue
    seen.add(key)
    observed.push({ ...move, seen: true })
  }
  const source = Array.isArray(mon?.resolved_moves) ? mon.resolved_moves : movesFromCsv(mon?.moves)
  const inferred = []
  const room = Math.max(0, cap - observed.length)
  for (const entry of source) {
    if (inferred.length >= room) break
    const move = asMove(entry)
    if (!move) continue
    const key = move.move_name.toLowerCase()
    if (seen.has(key)) continue
    seen.add(key)
    inferred.push({ ...move, seen: false })
  }
  return [...observed, ...inferred]
}

/** True when the shown slots include learnset estimates. */
export function hasEstimatedMoves(mon, slots = battleMoveSlots(mon)) {
  return Boolean(mon?.moves_estimated) && slots.some(m => !m.seen)
}
