import React, { act } from 'react'
import { createRoot } from 'react-dom/client'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import Box from './Box'
import {
  getBox, getParty, getRunDetails, getSpeciesLearnset, updateEncounterStatus, removeFromParty,
} from '../utils/dataLayer'

vi.mock('react-router-dom', () => ({
  useParams: () => ({ runId: '7', attemptId: '2' }),
}))

vi.mock('../utils/dataLayer', () => ({
  isLocalRun: () => false,
  getRunDetails: vi.fn(),
  getBox: vi.fn(),
  getParty: vi.fn(),
  getSpeciesSummary: vi.fn(),
  getSpeciesLearnset: vi.fn(),
  addToParty: vi.fn(),
  removeFromParty: vi.fn(),
  updateEncounterStatus: vi.fn(),
}))

vi.mock('../utils/api', () => ({
  apiFetch: vi.fn((url) => {
    if (url.startsWith('/api/evolutions/')) return Promise.resolve({ json: () => Promise.resolve([]) })
    if (url.startsWith('/api/pokemon/')) {
      return Promise.resolve({ json: () => Promise.resolve({ trainers_defeated_count: 3, bosses_defeated_count: 1, rivals_defeated_count: 0, badges_earned: [] }) })
    }
    return Promise.resolve({ json: () => Promise.resolve([]) })
  }),
}))

vi.mock('../components/AttemptHeader', () => ({ default: () => null }))
vi.mock('../components/AttemptSidePanel', () => ({ default: () => null }))
vi.mock('../components/Sprite', () => ({ default: () => <span /> }))

const snivy = {
  pokemon_id: 1, species_id: 495, species_name: 'Snivy', nickname: 'Salad', nature: 'Modest',
  status: 'Captured', shiny: false, gender: 'female', level_met: 5, location_name: 'Nuvema Town',
  type1: 'Grass', type2: null, ability: 'Overgrow', ability1: 'Overgrow', ability3: 'Contrary',
  hp: 45, atk: 45, def: 55, spa: 45, spd: 55, spe: 63, bst: 308, location_id: 1, bonus_location: 0,
}
const patrat = {
  pokemon_id: 2, species_id: 504, species_name: 'Patrat', nickname: null, nature: 'Hardy',
  status: 'Dead', shiny: false, gender: 'male', level_met: 3, location_name: 'Route 1',
  type1: 'Normal', type2: null, hp: 45, atk: 55, def: 39, spa: 35, spd: 39, spe: 42, bst: 255,
  location_id: 2, bonus_location: 0,
}

async function flush() {
  await act(async () => { await Promise.resolve() })
  await act(async () => { await Promise.resolve() })
}

describe('Box page', () => {
  let container
  let root

  beforeEach(async () => {
    getRunDetails.mockResolvedValue({ run_id: 7, game_id: 17, game_name: 'Black' })
    getBox.mockResolvedValue([snivy, patrat])
    getParty.mockResolvedValue([{ pokemon_id: 1 }])
    getSpeciesLearnset.mockResolvedValue({ version_group_id: 11, moves: [
      { learn_level: 1, move_id: 33, move_name: 'Tackle', type: 'Normal', damage_class: 'Physical', power: 40, accuracy: 100 },
      { learn_level: 7, move_id: 22, move_name: 'Vine Whip', type: 'Grass', damage_class: 'Physical', power: 45, accuracy: 100 },
    ] })
    updateEncounterStatus.mockResolvedValue({})
    removeFromParty.mockResolvedValue({})
    container = document.createElement('div')
    document.body.appendChild(container)
    root = createRoot(container)
    await act(async () => { root.render(<Box />) })
    await flush()
  })

  afterEach(async () => {
    await act(async () => { root.unmount() })
    container.remove()
    vi.clearAllMocks()
  })

  it('splits the box into alive and fallen sections', () => {
    const living = container.querySelector('#box-living-heading')
    const fallen = container.querySelector('#box-fallen-heading')
    expect(living.textContent).toContain('1 alive')
    expect(fallen.textContent).toContain('1 lost')
    const tiles = [...container.querySelectorAll('.box-tile')]
    expect(tiles.map(t => t.textContent)).toEqual([
      expect.stringContaining('Salad'),
      expect.stringContaining('Patrat'),
    ])
    expect(tiles[0].classList.contains('box-tile--party')).toBe(true)
    expect(tiles[1].classList.contains('box-tile--fallen')).toBe(true)
  })

  it('opens the summary for a selected Pokemon with its abilities, stats, learnset and record', async () => {
    expect(container.querySelector('.box-page__summary-placeholder')).not.toBeNull()

    await act(async () => { container.querySelector('.box-tile').click() })
    await flush()

    const summary = container.querySelector('.pokemon-summary')
    expect(summary).not.toBeNull()
    expect(summary.querySelector('.pokemon-summary__name').textContent).toContain('Salad')
    expect(summary.querySelector('.pokemon-summary__species').textContent).toBe('Snivy')
    expect(getSpeciesLearnset).toHaveBeenCalledWith(495, 17)

    const abilities = [...summary.querySelectorAll('.pokemon-summary__ability')].map(a => a.textContent)
    expect(abilities).toEqual(['Overgrow', 'Contraryhidden'])
    expect(summary.querySelector('.pokemon-summary__ability--chosen').textContent).toBe('Overgrow')

    expect(summary.querySelector('.pokemon-summary__bst').textContent).toBe('BST 308')
    const moveNames = [...summary.querySelectorAll('.pokemon-summary__move-name')].map(m => m.textContent)
    expect(moveNames).toEqual(['Tackle', 'Vine Whip'])
    // Level 1 is at or under the level met (5); level 7 is not.
    expect(summary.querySelectorAll('.pokemon-summary__move--known').length).toBe(1)

    const record = [...summary.querySelectorAll('.pokemon-summary__record strong')].map(s => s.textContent)
    expect(record).toEqual(['3', '1', '0'])

    // In the party already, so the action offers removal.
    expect(summary.querySelector('.pokemon-summary__action--remove')).not.toBeNull()
    expect(summary.querySelector('.pokemon-summary__action--add')).toBeNull()
  })

  it('marking a Pokemon fallen needs a confirmation and moves it to the fallen section', async () => {
    await act(async () => { container.querySelector('.box-tile').click() })
    await flush()

    await act(async () => { container.querySelector('.pokemon-summary__action--dead').click() })
    expect(updateEncounterStatus).not.toHaveBeenCalled()
    const confirm = [...container.querySelectorAll('.pokemon-summary__action')].find(b => b.textContent === 'Confirm fallen')
    expect(confirm).toBeDefined()

    await act(async () => { confirm.click() })
    await flush()

    expect(updateEncounterStatus).toHaveBeenCalledWith('7', '2', expect.objectContaining({ pokemon_id: 1, status: 'Dead', bonus_location: 0 }))
    expect(removeFromParty).toHaveBeenCalledWith('7', '2', 1)
    expect(container.querySelector('#box-living-heading').textContent).toContain('0 alive')
    expect(container.querySelector('#box-fallen-heading').textContent).toContain('2 lost')
    // The summary stays open on the now-fallen Pokemon and offers Revive.
    expect(container.querySelector('.pokemon-summary__action--revive')).not.toBeNull()
  })

  it('revives a fallen Pokemon back into the box', async () => {
    const fallenTile = container.querySelector('.box-tile--fallen')
    await act(async () => { fallenTile.click() })
    await flush()

    await act(async () => { container.querySelector('.pokemon-summary__action--revive').click() })
    await flush()

    expect(updateEncounterStatus).toHaveBeenCalledWith('7', '2', expect.objectContaining({ pokemon_id: 2, status: 'Captured' }))
    expect(container.querySelector('#box-living-heading').textContent).toContain('2 alive')
    expect(container.querySelector('#box-fallen-heading').textContent).toContain('0 lost')
  })
})
