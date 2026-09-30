import React, { act } from 'react'
import { createRoot } from 'react-dom/client'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import SplitSection from './SplitSection'
import { buildSplitFeed } from '../utils/splitFeed'

vi.mock('../utils/dataLayer', () => ({ saveSplitItem: vi.fn() }))
vi.mock('./Sprite', () => ({ default: () => <span /> }))

const splits = [
  { split_key: 'badge:33', ordinal: 0, kind: 'gym', label: 'Cress', type_focus: 'Water', level_cap: 14, title: 'Striaton City Gym', battle_type: 'rotation', final_trainer_id: 500, reveal_after: null },
  { split_key: 'badge:34', ordinal: 1, kind: 'gym', label: 'Lenora', type_focus: 'Normal', level_cap: 20, title: 'Nacrene City Gym', battle_type: 'double', final_trainer_id: 501, reveal_after: null },
  { split_key: 'postgame', ordinal: 2, kind: 'postgame', label: 'Postgame', final_trainer_id: null, reveal_after: 'badge:34' },
]
const methods = [{ key: 'grass-spots', label: 'Shaking grass', group: 'grass', is_rare: true }, { key: 'fish', label: 'Fishing', group: 'fishing' }]
const script = [
  { event_id: 3, display_name: 'Route 1', event_type: 'Location', boss_event_id: null, encounter_key: '3:0', home_split: 'badge:33', trainer_count: 3, available_trainer_count: 1,
    revisits: [{ split_key: 'badge:34', tables: [{ area: null, method: 'grass-spots', rare: [{ species_id: 385, name: 'JIRACHI', rate: 1 }] }, { area: null, method: 'fish', rare: [] }], areas: [], trainers: [
      { trainer_id: 2, trainer_name: 'PLASMA GRUNT', trainer_class: 'TRAINER_CLASS_PLASMA_GRUNT', max_level: 15, is_defeated: false },
    ] }] },
  { event_id: 500, display_name: 'Striaton City Gym', event_type: null, boss_event_id: 5000, home_split: 'badge:33', is_defeated: true },
  { event_id: 8, display_name: 'Route 3', event_type: 'Location', boss_event_id: null, encounter_key: '8:0', home_split: 'badge:34', trainer_count: 11, available_trainer_count: 11, revisits: [] },
  { event_id: 501, display_name: 'Nacrene City Gym', event_type: null, boss_event_id: 5010, home_split: 'badge:34', is_defeated: false },
]

let container, root
beforeEach(() => {
  globalThis.IS_REACT_ACT_ENVIRONMENT = true
  container = document.createElement('div'); document.body.appendChild(container); root = createRoot(container)
})
afterEach(async () => { await act(async () => root.unmount()); container.remove() })

function render(section, props = {}) {
  return act(async () => root.render(
    <SplitSection section={section} total={2} gameId={1001} encounterMethods={methods} expanded onToggle={() => {}} onJump={() => {}}
      renderRow={row => <div key={row.event_id} data-row={row.display_name}>{row.display_name}</div>} {...props} />
  ))
}

describe('SplitSection', () => {
  it('renders the band, the returns jump lists and the rows with the leader last', async () => {
    const feed = buildSplitFeed(script, splits, { '3:0': { status: 'Captured', nickname: 'Coo' } })
    const onJump = vi.fn()
    await render(feed.sections[1], { onJump, items: [{ item_record_id: 1, split_key: 'badge:34', item_name: 'Everstone', method: 'Thief', sources: [{ method_kind: 'thief', chance_percent: '50.00' }] }] })
    const text = container.textContent
    expect(text).toContain('Split 2 of 2 · current')
    expect(text).toContain('Lenora')
    expect(text).toContain('Level cap 20')
    expect(text).toContain('1 item · Thief 1')
    expect(text).toContain('Opened up in earlier areas')
    // Encounters: methods by name, the rare slot called out, the used state.
    const encounters = container.querySelector('[aria-label="New encounters in earlier areas"]')
    expect(encounters.textContent).toContain('Route 1')
    expect(encounters.textContent).toContain('Shaking grass')
    expect(encounters.textContent).toContain('Jirachi 1%')
    expect(encounters.textContent).toContain('Fishing')
    expect(encounters.textContent).toContain('Used · Coo')
    expect(encounters.textContent).not.toContain('table')
    // Trainers: grouped under the area, with class and level chips.
    const trainers = container.querySelector('[aria-label="New trainers in earlier areas"]')
    expect(trainers.textContent).toContain('Route 1')
    expect(trainers.textContent).toContain('Plasma Grunt · Lv 15')
    expect(trainers.textContent).toContain('0 / 1 beaten')
    // Rows: Route 3 then the leader under its own label.
    expect([...container.querySelectorAll('[data-row]')].map(el => el.dataset.row)).toEqual(['Route 3', 'Nacrene City Gym'])
    expect(text).toContain('Leader')
    await act(async () => trainers.querySelector('button').dispatchEvent(new MouseEvent('click', { bubbles: true })))
    expect(onJump).toHaveBeenCalledWith(expect.objectContaining({ encounterKey: '3:0', trainerIds: [2] }), 'trainers')
    await act(async () => encounters.querySelector('button').dispatchEvent(new MouseEvent('click', { bubbles: true })))
    expect(onJump).toHaveBeenLastCalledWith(expect.objectContaining({ encounterKey: '3:0' }), 'encounter')
  })

  it('collapses a beaten split to its band and hides the item editor from non-admins', async () => {
    const feed = buildSplitFeed(script, splits, {})
    await render(feed.sections[0], { expanded: false })
    expect(container.textContent).toContain('beaten')
    expect(container.querySelector('[data-row]')).toBeNull()
    expect(container.textContent).toContain('Expand')
    await render(feed.sections[0], { expanded: true })
    expect(container.querySelector('[data-row]')).toBeTruthy()
    expect(container.textContent).not.toContain('+ Add item')
  })
})
