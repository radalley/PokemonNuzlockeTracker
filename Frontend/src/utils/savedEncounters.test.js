import { describe, expect, it } from 'vitest'
import { applyStatusChange } from './savedEncounters'

describe('applyStatusChange', () => {
  it('records an optimistic status and merges into a stored entry', () => {
    const next = applyStatusChange({}, '240:0', 551, 'Captured')
    expect(next).toEqual({ '240:0': { species_id: 551, status: 'Captured' } })

    const stored = { '240:0': { pokemon_id: 7, species_id: 551, nickname: 'Croc', status: 'Captured' } }
    expect(applyStatusChange(stored, '240:0', 551, 'Dead')['240:0']).toEqual({ pokemon_id: 7, species_id: 551, nickname: 'Croc', status: 'Dead' })
  })

  it('removes an entry rolled back before the server ever stored it', () => {
    const optimistic = applyStatusChange({ '7:0': { pokemon_id: 3, species_id: 16, status: 'Captured' } }, '240:0', 551, 'Captured')
    const rolledBack = applyStatusChange(optimistic, '240:0', 551, '')
    expect(rolledBack).toEqual({ '7:0': { pokemon_id: 3, species_id: 16, status: 'Captured' } })
    // nothing to roll back: the same object comes back
    expect(applyStatusChange(rolledBack, '999:0', 1, '')).toBe(rolledBack)
  })

  it('keeps a stored entry whose status is cleared', () => {
    const stored = { '240:0': { pokemon_id: 7, species_id: 551, status: 'Missed' } }
    expect(applyStatusChange(stored, '240:0', 551, '')).toEqual({ '240:0': { pokemon_id: 7, species_id: 551, status: '' } })
  })
})
