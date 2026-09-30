/**
 * Turns a decomp-style constant (ABILITY_SHEER_FORCE, MOVE_QUICK_ATTACK,
 * sheer-force) into a display label (Sheer Force).
 */
export function formatConstant(value) {
  if (!value) return null
  return String(value)
    .replace(/^(ABILITY|MOVE)_/i, '')
    .replace(/[_-]/g, ' ')
    .toLowerCase()
    .replace(/\b\w/g, c => c.toUpperCase())
}

/**
 * pokebank.badges_earned arrives as a JSON array string from the API, a
 * real array from guest storage, or (historically) a comma list.
 */
export function parseBadgeIds(value) {
  if (!value) return []
  if (Array.isArray(value)) return value.map(v => Number(v)).filter(Number.isFinite)
  if (typeof value === 'number') return Number.isFinite(value) ? [value] : []
  if (typeof value !== 'string') return []
  const trimmed = value.trim()
  if (!trimmed) return []
  try {
    const parsed = JSON.parse(trimmed)
    if (Array.isArray(parsed)) return parsed.map(v => Number(v)).filter(Number.isFinite)
  } catch {
    // Fall back to comma-separated values.
  }
  return trimmed.split(',').map(part => Number(part.trim())).filter(Number.isFinite)
}

export const IV_STAT_KEYS = ['hp', 'atk', 'def', 'spa', 'spd', 'spe']
// The full physical IV range, matching the pokebank check constraint.
export const IV_MIN = 0
export const IV_MAX = 31

export function emptyIvs() {
  return Object.fromEntries(IV_STAT_KEYS.map(key => [key, null]))
}

/**
 * Coerce an IV object (stat-keyed, from the panel, guest storage, or the
 * API) into {hp, atk, def, spa, spd, spe} with ints in range or null.
 */
export function normalizeIvs(value) {
  const ivs = emptyIvs()
  if (!value || typeof value !== 'object') return ivs
  for (const key of IV_STAT_KEYS) {
    const raw = value[key] ?? value[`iv_${key}`]
    if (raw === null || raw === undefined || raw === '') continue
    const number = Number(raw)
    if (Number.isInteger(number) && number >= IV_MIN && number <= IV_MAX) ivs[key] = number
  }
  return ivs
}

export function hasAnyIv(value) {
  return IV_STAT_KEYS.some(key => value?.[key] != null)
}
