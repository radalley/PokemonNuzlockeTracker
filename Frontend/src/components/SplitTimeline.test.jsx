import React, { act } from 'react'
import { createRoot } from 'react-dom/client'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import SplitTimeline from './SplitTimeline'
import { getBattleRecords, getSplitCatalogue, saveSplitItem } from '../utils/dataLayer'

vi.mock('../utils/dataLayer', () => ({ getBattleRecords: vi.fn(), getSplitCatalogue: vi.fn(), saveSplitItem: vi.fn() }))
const splits = [
  { split_key: 'badge:33', event_id: 582, trainer_id: 1, trainer_name: 'CHILI', type_focus: 'Fire', kind: 'gym', badge_id: 33 },
  { split_key: 'badge:34', event_id: 588, trainer_id: 2, trainer_name: 'LENORA', type_focus: 'Normal', kind: 'gym', badge_id: 34 },
  ...['Shauntal', 'Marshal', 'Grimsley', 'Caitlin', 'Alder'].map((name, i) => ({ split_key: `boss:${i}`, trainer_id: i + 3, event_id: i + 589, trainer_name: name, kind: i === 4 ? 'champion' : 'elite_four' })),
]
let container, root
beforeEach(() => {
  sessionStorage.clear()
  window.innerWidth = 1500
  getSplitCatalogue.mockResolvedValue({ splits, items: [{ item_record_id: 1, split_key: 'badge:33', item_name: 'Sitrus Berry', method: 'Thief', sources: [{ item_source_id: 1, method_kind: 'thief', source_species_id: 531, species_name: 'Audino', chance_percent: '5.00', source_detail: 'Audino' }] }] })
  getBattleRecords.mockResolvedValue([{ trainer_id: 1, split_key: 'badge:33', party: [{ slot: 1, pokemon_id: 10, species_id: 495, species_name: 'Snivy', nickname: 'Leaf', died_in_battle: true }] }])
  saveSplitItem.mockResolvedValue({})
  container = document.createElement('div'); document.body.appendChild(container); root = createRoot(container)
})
afterEach(async () => { await act(async () => root.unmount()); container.remove(); vi.clearAllMocks() })
async function render(admin = false) {
  await act(async () => root.render(<MemoryRouter><SplitTimeline runId="7" attemptId="1" gameId={1001} starter="Grass" editMode={admin} script={[{ event_id: 2, is_defeated: true }]} /></MemoryRouter>))
}
async function click(text) {
  await act(async () => [...container.querySelectorAll('button')].find(b => b.textContent === text).click())
}
it('keeps all leaders under filters, omits League tables, and links the historic form', async () => {
  await render()
  expect(container.querySelector('.split-timeline__title')?.textContent).toBe('Splits')
  expect(container.querySelector('.split-timeline__toggle')).toBeNull()
  expect(container.querySelectorAll('.split-card')).toHaveLength(7)
  expect(container.querySelectorAll('.split-item-group--thief')).toHaveLength(1)
  expect(container.querySelector('[aria-label="Chili items"]')).toBeTruthy()
  expect(container.querySelector('.split-card__mon').getAttribute('href')).toBe('/box/7/1?pokemon=10')
  expect(container.querySelector('.split-card__mon img').getAttribute('src')).toContain('/495.png')
  expect(container.querySelector('.split-card__mon--fallen')).toBeTruthy()
  expect(container.textContent).toContain('Party not recorded')
  expect(container.textContent).not.toContain('Victory party')
  expect(container.querySelector('input[type=checkbox]')).toBeNull()
  await click('Items')
  expect(container.querySelector('.split-card__mon')).toBeNull()
  expect(container.querySelectorAll('.split-card')).toHaveLength(7)
  await click('Parties')
  expect(container.querySelector('.split-item-groups')).toBeNull()
  expect(container.querySelectorAll('.split-card')).toHaveLength(7)
})
it('groups structured sources and shows their rates without duplicating the item editor', async () => {
  getSplitCatalogue.mockResolvedValue({ splits, items: [
    { item_record_id: 1, split_key: 'badge:34', item_name: 'Everstone', method: 'Multiple sources', sources: [
      { item_source_id: 1, method_kind: 'thief', source_species_id: 524, species_name: 'Roggenrola', chance_percent: '50.00', source_detail: 'Wellspring Cave 1F' },
      { item_source_id: 2, method_kind: 'dust_cloud', chance_percent: '3.00', source_detail: 'Wellspring Cave 1F' }
    ] }
  ] })
  await render(true)
  expect(container.querySelectorAll('.split-item')).toHaveLength(2)
  expect(container.querySelector('.split-item-group--thief').textContent).toContain('50%')
  expect(container.querySelector('.split-item-group--dust_cloud').textContent).toContain('3%')
  expect(container.querySelectorAll('[aria-label="Edit Everstone"]')).toHaveLength(2)
})
it('exposes exactly split/item/method for admins and appends via the shared endpoint', async () => {
  await render(true)
  await click('+ Add item')
  const form = container.querySelector('form')
  expect(form.querySelectorAll('select,input')).toHaveLength(3)
  expect(form.querySelectorAll('option')).toHaveLength(2)
  const inputs = form.querySelectorAll('input')
  await act(async () => {
    for (const [input, value] of [[inputs[0], 'Sitrus Berry'], [inputs[1], 'Thief - Audino 5%']]) {
      Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set.call(input, value)
      input.dispatchEvent(new Event('input', { bubbles: true }))
    }
  })
  await act(async () => form.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true })))
  expect(saveSplitItem).toHaveBeenCalledWith(1001, { split_key: 'badge:33', item_name: 'Sitrus Berry', method: 'Thief - Audino 5%' }, 'POST')
})
it('does not expose admin editing to ordinary users', async () => {
  await render()
  expect(container.textContent).not.toContain('+ Add item')
  expect(container.querySelector('[aria-label="Edit Sitrus Berry"]')).toBeNull()
})
