import { apiFetch } from './api'

const abilityKey = name => String(name || '').toLowerCase().replace(/^ability_/, '').replace(/[^a-z0-9]/g, '')

/**
 * The ability an evolved Pokemon ends up with: whatever sits in the same
 * slot on the new species (slot 1, slot 2, hidden). Lists are the
 * abilities endpoint's [{name, slot}] shape, deduplicated, so a missing
 * slot 2 means the species repeats its slot-1 ability. An ability that
 * is not in the old species' slots (typed by hand) or a slot the new
 * species lacks keeps the current value.
 */
export function evolvedAbility(current, fromAbilities, toAbilities) {
  if (!current) return current || ''
  const key = abilityKey(current)
  const from = (fromAbilities || []).find(a => abilityKey(a.name) === key)
  if (!from?.slot) return current
  const to = toAbilities || []
  const target = to.find(a => a.slot === from.slot)
    || (from.slot === 2 ? to.find(a => a.slot === 1) : null)
  return target?.name || current
}

async function fetchAbilities(speciesId, gameId) {
  const query = gameId ? `?game_id=${gameId}` : ''
  const res = await apiFetch(`/api/species/${speciesId}/abilities${query}`)
  if (!res.ok) return []
  const data = await res.json()
  return Array.isArray(data) ? data : []
}

/**
 * evolvedAbility with the two species' ability lists fetched. A failed
 * lookup keeps the current ability rather than blocking the evolution.
 */
export async function resolveEvolvedAbility(current, fromSpeciesId, toSpeciesId, gameId) {
  if (!current || !fromSpeciesId || !toSpeciesId) return current || ''
  try {
    const [from, to] = await Promise.all([
      fetchAbilities(fromSpeciesId, gameId),
      fetchAbilities(toSpeciesId, gameId),
    ])
    return evolvedAbility(current, from, to)
  } catch (err) {
    console.error('Failed to resolve evolved ability:', err)
    return current
  }
}
