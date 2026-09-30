import React, { act } from 'react'
import { createRoot } from 'react-dom/client'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import LocationRow from './LocationRow'
import { apiFetch } from '../utils/api'
import { deleteEncounterById, saveEncounter } from '../utils/dataLayer'

vi.mock('../contexts/AuthContext', () => ({
  useAuth: () => ({ user: null }),
}))

vi.mock('../utils/api', () => ({
  apiFetch: vi.fn(),
}))

vi.mock('../utils/dataLayer', () => ({
  saveEncounter: vi.fn(),
  deleteEncounterById: vi.fn(),
  getTrainerList: vi.fn(),
  addBonusLocation: vi.fn(),
  deleteBonusLocation: vi.fn(),
  renameBonusLocation: vi.fn(),
  addToParty: vi.fn(),
  removeFromParty: vi.fn(),
  getParty: vi.fn(),
  markTrainerVictory: vi.fn(),
  endAttempt: vi.fn(),
}))

vi.mock('./Sprite', () => ({
  default: () => <span />,
}))

const METHODS = [
  { key: 'grass', label: 'Tall grass', group: 'grass', is_rare: false, sort_order: 10, description: '' },
  { key: 'sand', label: 'Desert sand', group: 'ground', is_rare: false, sort_order: 70, description: '' },
  { key: 'static', label: 'Static encounter', group: 'special', is_rare: false, sort_order: 160, description: '' },
]
const slot = (over) => ({
  species_id: 1, name: 'X', method: 'sand', area: null, area_sort: 0, condition: null,
  slot_kind: 'slot', tag: null, rate: 20, min_level: null, max_level: null, note: null, ...over,
})
const TABLES = [
  slot({ species_id: 551, name: 'SANDILE', area: '1F', area_sort: 1, rate: 60 }),
  slot({ species_id: 27, name: 'SANDSHREW', area: '1F', area_sort: 1, rate: 40 }),
  slot({ species_id: 637, name: 'VOLCARONA', method: 'static', area: 'Volcarona Room', area_sort: 2, rate: null, slot_kind: 'static', tag: 'special', min_level: 75, max_level: 75 }),
]
const POOL = [{ species_id: 551, name: 'SANDILE' }, { species_id: 27, name: 'SANDSHREW' }, { species_id: 637, name: 'VOLCARONA' }]
const EMPTY = []
const DUPED = new Set()
const PARTY = new Set()
const ROW = {
  event_id: 240,
  event_type: 'Location',
  display_name: 'Relic Castle',
  encounter_key: '240:0',
  secondary_sort_order: 0,
  trainer_count: 0,
  available_trainer_count: 0,
}

describe('LocationRow: encounter tables in the blank state', () => {
  let container
  let root

  beforeEach(() => {
    globalThis.IS_REACT_ACT_ENVIRONMENT = true
    container = document.createElement('div')
    document.body.appendChild(container)
    root = createRoot(container)
    apiFetch.mockReset()
    apiFetch.mockImplementation(() => Promise.resolve({ ok: true, json: async () => [] }))
    saveEncounter.mockReset()
    saveEncounter.mockResolvedValue({ success: true, pokemon_id: 42 })
    deleteEncounterById.mockReset()
    deleteEncounterById.mockResolvedValue({ success: true })
    localStorage.clear()
  })

  afterEach(async () => {
    await act(async () => root.unmount())
    container.remove()
  })

  const renderRow = async (props = {}) => {
    await act(async () => {
      root.render(
        <LocationRow
          row={ROW}
          runId={1}
          attemptNumber={1}
          gameId={1001}
          viewMode="encounters"
          pool={POOL}
          poolTables={TABLES}
          encounterMethods={METHODS}
          allSpecies={EMPTY}
          dupedFamilyIds={DUPED}
          partyPokemonIds={PARTY}
          {...props}
        />
      )
    })
  }
  const click = async (el) => act(async () => { el.dispatchEvent(new MouseEvent('click', { bubbles: true })) })
  const encounterButton = () => container.querySelector('.location-row__encounter-button')
  const tables = () => container.querySelector('.encounter-tables')
  const editor = () => container.querySelector('.encounter-editor')
  const tableRow = (name) => [...container.querySelectorAll('.encounter-tables__row')].find(r => r.textContent.includes(name))
  const buttonNamed = (text) => [...container.querySelectorAll('button')].find(b => b.textContent.trim() === text)

  const confirmBar = () => container.querySelector('.encounter-confirm')
  const confirmCaught = () => container.querySelector('.encounter-confirm__caught')
  const confirmMissed = () => container.querySelector('.encounter-confirm__missed')
  const typeInto = async (input, value) => act(async () => {
    const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set
    setter.call(input, value)
    input.dispatchEvent(new Event('input', { bubbles: true }))
  })
  const wait = (ms) => act(async () => { await new Promise(resolve => setTimeout(resolve, ms)) })

  it('opens on the tables, and a tap only selects: the confirm bar decides', async () => {
    await renderRow()
    expect(encounterButton().textContent).toContain('Choose encounter')
    await click(encounterButton())
    expect(tables()).toBeTruthy()
    expect(editor()).toBeNull()
    expect(container.querySelector('input[placeholder="Search any species"]')).toBeTruthy()
    // nothing selected: the bar asks for a pick and cannot decide
    expect(confirmBar().textContent).toContain('Tap a Pokémon to select it')
    expect(confirmCaught().disabled).toBe(true)
    expect(confirmMissed().disabled).toBe(true)

    await click(tableRow('SANDILE'))
    // still the tables, nothing saved, the summary undecided
    expect(tables()).toBeTruthy()
    expect(editor()).toBeNull()
    expect(tableRow('SANDILE').getAttribute('aria-pressed')).toBe('true')
    expect(confirmBar().textContent).toContain('SANDILE')
    expect(confirmBar().textContent).toContain('Desert sand · 60% · 1F')
    expect(confirmCaught().disabled).toBe(false)
    expect(encounterButton().textContent).toContain('Choose encounter')
    expect(saveEncounter).not.toHaveBeenCalled()

    // another tap moves the selection; a tap on the selected row clears it
    await click(tableRow('SANDSHREW'))
    expect(tableRow('SANDILE').getAttribute('aria-pressed')).toBe('false')
    expect(confirmBar().textContent).toContain('SANDSHREW')
    await click(tableRow('SANDSHREW'))
    expect(confirmBar().textContent).toContain('Tap a Pokémon to select it')
    expect(saveEncounter).not.toHaveBeenCalled()
  })

  it('Caught saves the selection exactly once and opens the stat screen', async () => {
    const onStatusChange = vi.fn()
    await renderRow({ onStatusChange })
    await click(encounterButton())
    await click(tableRow('SANDSHREW'))
    await click(confirmCaught())

    expect(saveEncounter).toHaveBeenCalledTimes(1)
    const args = saveEncounter.mock.calls[0]
    expect(args.slice(0, 6)).toEqual([1, 1, 240, 0, 27, 'SANDSHREW'])
    expect(args).toContain('Captured')
    expect(onStatusChange).toHaveBeenCalledWith('240:0', 27, 'Captured')
    expect(tables()).toBeNull()
    expect(editor()).toBeTruthy()
    expect(encounterButton().textContent).toContain('SANDSHREW')
    // where it came from stays visible after the save, with no Change
    expect(container.querySelector('.encounter-provenance').textContent).toContain('Desert sand · 40% · 1F')
    expect(buttonNamed('Change')).toBeUndefined()
    await wait(0)
    expect(buttonNamed('Party')).toBeTruthy()
  })

  it('Undo after Caught deletes the encounter and returns to the tables with the pick selected', async () => {
    await renderRow()
    await click(encounterButton())
    await click(tableRow('SANDILE'))
    await click(confirmCaught())
    await wait(0)
    // details typed on the stat screen are discarded with the encounter
    await typeInto(container.querySelector('input[placeholder="Nickname"]'), 'Croc')
    await typeInto(container.querySelector('input[aria-label="HP IV"]'), '31')
    await click(container.querySelector('button[title="Toggle shiny"]'))

    await click(buttonNamed('Undo'))
    expect(deleteEncounterById).toHaveBeenCalledWith(1, 1, 42)
    expect(tables()).toBeTruthy()
    expect(encounterButton().textContent).toContain('Choose encounter')
    expect(tableRow('SANDILE').getAttribute('aria-pressed')).toBe('true')
    expect(confirmBar().textContent).toContain('SANDILE')

    saveEncounter.mockClear()
    await click(tableRow('SANDSHREW'))
    await click(confirmCaught())
    expect(saveEncounter).toHaveBeenCalledTimes(1)
    const args = saveEncounter.mock.calls[0]
    expect(args[4]).toBe(27)
    expect(args[6]).toBe('')      // nickname
    expect(args[9]).toBe(false)   // shiny
    expect(args[13].hp ?? null).toBeNull()
  })

  it('selects a static from the rare strip and confirms it', async () => {
    await renderRow()
    await click(encounterButton())
    const chip = [...container.querySelectorAll('.encounter-tables__chip')].find(c => c.textContent.includes('VOLCARONA'))
    await click(chip)
    expect(editor()).toBeNull()
    expect(confirmBar().textContent).toContain('Static encounter · Static · Volcarona Room · Lv 75')
    await click(confirmMissed())
    expect(saveEncounter).toHaveBeenCalledTimes(1)
    expect(saveEncounter.mock.calls[0]).toContain('Missed')
    expect(container.querySelector('.encounter-provenance').textContent).toContain('Static encounter · Static · Volcarona Room · Lv 75')
  })

  it('opens straight on the editor when an encounter is already saved', async () => {
    await renderRow({ savedEncounter: { pokemon_id: 7, species_id: 551, species_name: 'SANDILE', status: 'Captured', nickname: 'Croc' } })
    expect(encounterButton().textContent).toContain('Croc')
    await click(encounterButton())
    expect(editor()).toBeTruthy()
    expect(tables()).toBeNull()
    expect(confirmBar()).toBeNull()
    expect(container.querySelector('.encounter-provenance')).toBeNull()
  })

  it('selects from the plain pool when a game has no tables; Missed then Undo comes back selected', async () => {
    await renderRow({ poolTables: EMPTY })
    expect(encounterButton().textContent).toContain('Log encounter')
    await click(encounterButton())
    expect(tables()).toBeTruthy()
    await click(tableRow('SANDSHREW'))
    expect(confirmBar().textContent).toContain('Encounter list')
    await click(confirmMissed())
    expect(saveEncounter).toHaveBeenCalledTimes(1)
    expect(container.querySelector('.encounter-provenance').textContent).toContain('Encounter list')
    await wait(0)

    await click(buttonNamed('Undo'))
    expect(deleteEncounterById).toHaveBeenCalledWith(1, 1, 42)
    expect(tables()).toBeTruthy()
    expect(tableRow('SANDSHREW').getAttribute('aria-pressed')).toBe('true')

    await act(async () => root.unmount())
    container.remove()
    container = document.createElement('div')
    document.body.appendChild(container)
    root = createRoot(container)
    await renderRow({ poolTables: EMPTY, pool: EMPTY })
    await click(encounterButton())
    expect(container.textContent).toContain('No wild encounters documented for Relic Castle')
  })

  it('a search result in the tables selects instead of opening the editor', async () => {
    const species = [{ species_id: 25, name: 'PIKACHU' }]
    await renderRow({ allSpecies: species })
    await click(encounterButton())
    const input = container.querySelector('input[placeholder="Search any species"]')
    await typeInto(input, 'pika')
    const option = [...container.querySelectorAll('span')].find(el => el.textContent === 'PIKACHU')
    await click(option.parentElement)
    expect(tables()).toBeTruthy()
    expect(confirmBar().textContent).toContain('PIKACHU')
    expect(confirmBar().textContent).toContain('Searched')
    expect(saveEncounter).not.toHaveBeenCalled()
  })

  it('shows the tables when the only saved entry is a status that never reached the server', async () => {
    // Attempt keeps an optimistic {species_id, status} entry and rolls a failed
    // create back to status '', leaving an object with no pokemon behind it.
    await renderRow({ savedEncounter: { species_id: 551, status: '' } })
    expect(encounterButton().textContent).toContain('Choose encounter')
    await click(encounterButton())
    expect(tables()).toBeTruthy()
    expect(editor()).toBeNull()
  })

  it('after a failed save, retyping keeps focus and no new pick inherits the status', async () => {
    const onStatusChange = vi.fn()
    saveEncounter.mockReset()
    saveEncounter.mockRejectedValueOnce(new Error('offline'))
    saveEncounter.mockResolvedValue({ success: true, pokemon_id: 42 })
    const errors = vi.spyOn(console, 'error').mockImplementation(() => {})
    try {
      await renderRow({ onStatusChange })
      await click(encounterButton())
      await click(tableRow('SANDILE'))
      await click(confirmCaught())
      await wait(0)
      expect(buttonNamed('Retry Save')).toBeTruthy()

      // the player changes their mind about the species instead of retrying
      const input = container.querySelector('input[placeholder="Encounter"]')
      await act(async () => { input.focus() })
      await typeInto(input, 'SAND')
      expect(input.isConnected).toBe(true)
      expect(document.activeElement).toBe(input)
      expect(editor()).toBeTruthy()
      expect(buttonNamed('Retry Save')).toBeUndefined()
      await typeInto(input, '')
      expect(document.activeElement).toBe(input)

      await click(buttonNamed('Back to tables'))
      await click(tableRow('SANDSHREW'))
      await wait(700)
      expect(saveEncounter).toHaveBeenCalledTimes(1)
      expect(confirmCaught().disabled).toBe(false)
    } finally {
      errors.mockRestore()
    }
  })

  it('Cancel after a failed save returns to the tables with the pick selected', async () => {
    saveEncounter.mockReset()
    saveEncounter.mockRejectedValueOnce(new Error('offline'))
    const errors = vi.spyOn(console, 'error').mockImplementation(() => {})
    try {
      await renderRow()
      await click(encounterButton())
      await click(tableRow('SANDILE'))
      await click(confirmCaught())
      await wait(0)
      await click(buttonNamed('Cancel'))
      expect(deleteEncounterById).not.toHaveBeenCalled()
      expect(tables()).toBeTruthy()
      expect(tableRow('SANDILE').getAttribute('aria-pressed')).toBe('true')
    } finally {
      errors.mockRestore()
    }
  })

  it('locks the species search and hides Change while the create is in flight', async () => {
    let resolveSave
    saveEncounter.mockReset()
    saveEncounter.mockReturnValue(new Promise(resolve => { resolveSave = resolve }))
    await renderRow()
    await click(encounterButton())
    await click(tableRow('SANDILE'))
    await click(confirmCaught())
    const input = container.querySelector('input[placeholder="Encounter"]')
    expect(input.readOnly).toBe(true)
    expect(buttonNamed('Saving...')).toBeTruthy()
    expect(buttonNamed('Change')).toBeUndefined()
    await act(async () => { resolveSave({ success: true, pokemon_id: 42 }) })
    expect(input.readOnly).toBe(false)
  })

  it('hides Change after a failed save: the choice is Retry or Cancel', async () => {
    saveEncounter.mockReset()
    saveEncounter.mockRejectedValueOnce(new Error('offline'))
    const errors = vi.spyOn(console, 'error').mockImplementation(() => {})
    try {
      await renderRow()
      await click(encounterButton())
      await click(tableRow('SANDILE'))
      await click(confirmCaught())
      await wait(0)
      expect(buttonNamed('Retry Save')).toBeTruthy()
      expect(buttonNamed('Change')).toBeUndefined()
      expect(container.querySelector('input[placeholder="Encounter"]').readOnly).toBe(false)
    } finally {
      errors.mockRestore()
    }
  })

  it('clearing a row while its create is in flight leaves the row usable', async () => {
    saveEncounter.mockReset()
    saveEncounter.mockReturnValueOnce(new Promise(() => {}))   // never settles
    saveEncounter.mockResolvedValue({ success: true, pokemon_id: 43 })
    await renderRow()
    await click(encounterButton())
    await click(tableRow('SANDILE'))
    await click(confirmCaught())
    expect(buttonNamed('Saving...')).toBeTruthy()

    await click(container.querySelector('.location-row__menu > button'))
    const clear = [...container.querySelectorAll('button.menu-item')].find(d => d.textContent === 'Clear encounter')
    await click(clear)

    await click(encounterButton())
    expect(tables()).toBeTruthy()
    expect(container.querySelector('input[placeholder="Search any species"]').readOnly).toBe(false)
    await click(tableRow('SANDSHREW'))
    expect(confirmCaught().disabled).toBe(false)
    await click(confirmCaught())
    expect(saveEncounter).toHaveBeenCalledTimes(2)
    await wait(0)
    expect(buttonNamed('Party')).toBeTruthy()
  })

  it('a species picked from the dropdown after a failed save does not inherit its status', async () => {
    const species = [{ species_id: 551, name: 'SANDILE' }, { species_id: 553, name: 'SANDILEX' }]
    saveEncounter.mockReset()
    saveEncounter.mockRejectedValueOnce(new Error('offline'))
    saveEncounter.mockResolvedValue({ success: true, pokemon_id: 42 })
    const errors = vi.spyOn(console, 'error').mockImplementation(() => {})
    try {
      await renderRow({ allSpecies: species })
      await click(encounterButton())
      await click(tableRow('SANDILE'))
      await click(confirmCaught())
      await wait(0)
      expect(buttonNamed('Retry Save')).toBeTruthy()

      // focusing (without typing) opens the dropdown filtered by the name
      const input = container.querySelector('input[placeholder="Encounter"]')
      await act(async () => { input.dispatchEvent(new FocusEvent('focusin', { bubbles: true })) })
      await act(async () => { input.focus() })
      const option = [...container.querySelectorAll('span')].find(el => el.textContent === 'SANDILEX')
      await click(option.parentElement)
      await wait(700)
      expect(saveEncounter).toHaveBeenCalledTimes(1)
      expect(buttonNamed('Retry Save')).toBeUndefined()
      expect(buttonNamed('Caught')).toBeTruthy()
    } finally {
      errors.mockRestore()
    }
  })

  it('disables the selection and the confirm bar when the attempt has ended', async () => {
    await renderRow({ attemptEnded: true })
    await click(encounterButton())
    expect(tableRow('SANDILE').disabled).toBe(true)
    expect(confirmBar().textContent).toContain('This attempt has ended')
    expect(confirmCaught().disabled).toBe(true)
  })

  it('shows the season it is given and reports a pick to its owner', async () => {
    const seasonal = [
      slot({ species_id: 420, name: 'CHERUBI', method: 'grass', condition: 'season:spring,summer,autumn', rate: 100 }),
      slot({ species_id: 459, name: 'SNOVER', method: 'grass', condition: 'season:winter', rate: 100 }),
    ]
    const onSeasonChange = vi.fn()
    await renderRow({ poolTables: seasonal, season: 'winter', onSeasonChange })
    await click(encounterButton())
    expect(tableRow('SNOVER')).toBeTruthy()
    await click(buttonNamed('Summer'))
    expect(onSeasonChange).toHaveBeenCalledWith('summer')
    // the owner decides: until it re-renders with summer, winter stays
    expect(tableRow('SNOVER')).toBeTruthy()
    await renderRow({ poolTables: seasonal, season: 'summer', onSeasonChange })
    expect(tableRow('CHERUBI')).toBeTruthy()
  })

  it('remembers the chosen season per run', async () => {
    const seasonal = [
      slot({ species_id: 420, name: 'CHERUBI', method: 'grass', condition: 'season:spring,summer,autumn', rate: 100 }),
      slot({ species_id: 459, name: 'SNOVER', method: 'grass', condition: 'season:winter', rate: 100 }),
    ]
    await renderRow({ poolTables: seasonal })
    await click(encounterButton())
    await click(buttonNamed('Winter'))
    expect(tableRow('SNOVER')).toBeTruthy()
    expect(tableRow('CHERUBI')).toBeUndefined()
    expect(localStorage.getItem('lockley:season:1')).toBe('winter')
  })
})
