// First species of each generation's starter trio (national dex). Each
// trio is nine consecutive ids: grass line, fire line, water line.
const TRIO_STARTS = [1, 152, 252, 387, 495, 650, 722, 810, 906]
const BRANCHES = ['Grass', 'Fire', 'Water']

// Every game's script carries canonical location 1, "Starter".
const STARTER_LOCATION_ID = 1

/**
 * The session-stats branch (Fire / Grass / Water) a starter species
 * belongs to, or null for anything outside the classic trios (Yellow's
 * Pikachu, Let's Go partners, a hack's oddity).
 */
export function starterBranchForSpecies(speciesId) {
  const id = Number(speciesId)
  if (!Number.isInteger(id)) return null
  for (const start of TRIO_STARTS) {
    const offset = id - start
    if (offset >= 0 && offset < 9) return BRANCHES[Math.floor(offset / 3)]
  }
  return null
}

/**
 * The species caught at the Starter location, or null when nothing is
 * logged there yet (a Missed starter does not count).
 */
export function starterCaptureSpecies(savedEncounters) {
  for (const [key, entry] of Object.entries(savedEncounters || {})) {
    if (Number(String(key).split(':')[0]) !== STARTER_LOCATION_ID) continue
    if (entry?.status === 'Captured' || entry?.status === 'Dead') return Number(entry.species_id) || null
  }
  return null
}
