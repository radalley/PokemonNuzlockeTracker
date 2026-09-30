import { describe, expect, it } from 'vitest'
import { moveBy, moveRelative, reorderWithinGroup, sameOrder } from './trainerOrder'

describe('moveRelative', () => {
  it('drops the moved id before or after the target', () => {
    expect(moveRelative([1, 2, 3, 4], 4, 2, 'before')).toEqual([1, 4, 2, 3])
    expect(moveRelative([1, 2, 3, 4], 1, 3, 'after')).toEqual([2, 3, 1, 4])
  })

  it('is a no-op when the target is the moved id or is not in the list', () => {
    expect(moveRelative([1, 2, 3], 2, 2, 'before')).toEqual([1, 2, 3])
    expect(moveRelative([1, 2, 3], 2, 9, 'before')).toEqual([1, 2, 3])
    expect(moveRelative([1, 2, 3], 9, 1, 'before')).toEqual([1, 2, 3])
  })

  it('never mutates its input', () => {
    const ids = [1, 2, 3]
    moveRelative(ids, 3, 1, 'before')
    expect(ids).toEqual([1, 2, 3])
  })
})

describe('moveBy', () => {
  it('shifts by the delta and clamps at the ends', () => {
    expect(moveBy([1, 2, 3], 3, -1)).toEqual([1, 3, 2])
    expect(moveBy([1, 2, 3], 1, 1)).toEqual([2, 1, 3])
    expect(moveBy([1, 2, 3], 1, -1)).toEqual([1, 2, 3])
    expect(moveBy([1, 2, 3], 3, 5)).toEqual([1, 2, 3])
    expect(moveBy([1, 2, 3], 9, 1)).toEqual([1, 2, 3])
  })
})

describe('reorderWithinGroup', () => {
  const row = (trainer_id, area_id = null) => ({ trainer_id, area_id })
  const list = [row(1), row(2, 7), row(3), row(4, 7), row(5)]
  const street = t => t.area_id == null
  const gym = t => t.area_id === 7

  it('rearranges only the group, keeping its slots and every other row in place', () => {
    const out = reorderWithinGroup(list, street, [5, 1, 3])
    expect(out.map(t => t.trainer_id)).toEqual([5, 2, 1, 4, 3])
    expect(reorderWithinGroup(list, gym, [4, 2]).map(t => t.trainer_id)).toEqual([1, 4, 3, 2, 5])
  })

  it('trails members the order left out, in their old relative order', () => {
    expect(reorderWithinGroup(list, street, [5]).map(t => t.trainer_id)).toEqual([5, 2, 1, 4, 3])
  })

  it('ignores ids that are not group members', () => {
    expect(reorderWithinGroup(list, street, [2, 3, 1, 5]).map(t => t.trainer_id)).toEqual([3, 2, 1, 4, 5])
  })
})

describe('sameOrder', () => {
  it('compares element by element', () => {
    expect(sameOrder([1, 2], [1, 2])).toBe(true)
    expect(sameOrder([1, 2], [2, 1])).toBe(false)
    expect(sameOrder([1], [1, 2])).toBe(false)
  })
})
