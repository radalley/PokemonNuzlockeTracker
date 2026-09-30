/**
 * Attempt's optimistic bookkeeping for a status chosen on a location, keyed
 * by encounter_key. A status merges into the entry; rolling a status back to
 * '' for an entry the server never stored (no pokemon_id) removes it, so no
 * phantom entry is left for the dupe graying or the encounter panel to read.
 */
export function applyStatusChange(saved, encounterKey, speciesId, status) {
  const current = saved[encounterKey]
  if (!status && !current?.pokemon_id) {
    if (!current) return saved
    const next = { ...saved }
    delete next[encounterKey]
    return next
  }
  return { ...saved, [encounterKey]: { ...(current || {}), species_id: speciesId, status } }
}
