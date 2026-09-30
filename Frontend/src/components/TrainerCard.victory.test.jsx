import React, { act } from 'react'
import { createRoot } from 'react-dom/client'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import TrainerCard from './TrainerCard'
import { apiFetch } from '../utils/api'
import { getParty, markTrainerVictory } from '../utils/dataLayer'

vi.mock('../contexts/AuthContext', () => ({
  useAuth: () => ({ user: null }),
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

// The battle modal is rendered for real here: these tests are about what
// happens to it after a win.

describe('TrainerCard: the battle modal after a victory', () => {
  let container
  let root

  beforeEach(() => {
    container = document.createElement('div')
    document.body.appendChild(container)
    root = createRoot(container)
    apiFetch.mockReset()
    apiFetch.mockResolvedValue({ ok: true, json: async () => [] })
    getParty.mockReset()
    getParty.mockResolvedValue([])
    markTrainerVictory.mockReset()
  })

  afterEach(async () => {
    vi.useRealTimers()
    await act(async () => root.unmount())
    container.remove()
  })

  const openBattle = async () => {
    await act(async () => {
      root.render(
        <TrainerCard trainerName="BIANCA" trainerId={7} runId={1} attemptId={1} gameId={1001} enableBattle />
      )
    })
    const battleBtn = [...container.querySelectorAll('button')].find(b => b.textContent.trim() === 'Battle')
    await act(async () => {
      battleBtn.dispatchEvent(new MouseEvent('click', { bubbles: true }))
    })
    expect(container.querySelector('.battle-compare')).toBeTruthy()
  }

  const markVictory = async () => {
    const btn = [...container.querySelectorAll('.battle-compare button')].find(b => b.textContent.trim() === 'Mark Victory')
    await act(async () => {
      btn.dispatchEvent(new MouseEvent('click', { bubbles: true }))
    })
  }

  it('closes at once on a plain win and marks the card defeated', async () => {
    markTrainerVictory.mockResolvedValue({ success: true })
    await openBattle()
    await markVictory()
    expect(container.querySelector('.battle-compare')).toBeNull()
    expect(container.textContent).toContain('Defeated')
  })

  it('lingers briefly to show an awarded badge, then closes on its own', async () => {
    vi.useFakeTimers()
    markTrainerVictory.mockResolvedValue({
      success: true,
      badge_awarded: { badge_id: 33, badge_name: 'Trio Badge' },
    })
    await openBattle()
    await markVictory()
    // still open, showing the badge banner
    expect(container.querySelector('.battle-compare')).toBeTruthy()
    expect(container.textContent).toContain('Trio Badge')
    act(() => { vi.advanceTimersByTime(1600) })
    expect(container.querySelector('.battle-compare')).toBeNull()
  })

  it('stays open when a gym win has no badge mapping, so the warning is read', async () => {
    vi.useFakeTimers()
    markTrainerVictory.mockResolvedValue({ success: true, is_gym_leader: true })
    await openBattle()
    await markVictory()
    act(() => { vi.advanceTimersByTime(5000) })
    expect(container.querySelector('.battle-compare')).toBeTruthy()
    expect(container.textContent).toContain('no badge assignment')
  })

  it('a manual Back during the badge linger cancels the pending auto-close cleanly', async () => {
    vi.useFakeTimers()
    markTrainerVictory.mockResolvedValue({
      success: true,
      badge_awarded: { badge_id: 33, badge_name: 'Trio Badge' },
    })
    await openBattle()
    await markVictory()
    const back = [...container.querySelectorAll('.battle-compare button')].find(b => b.textContent.trim() === 'Back')
    await act(async () => {
      back.dispatchEvent(new MouseEvent('click', { bubbles: true }))
    })
    expect(container.querySelector('.battle-compare')).toBeNull()
    // the timer must not throw or reopen anything later
    act(() => { vi.advanceTimersByTime(2000) })
    expect(container.querySelector('.battle-compare')).toBeNull()
  })
})
