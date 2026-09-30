import React, { act } from 'react'
import { createRoot } from 'react-dom/client'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import GameFlagsPanel from './GameFlagsPanel'
import OpensInPicker from './OpensInPicker'
import { saveAvailabilityRule, saveGate } from '../utils/dataLayer'
import { splitIndexFrom } from '../utils/splitFeed'

vi.mock('../utils/dataLayer', () => ({ saveGate: vi.fn(), saveAvailabilityRule: vi.fn() }))

const splits = [
  { split_key: 'badge:33', ordinal: 0, kind: 'gym', label: 'Cress', type_focus: 'Water' },
  { split_key: 'badge:34', ordinal: 1, kind: 'gym', label: 'Lenora', type_focus: 'Normal' },
  { split_key: 'league', ordinal: 2, kind: 'league', label: 'Pokémon League' },
]
const gates = [
  { gate_key: 'surf', label: 'Surf', opens_in: null, default_methods: ['surf', 'surf-spots'], note: 'Not decided yet.' },
  { gate_key: 'fishing', label: 'Super Rod', opens_in: 'badge:34', default_methods: ['fish'], note: null },
]
const methods = [
  { key: 'surf', label: 'Surfing', group: 'water' }, { key: 'surf-spots', label: 'Rippling water', group: 'water' }, { key: 'fish', label: 'Fishing', group: 'fishing' },
]
const index = splitIndexFrom(splits)

let container, root
beforeEach(() => {
  globalThis.IS_REACT_ACT_ENVIRONMENT = true
  container = document.createElement('div'); document.body.appendChild(container); root = createRoot(container)
  saveGate.mockReset(); saveGate.mockResolvedValue({ gate_key: 'surf', opens_in: 'badge:34' })
  saveAvailabilityRule.mockReset(); saveAvailabilityRule.mockResolvedValue({})
})
afterEach(async () => { await act(async () => root.unmount()); container.remove() })

const click = el => act(async () => el.dispatchEvent(new MouseEvent('click', { bubbles: true })))
const buttons = () => [...container.querySelectorAll('button')]

describe('GameFlagsPanel', () => {
  it('lists each gate with its methods and saves a picked split', async () => {
    const onSaved = vi.fn()
    await act(async () => root.render(<GameFlagsPanel gameId={1001} gameName="Blaze Black" splits={splits} gates={gates} index={index} encounterMethods={methods} onSaved={onSaved} />))
    const text = container.textContent
    expect(text).toContain('Surf')
    expect(text).toContain('Surfing · Rippling water')
    expect(text).toContain('Split not set')
    expect(text).toContain('Opens in Lenora')
    const surfNotSet = buttons().find(b => b.textContent === 'Not set')
    expect(surfNotSet.getAttribute('aria-pressed')).toBe('true')
    await click(buttons().find(b => b.getAttribute('aria-label') === 'Surf opens in Lenora'))
    expect(saveGate).toHaveBeenCalledWith(1001, 'surf', 'badge:34')
    expect(onSaved).toHaveBeenCalled()
  })

  it('explains an empty gate list', async () => {
    await act(async () => root.render(<GameFlagsPanel gameId={17} splits={[]} gates={[]} />))
    expect(container.textContent).toContain('No flags for this game')
  })
})

describe('OpensInPicker', () => {
  const render = (current) => act(async () => root.render(
    <OpensInPicker gameId={1001} subjectKind="location" subjectKey="9" subjectLabel="Route 4" current={current} inheritedLabel="story order" splits={splits} gates={gates} index={index} onSaved={() => {}} />
  ))

  it('shows an inherited resolution and saves an explicit split', async () => {
    await render({ opens_in: 'badge:34', opens_rule: null })
    expect(buttons()[0].textContent).toContain('Inherits · Lenora')
    await click(buttons()[0])
    await click(buttons().find(b => b.getAttribute('aria-label') === 'Cress'))
    await click(buttons().find(b => b.textContent === 'Save'))
    expect(saveAvailabilityRule).toHaveBeenCalledWith(1001, 'location', '9', { opensIn: 'badge:33', gateKey: null, note: '' })
  })

  it('shows an explicit rule and can revert it to inherit or a gate', async () => {
    await render({ opens_in: 'badge:33', opens_rule: { opens_in: 'badge:33', gate_key: null, note: 'user' } })
    expect(buttons()[0].textContent).toContain('Opens in: Cress')
    await click(buttons()[0])
    await click(buttons().find(b => b.textContent.startsWith('Inherit')))
    await click(buttons().find(b => b.textContent === 'Save'))
    expect(saveAvailabilityRule).toHaveBeenLastCalledWith(1001, 'location', '9', {})
    await click(buttons()[0])
    await click(buttons().find(b => b.textContent.startsWith('Surf')))
    await click(buttons().find(b => b.textContent === 'Save'))
    expect(saveAvailabilityRule).toHaveBeenLastCalledWith(1001, 'location', '9', { opensIn: null, gateKey: 'surf', note: 'user' })
  })

  it('names an unknown gate resolution', async () => {
    await render({ opens_in: null, opens_gate: 'surf', opens_unknown: true, opens_rule: { opens_in: null, gate_key: 'surf', note: null } })
    expect(buttons()[0].textContent).toContain('Opens in: Surf · not set')
  })
})
