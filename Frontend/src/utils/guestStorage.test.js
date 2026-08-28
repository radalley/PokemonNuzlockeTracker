import { afterEach, beforeEach, describe, expect, it } from 'vitest'
import {
  addBonusLocation,
  addToParty,
  clearLocalData,
  createRun,
  deleteBonusLocation,
  deleteEncounter,
  deleteRun,
  getBonusLocations,
  getEncounters,
  getParty,
  getRuns,
  getSessionStats,
  hasLocalData,
  markTrainerVictory,
  removeFromParty,
  renameBonusLocation,
  upsertEncounter,
  _getState,
} from './guestStorage.js'

beforeEach(() => {
  localStorage.clear()
})

afterEach(() => {
  localStorage.clear()
})

describe('hasLocalData / clearLocalData', () => {
  it('reports no data on a clean slate', () => {
    expect(hasLocalData()).toBe(false)
  })

  it('reports data once a run exists', () => {
    createRun({ game_id: 1, game_name: 'Test Game' }, 'My Run')
    expect(hasLocalData()).toBe(true)
  })

  it('clearLocalData wipes everything', () => {
    createRun({ game_id: 1, game_name: 'Test Game' }, 'My Run')
    clearLocalData()
    expect(hasLocalData()).toBe(false)
  })
})

describe('_getState resilience', () => {
  it('falls back to default state when localStorage holds corrupted JSON', () => {
    localStorage.setItem('lockley_guest', '{not valid json')
    const state = _getState()
    expect(state.runs).toEqual([])
    expect(state.counters).toEqual({ run: 1, pokemon: 1, bonus: 1 })
  })

  it('falls back to default state when localStorage is empty', () => {
    const state = _getState()
    expect(state.runs).toEqual([])
  })
})

describe('createRun / deleteRun', () => {
  it('creates a run with a first attempt', () => {
    const result = createRun({ game_id: 3, game_name: 'Emerald' }, 'Solo Run')
    expect(result.success).toBe(true)
    expect(result.attempt_number).toBe(1)

    const runs = getRuns()
    expect(runs).toHaveLength(1)
    expect(runs[0].run_name).toBe('Solo Run')
    expect(runs[0].total_attempts).toBe(1)
  })

  it('deleteRun removes the run and all of its keyed state', () => {
    const { run_id } = createRun({ game_id: 3, game_name: 'Emerald' }, 'Solo Run')
    upsertEncounter(run_id, 1, 10, 0, 25, 'Pikachu', 'Sparky', 'Jolly', 'Captured', false)

    deleteRun(run_id)

    expect(getRuns()).toHaveLength(0)
    expect(getEncounters(run_id, 1)).toEqual({})
  })
})

describe('upsertEncounter / deleteEncounter', () => {
  it('records a new encounter and assigns it a pokemon id', () => {
    const { run_id } = createRun({ game_id: 1 }, 'Run')
    const pokemonId = upsertEncounter(run_id, 1, 10, 0, 25, 'Pikachu', null, null, 'Captured', false)

    const encounters = getEncounters(run_id, 1)
    const encounter = Object.values(encounters)[0]
    expect(encounter.pokemon_id).toBe(pokemonId)
    expect(encounter.species_name).toBe('Pikachu')
    expect(encounter.status).toBe('Captured')
  })

  it('re-encountering the same location+bonus slot updates in place, not duplicates', () => {
    const { run_id } = createRun({ game_id: 1 }, 'Run')
    upsertEncounter(run_id, 1, 10, 0, 25, 'Pikachu', null, null, 'Captured', false)
    upsertEncounter(run_id, 1, 10, 0, 26, 'Raichu', null, null, 'Captured', false)

    const encounters = getEncounters(run_id, 1)
    expect(Object.keys(encounters)).toHaveLength(1)
    expect(Object.values(encounters)[0].species_id).toBe(26)
  })

  it('deleteEncounter removes it from both encounters and party', () => {
    const { run_id } = createRun({ game_id: 1 }, 'Run')
    const pokemonId = upsertEncounter(run_id, 1, 10, 0, 25, 'Pikachu', null, null, 'Captured', false)
    addToParty(run_id, 1, pokemonId)

    deleteEncounter(run_id, 1, pokemonId)

    expect(getEncounters(run_id, 1)).toEqual({})
    expect(getParty(run_id, 1)).toEqual([])
  })
})

describe('party management (6-slot cap)', () => {
  function seedEncounter(runId, attemptNumber, speciesId) {
    return upsertEncounter(runId, attemptNumber, speciesId, 0, speciesId, `Species${speciesId}`, null, null, 'Captured', false)
  }

  it('assigns sequential slots starting at 1', () => {
    const { run_id } = createRun({ game_id: 1 }, 'Run')
    const pokemonId = seedEncounter(run_id, 1, 1)
    const slot = addToParty(run_id, 1, pokemonId)
    expect(slot).toBe(1)
  })

  it('is idempotent for the same pokemon', () => {
    const { run_id } = createRun({ game_id: 1 }, 'Run')
    const pokemonId = seedEncounter(run_id, 1, 1)
    const first = addToParty(run_id, 1, pokemonId)
    const second = addToParty(run_id, 1, pokemonId)
    expect(first).toBe(second)
    expect(getParty(run_id, 1)).toHaveLength(1)
  })

  it('caps the party at 6 pokemon', () => {
    const { run_id } = createRun({ game_id: 1 }, 'Run')
    const ids = Array.from({ length: 7 }, (_, i) => seedEncounter(run_id, 1, i + 1))

    const slots = ids.slice(0, 6).map(id => addToParty(run_id, 1, id))
    expect(slots).toEqual([1, 2, 3, 4, 5, 6])

    const seventh = addToParty(run_id, 1, ids[6])
    expect(seventh).toBeNull()
  })

  it('removeFromParty frees the slot for reuse', () => {
    const { run_id } = createRun({ game_id: 1 }, 'Run')
    const ids = Array.from({ length: 7 }, (_, i) => seedEncounter(run_id, 1, i + 1))
    ids.slice(0, 6).forEach(id => addToParty(run_id, 1, id))

    removeFromParty(run_id, 1, ids[2]) // frees slot 3
    const newSlot = addToParty(run_id, 1, ids[6])

    expect(newSlot).toBe(3)
  })

  it('refuses to add a pokemon that has no recorded encounter', () => {
    const { run_id } = createRun({ game_id: 1 }, 'Run')
    const slot = addToParty(run_id, 1, 999999)
    expect(slot).toBeNull()
  })
})

describe('markTrainerVictory + getSessionStats', () => {
  it('marking the same trainer twice does not double-count', () => {
    const { run_id } = createRun({ game_id: 1 }, 'Run')
    markTrainerVictory(run_id, 1, 5, 12)
    markTrainerVictory(run_id, 1, 5, 12)

    const stats = getSessionStats(run_id, 1)
    expect(stats.trainers_defeated).toBe(1)
    expect(stats.badges_earned).toBe(1)
  })

  it('session stats reflect caught/dead/missed counts', () => {
    const { run_id } = createRun({ game_id: 1 }, 'Run')
    upsertEncounter(run_id, 1, 1, 0, 1, 'A', null, null, 'Captured', false)
    upsertEncounter(run_id, 1, 2, 0, 2, 'B', null, null, 'Dead', false)
    upsertEncounter(run_id, 1, 3, 0, 3, 'C', null, null, 'Missed', false)

    const stats = getSessionStats(run_id, 1)
    expect(stats.pokemon_caught).toBe(1)
    expect(stats.pokemon_dead).toBe(1)
    expect(stats.pokemon_missed).toBe(1)
  })
})

describe('bonus locations', () => {
  it('add / delete round-trips cleanly', () => {
    const { run_id } = createRun({ game_id: 1 }, 'Run')
    const added = addBonusLocation(run_id, 1, 42)
    expect(added.success).toBe(true)
    expect(getBonusLocations(run_id, 1)).toHaveLength(1)

    const deleted = deleteBonusLocation(run_id, 1, 42, added.secondary_sort_order)
    expect(deleted.success).toBe(true)
    expect(getBonusLocations(run_id, 1)).toHaveLength(0)
  })

  it('rename updates the stored name', () => {
    const { run_id } = createRun({ game_id: 1 }, 'Run')
    const added = addBonusLocation(run_id, 1, 42)
    renameBonusLocation(run_id, 1, 42, added.secondary_sort_order, 'Custom Name')

    const [location] = getBonusLocations(run_id, 1)
    expect(location.canonical_name).toBe('Custom Name')
  })

  it('secondary sort order increments across multiple bonus locations at the same canonical location', () => {
    const { run_id } = createRun({ game_id: 1 }, 'Run')
    const first = addBonusLocation(run_id, 1, 42)
    const second = addBonusLocation(run_id, 1, 42)
    expect(second.secondary_sort_order).toBeGreaterThan(first.secondary_sort_order)
  })

  it('starts above the base row secondary sort so keys never collide with the canonical row', () => {
    const { run_id } = createRun({ game_id: 1 }, 'Run')
    // Dreamyard-style placement: the canonical row itself sits at secondary 1.
    const added = addBonusLocation(run_id, 1, 234, 1)
    expect(added.secondary_sort_order).toBe(2)
  })
})
