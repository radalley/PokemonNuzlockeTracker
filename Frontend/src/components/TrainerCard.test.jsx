import React, { act } from 'react'
import { createRoot } from 'react-dom/client'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import TrainerCard from './TrainerCard'
import { apiFetch } from '../utils/api'

const authState = vi.hoisted(() => ({ user: null }))

vi.mock('../contexts/AuthContext', () => ({
  useAuth: () => ({ user: authState.user }),
}))

vi.mock('../utils/api', () => ({
  apiFetch: vi.fn(),
}))

vi.mock('../utils/dataLayer', () => ({
  getParty: vi.fn(),
  markTrainerVictory: vi.fn(),
  endAttempt: vi.fn(),
}))

vi.mock('./Sprite', () => ({
  default: () => <span />,
}))

vi.mock('./BattleCompareModal', () => ({
  default: () => null,
}))

const mv = (name) => ({
  move_id: name,
  move_name: name,
  type: 'Normal',
  damage_class: 'physical',
  power: 40,
  accuracy: 100,
})

const hoothoot = () => ({
  slot: 1,
  species_id: 163,
  species_name: 'Hoothoot',
  lvl: 9,
  type1: 'NORMAL',
  type2: 'FLYING',
  ability1: 'ABILITY_INSOMNIA',
  held_item: null,
  moves: null,
  moves_estimated: true,
  observed_moves: [mv('Tackle')],
  resolved_moves: [mv('Tackle'), mv('Hypnosis'), mv('Growl'), mv('Foresight'), mv('Night Shade')],
})

describe('TrainerCard moves panel', () => {
  let container
  let root

  beforeEach(() => {
    container = document.createElement('div')
    document.body.appendChild(container)
    root = createRoot(container)
    apiFetch.mockReset()
    apiFetch.mockImplementation((url, opts = {}) => {
      if (url.includes('/party')) {
        return Promise.resolve({ ok: true, json: async () => [hoothoot()] })
      }
      if (url === '/api/admin/trainer-moves' && opts.method === 'POST') {
        const body = JSON.parse(opts.body)
        return Promise.resolve({ ok: true, json: async () => ({ move: mv(body.move_name) }) })
      }
      return Promise.resolve({ ok: true, json: async () => [] })
    })
  })

  afterEach(async () => {
    await act(async () => root.unmount())
    container.remove()
    authState.user = null
  })

  const renderExpandedCard = async () => {
    await act(async () => {
      root.render(<TrainerCard trainerName="JIMMY" trainerClass="Youngster" trainerId={7} gameId={1001} />)
    })
    const card = container.querySelector('.trainer-card')
    await act(async () => {
      card.dispatchEvent(new MouseEvent('click', { bubbles: true }))
    })
    return card
  }

  const confirmButtons = () => [...container.querySelectorAll('button[title="Confirm this move was seen"]')]
  const removeButtons = () => [...container.querySelectorAll('button[title="Remove observed move"]')]

  it('caps displayed moves at four: observed first, estimates fill the rest', async () => {
    const card = await renderExpandedCard()
    expect(card.textContent).toContain('Tackle')
    expect(card.textContent).toContain('Foresight')
    // 1 observed + 3 estimates = 4; the fifth learnset move never renders
    expect(card.textContent).not.toContain('Night Shade')
  })

  it('hides all observed-move admin controls from non-admins', async () => {
    await renderExpandedCard()
    expect(confirmButtons()).toHaveLength(0)
    expect(removeButtons()).toHaveLength(0)
  })

  it('lets an admin confirm an estimated move with one click', async () => {
    authState.user = { account_type: 'admin' }
    const card = await renderExpandedCard()

    // one ✕ on the seen row, one ✓ per estimated row
    expect(removeButtons()).toHaveLength(1)
    expect(confirmButtons()).toHaveLength(3)

    const hypnosis = confirmButtons().find(b => b.parentElement.textContent.includes('Hypnosis'))
    expect(hypnosis).toBeTruthy()
    await act(async () => {
      hypnosis.dispatchEvent(new MouseEvent('click', { bubbles: true }))
    })

    const post = apiFetch.mock.calls.find(([url, opts]) => url === '/api/admin/trainer-moves' && opts?.method === 'POST')
    expect(post).toBeTruthy()
    expect(JSON.parse(post[1].body)).toEqual({ trainer_id: 7, slot: 1, move_name: 'Hypnosis' })

    // Hypnosis promoted to seen; estimates recompute to the two remaining slots
    expect(removeButtons()).toHaveLength(2)
    expect(confirmButtons()).toHaveLength(2)
    expect(card.textContent).not.toContain('Night Shade')
  })

  it('confirming an estimate does not toggle the card closed', async () => {
    authState.user = { account_type: 'admin' }
    const card = await renderExpandedCard()
    await act(async () => {
      confirmButtons()[0].dispatchEvent(new MouseEvent('click', { bubbles: true }))
    })
    // still expanded: move rows remain rendered
    expect(card.textContent).toContain('Tackle')
    expect(confirmButtons().length).toBeGreaterThan(0)
  })
})
