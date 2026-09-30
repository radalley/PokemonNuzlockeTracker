import React, { act } from 'react'
import { createRoot } from 'react-dom/client'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import LocationRow from './LocationRow'
import { apiFetch } from '../utils/api'
import { getTrainerList } from '../utils/dataLayer'

const editState = vi.hoisted(() => ({ editMode: false }))

vi.mock('../contexts/EditModeContext', () => ({
  useEditMode: () => ({ canEdit: editState.editMode, editMode: editState.editMode, toggleEditMode: () => {} }),
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

const trainer = (id, name, extra = {}) => ({
  trainer_id: id,
  encounter_name: `TRAINER_${name}`,
  trainer_name: name,
  trainer_class: 'TRAINER_CLASS_YOUNGSTER',
  trainer_pic: null,
  trainer_items: null,
  version_group_id: 1001,
  area_id: null,
  area_name: null,
  area_kind: null,
  is_event: 0,
  is_rematch: 0,
  is_double: 0,
  is_defeated: 0,
  ...extra,
})

const ROW = {
  event_id: 3,
  event_type: 'Location',
  display_name: 'Route 3',
  encounter_key: '3:0',
  secondary_sort_order: 0,
  trainer_count: 3,
  available_trainer_count: 3,
}

// LocationRow's list/set props must keep their identity across renders
// (Attempt.jsx passes shared constants); fresh defaults would re-fire its
// encounter effects on every render.
const POOL = []
const SPECIES = []
const DUPED = new Set()
const PARTY = new Set()

const renderRow = (root) => act(async () => {
  root.render(
    <LocationRow
      row={ROW}
      runId={1}
      attemptNumber={1}
      gameId={1001}
      viewMode="trainers"
      pool={POOL}
      allSpecies={SPECIES}
      dupedFamilyIds={DUPED}
      partyPokemonIds={PARTY}
    />
  )
})

describe('LocationRow: admin trainer reorder', () => {
  let container
  let root

  beforeEach(() => {
    globalThis.IS_REACT_ACT_ENVIRONMENT = true
    container = document.createElement('div')
    document.body.appendChild(container)
    root = createRoot(container)
    editState.editMode = false
    apiFetch.mockReset()
    apiFetch.mockImplementation((url) => {
      if (url === '/api/admin/trainer-order') {
        return Promise.resolve({ ok: true, json: async () => ({ success: true }) })
      }
      return Promise.resolve({ ok: true, json: async () => [] })
    })
    getTrainerList.mockReset()
    getTrainerList.mockResolvedValue([trainer(1, 'ALPHA'), trainer(2, 'BRAVO'), trainer(3, 'CHARLIE')])
  })

  afterEach(async () => {
    await act(async () => root.unmount())
    container.remove()
  })

  const click = async (el) => act(async () => { el.dispatchEvent(new MouseEvent('click', { bubbles: true })) })
  // A click on the card root opens it.
  const openCard = (card) => click(card)
  const buttons = (scope = container) => [...scope.querySelectorAll('button')]
  const cards = () => [...container.querySelectorAll('.trainer-card')]
  const cardNames = () => cards().map(c => c.querySelector('.trainer-card-summary__identity').textContent.replace(/Youngster.*$/, ''))
  const cardFor = (name) => cards().find(c => c.textContent.includes(name))
  const orderPosts = () => apiFetch.mock.calls.filter(([url]) => url === '/api/admin/trainer-order')

  const openPanel = async () => {
    await renderRow(root)
    const trainersButton = buttons().find(b => b.textContent.trim().startsWith('Trainers'))
    await click(trainersButton)
    expect(cardNames()).toEqual(['ALPHA', 'BRAVO', 'CHARLIE'])
  }

  it('shows no reorder controls outside edit mode', async () => {
    await openPanel()
    await openCard(cardFor('BRAVO'))
    expect(buttons().some(b => b.textContent.trim() === 'Edit')).toBe(false)
    expect(container.querySelector('[aria-label="Drag to reorder"]')).toBeNull()
  })

  it('puts reorder controls on every card in edit mode and nudges with the arrows', async () => {
    editState.editMode = true
    await openPanel()
    // closed cards carry the controls too, left of Battle; no per-card Edit
    expect([...cardFor('BRAVO').querySelectorAll('.trainer-card-summary__battle button')].map(b => b.textContent.trim()))
      .toEqual(['⠿', '▲', '▼', 'Battle'])
    expect(cardFor('ALPHA').querySelector('[aria-label="Move down"]')).toBeTruthy()
    expect(buttons().some(b => ['Edit', 'Done'].includes(b.textContent.trim()))).toBe(false)

    await click(cardFor('BRAVO').querySelector('[aria-label="Move down"]'))
    expect(cardNames()).toEqual(['ALPHA', 'CHARLIE', 'BRAVO'])
    expect(orderPosts()).toHaveLength(1)
    expect(JSON.parse(orderPosts()[0][1].body)).toEqual({ trainer_ids: [1, 3, 2] })
    // now last: no further move down
    expect(cardFor('BRAVO').querySelector('[aria-label="Move down"]').disabled).toBe(true)
    expect(cardFor('BRAVO').querySelector('[aria-label="Move up"]').disabled).toBe(false)

    // the first card cannot move up: no request is sent
    await click(cardFor('ALPHA').querySelector('[aria-label="Move up"]'))
    expect(orderPosts()).toHaveLength(1)
  })

  it('drops a dragged card before or after a sibling in the same group', async () => {
    editState.editMode = true
    await openPanel()

    const handle = cardFor('CHARLIE').querySelector('[aria-label="Drag to reorder"]')
    const dataTransfer = { effectAllowed: '', dropEffect: '', setData: () => {}, setDragImage: () => {} }
    const dragEvent = (type, clientY = 0) => {
      const event = new MouseEvent(type, { bubbles: true, cancelable: true, clientY })
      Object.defineProperty(event, 'dataTransfer', { value: dataTransfer })
      return event
    }
    await act(async () => { handle.dispatchEvent(dragEvent('dragstart')) })
    await act(async () => { await new Promise(resolve => setTimeout(resolve, 0)) })

    // jsdom boxes are zero-sized, so any clientY lands "after" the target
    const alphaSlot = cardFor('ALPHA').parentElement
    await act(async () => { alphaSlot.dispatchEvent(dragEvent('dragover', 5)) })
    expect(alphaSlot.className).toContain('trainer-slot--drop-after')
    await act(async () => { alphaSlot.dispatchEvent(dragEvent('drop', 5)) })

    expect(cardNames()).toEqual(['ALPHA', 'CHARLIE', 'BRAVO'])
    expect(JSON.parse(orderPosts()[0][1].body)).toEqual({ trainer_ids: [1, 3, 2] })
    expect(container.querySelector('.trainer-slot--drop-after')).toBeNull()
  })

  it('ignores a drag over a card outside the dragged card’s group', async () => {
    editState.editMode = true
    getTrainerList.mockResolvedValue([
      trainer(1, 'ALPHA'), trainer(2, 'BRAVO'),
      trainer(3, 'GYMBO', { area_id: 9, area_name: 'Striaton Gym', area_kind: 'gym' }),
    ])
    await renderRow(root)
    await click(buttons().find(b => b.textContent.trim().startsWith('Trainers')))

    const dataTransfer = { effectAllowed: '', dropEffect: '', setData: () => {}, setDragImage: () => {} }
    const dragEvent = (type) => {
      const event = new MouseEvent(type, { bubbles: true, cancelable: true })
      Object.defineProperty(event, 'dataTransfer', { value: dataTransfer })
      return event
    }
    await act(async () => { cardFor('ALPHA').querySelector('[aria-label="Drag to reorder"]').dispatchEvent(dragEvent('dragstart')) })
    const gymSlot = cardFor('GYMBO').parentElement
    await act(async () => { gymSlot.dispatchEvent(dragEvent('dragover')) })
    expect(gymSlot.className).not.toContain('trainer-slot--drop')
    await act(async () => { gymSlot.dispatchEvent(dragEvent('drop')) })
    expect(orderPosts()).toHaveLength(0)
    expect(cardNames()).toEqual(['ALPHA', 'BRAVO', 'GYMBO'])
  })

  it('holds the controls while a save is pending, and keeps them through a list reload', async () => {
    editState.editMode = true
    let resolveSave
    apiFetch.mockImplementation((url) => {
      if (url === '/api/admin/trainer-order') {
        return new Promise(resolve => { resolveSave = () => resolve({ ok: true, json: async () => ({ success: true }) }) })
      }
      return Promise.resolve({ ok: true, json: async () => [] })
    })
    await openPanel()
    await click(cardFor('ALPHA').querySelector('[aria-label="Move down"]'))
    expect(cardNames()).toEqual(['BRAVO', 'ALPHA', 'CHARLIE'])
    // pending: every reorder control is off, a second click sends nothing
    expect(cardFor('ALPHA').querySelector('[aria-label="Move down"]').disabled).toBe(true)
    expect(cardFor('ALPHA').querySelector('[aria-label="Move up"]').disabled).toBe(true)
    expect(cardFor('ALPHA').querySelector('[aria-label="Drag to reorder"]').disabled).toBe(true)
    await click(cardFor('ALPHA').querySelector('[aria-label="Move down"]'))
    expect(orderPosts()).toHaveLength(1)

    await act(async () => { resolveSave() })
    expect(cardFor('ALPHA').querySelector('[aria-label="Move down"]').disabled).toBe(false)

    // reloading the list (special-trainers toggle) leaves edit mode on
    const toggle = container.querySelector('input[type="checkbox"]')
    await act(async () => { toggle.click() })
    expect(cardFor('ALPHA').querySelector('[aria-label="Move down"]')).toBeTruthy()
  })

  it('puts the order back and says so when the save fails', async () => {
    editState.editMode = true
    apiFetch.mockImplementation((url) => {
      if (url === '/api/admin/trainer-order') {
        return Promise.resolve({ ok: false, status: 400, json: async () => ({ error: 'Trainers can only be reordered within one location area' }) })
      }
      return Promise.resolve({ ok: true, json: async () => [] })
    })
    await openPanel()
    await click(cardFor('ALPHA').querySelector('[aria-label="Move down"]'))

    expect(cardNames()).toEqual(['ALPHA', 'BRAVO', 'CHARLIE'])
    expect(container.querySelector('.location-row__reorder-error').textContent).toContain('one location area')
  })
})
