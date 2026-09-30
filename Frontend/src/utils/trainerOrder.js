// Reordering trainers within one group (area) of a location's trainer
// panel. Pure list arithmetic; LocationRow owns the state and the save.

/** ids with movedId placed directly before or after targetId. */
export function moveRelative(ids, movedId, targetId, position) {
  if (movedId === targetId) return ids.slice()
  const without = ids.filter(id => id !== movedId)
  const at = without.indexOf(targetId)
  if (at < 0 || without.length === ids.length) return ids.slice()
  const insertAt = position === 'after' ? at + 1 : at
  return [...without.slice(0, insertAt), movedId, ...without.slice(insertAt)]
}

/** ids with movedId shifted by delta positions, clamped to the ends. */
export function moveBy(ids, movedId, delta) {
  const from = ids.indexOf(movedId)
  if (from < 0) return ids.slice()
  const to = Math.max(0, Math.min(ids.length - 1, from + delta))
  if (to === from) return ids.slice()
  const without = ids.filter(id => id !== movedId)
  return [...without.slice(0, to), movedId, ...without.slice(to)]
}

/**
 * The trainer list with one group's members rearranged into orderedIds.
 * Rows outside the group keep their places, and so do the slots the
 * group occupies; members missing from orderedIds trail in their old
 * relative order.
 */
export function reorderWithinGroup(list, isMember, orderedIds) {
  const members = list.filter(isMember)
  const byId = new Map(members.map(t => [t.trainer_id, t]))
  const queue = orderedIds.map(id => byId.get(id)).filter(Boolean)
  const ranked = new Set(queue.map(t => t.trainer_id))
  for (const member of members) {
    if (!ranked.has(member.trainer_id)) queue.push(member)
  }
  let next = 0
  return list.map(row => (isMember(row) ? queue[next++] : row))
}

export function sameOrder(a, b) {
  return a.length === b.length && a.every((id, i) => id === b[i])
}
