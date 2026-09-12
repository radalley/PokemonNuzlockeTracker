import React, { act } from 'react'
import { createRoot } from 'react-dom/client'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import AttemptHeader from './AttemptHeader'
import { getAttempts, getParty, removeFromParty } from '../utils/dataLayer'

vi.mock('react-router-dom', () => ({
  useNavigate: () => vi.fn(),
  useLocation: () => ({ pathname: '/attempt/1/1' }),
}))

vi.mock('../utils/dataLayer', () => ({
  getAttempts: vi.fn(),
  getParty: vi.fn(),
  createAttempt: vi.fn(),
  removeFromParty: vi.fn(),
  endAttempt: vi.fn(),
}))

vi.mock('./Sprite', () => ({
  default: () => <span />,
}))

vi.mock('./HeaderAuthMenu', () => ({
  default: () => null,
}))

// The party slot's only "this will drop the Pokemon" warning is a hover
// tint, so touch devices need a second tap instead. useHoverCapable reads
// that capability from matchMedia; jsdom has no implementation, so supply
// one whose answer we control.
function stubPointer({ hover }) {
  window.matchMedia = query => ({
    matches: query.includes('hover: hover') ? hover : !hover,
    media: query,
    addEventListener: () => {},
    removeEventListener: () => {},
    addListener: () => {},
    removeListener: () => {},
  })
}

const member = {
  pokemon_id: 42,
  species_id: 501,
  party_slot: 1,
  shiny: false,
}

describe('AttemptHeader party slots', () => {
  let container
  let root

  beforeEach(() => {
    getAttempts.mockResolvedValue([{ attempt_number: 1, outcome: null }])
    getParty.mockResolvedValue([member])
    removeFromParty.mockResolvedValue({})
    container = document.createElement('div')
    document.body.appendChild(container)
    root = createRoot(container)
  })

  afterEach(async () => {
    await act(async () => { root.unmount() })
    container.remove()
    vi.clearAllMocks()
    delete window.matchMedia
  })

  const render = async () => {
    await act(async () => {
      root.render(
        <AttemptHeader
          runId={1}
          attemptId={1}
          runDetails={{ name: 'Blaze Black', game_name: 'Blaze Black' }}
        />
      )
    })
  }

  // The filled slot is the one carrying the drop affordance.
  const filledSlot = () =>
    [...container.querySelectorAll('.attempt-header__party-slot')]
      .find(el => el.getAttribute('title'))

  const click = async (el) => {
    await act(async () => {
      el.dispatchEvent(new MouseEvent('click', { bubbles: true }))
    })
  }

  it('drops the Pokemon on a single click when the pointer can hover', async () => {
    stubPointer({ hover: true })
    await render()

    await click(filledSlot())

    expect(removeFromParty).toHaveBeenCalledWith(1, 1, 42)
  })

  it('requires a second tap to drop the Pokemon on a touch device', async () => {
    stubPointer({ hover: false })
    await render()

    await click(filledSlot())
    expect(removeFromParty).not.toHaveBeenCalled()
    expect(filledSlot().textContent).toContain('Drop?')

    await click(filledSlot())
    expect(removeFromParty).toHaveBeenCalledWith(1, 1, 42)
  })
})
