import { describe, expect, it } from 'vitest'
import { battleMoveSlots, hasEstimatedMoves } from './trainerMoves'

const mv = (name, extra = {}) => ({ move_name: name, type: 'Normal', damage_class: 'physical', power: 40, accuracy: 100, ...extra })

describe('battleMoveSlots', () => {
  it('puts seen moves first and lets estimates fill only the remaining slots', () => {
    const slots = battleMoveSlots({
      observed_moves: [mv('Crunch'), mv('Dig')],
      resolved_moves: [mv('Crunch'), mv('Bite'), mv('Sand Tomb'), mv('Torment'), mv('Swagger')],
    })
    expect(slots.map(m => [m.move_name, m.seen])).toEqual([
      ['Crunch', true], ['Dig', true], ['Bite', false], ['Sand Tomb', false],
    ])
  })

  it('never repeats a seen move as an estimate, regardless of case', () => {
    const slots = battleMoveSlots({
      observed_moves: [{ move_name: 'tackle' }],
      resolved_moves: [mv('Tackle'), mv('Growl')],
    })
    expect(slots.map(m => m.move_name)).toEqual(['tackle', 'Growl'])
  })

  it('never lists the same estimate twice', () => {
    const slots = battleMoveSlots({ resolved_moves: [mv('Growl'), mv('growl'), mv('Tackle')] })
    expect(slots.map(m => m.move_name)).toEqual(['Growl', 'Tackle'])
  })

  it('drops duplicate observations and blank entries', () => {
    const slots = battleMoveSlots({
      observed_moves: [mv('Bite'), { move_name: 'BITE' }, null, { move_name: '' }],
      resolved_moves: [null, '', mv('Growl')],
    })
    expect(slots.map(m => m.move_name)).toEqual(['Bite', 'Growl'])
  })

  it('shows only seen moves once four have been observed', () => {
    const slots = battleMoveSlots({
      observed_moves: [mv('A'), mv('B'), mv('C'), mv('D'), mv('E')],
      resolved_moves: [mv('F')],
    })
    expect(slots.map(m => m.move_name)).toEqual(['A', 'B', 'C', 'D', 'E'])
    expect(slots.every(m => m.seen)).toBe(true)
  })

  it('accepts plain move-name strings in the resolved list', () => {
    const slots = battleMoveSlots({ resolved_moves: ['Leaf Tornado', 'Wrap'] })
    expect(slots).toEqual([
      { move_name: 'Leaf Tornado', seen: false },
      { move_name: 'Wrap', seen: false },
    ])
  })

  it('falls back to the raw moves column when nothing was resolved', () => {
    const slots = battleMoveSlots({ moves: 'MOVE_LEAF_TORNADO, MOVE_WRAP' })
    expect(slots.map(m => m.move_name)).toEqual(['Leaf Tornado', 'Wrap'])
  })

  it('treats an empty resolved list as no estimates, not as a fallback', () => {
    expect(battleMoveSlots({ resolved_moves: [], moves: 'MOVE_TACKLE' })).toEqual([])
  })

  it('handles a missing Pokémon', () => {
    expect(battleMoveSlots(null)).toEqual([])
    expect(battleMoveSlots(undefined)).toEqual([])
  })
})

describe('hasEstimatedMoves', () => {
  it('is true only when an estimate is actually on display', () => {
    expect(hasEstimatedMoves({ moves_estimated: true, observed_moves: [], resolved_moves: [mv('Growl')] })).toBe(true)
    expect(hasEstimatedMoves({ moves_estimated: false, observed_moves: [], resolved_moves: [mv('Growl')] })).toBe(false)
    // Four sightings leave no room for estimates.
    expect(hasEstimatedMoves({
      moves_estimated: true,
      observed_moves: [mv('A'), mv('B'), mv('C'), mv('D')],
      resolved_moves: [mv('E')],
    })).toBe(false)
    expect(hasEstimatedMoves({ moves_estimated: true, resolved_moves: [] })).toBe(false)
  })
})
