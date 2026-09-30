import React, { act } from 'react'
import { createRoot } from 'react-dom/client'
import { afterEach, beforeEach, describe, expect, it } from 'vitest'
import useRunSeason from './useRunSeason'

// Two locations reading the run's season, the way Attempt passes one
// season to every LocationRow.
function Run({ runId }) {
  const [season, setSeason] = useRunSeason(runId)
  return (
    <div>
      <button type="button" id="route-6" data-season={season} onClick={() => setSeason('winter')}>Route 6</button>
      <button type="button" id="route-7" data-season={season}>Route 7</button>
    </div>
  )
}

describe('useRunSeason', () => {
  let container
  let root

  beforeEach(() => {
    globalThis.IS_REACT_ACT_ENVIRONMENT = true
    localStorage.clear()
    container = document.createElement('div')
    document.body.appendChild(container)
    root = createRoot(container)
  })

  afterEach(async () => {
    await act(async () => root.unmount())
    container.remove()
  })

  const render = async (runId) => act(async () => { root.render(<Run runId={runId} />) })
  const seasonOf = (id) => container.querySelector(`#${id}`).dataset.season

  it('shares one season across locations and remembers it per run', async () => {
    localStorage.setItem('lockley:season:5', 'autumn')
    await render('5')
    expect(seasonOf('route-6')).toBe('autumn')

    await act(async () => { container.querySelector('#route-6').click() })
    expect(seasonOf('route-6')).toBe('winter')
    expect(seasonOf('route-7')).toBe('winter')
    expect(localStorage.getItem('lockley:season:5')).toBe('winter')

    // another run reads its own season, not the one picked for run 5
    localStorage.setItem('lockley:season:9', 'summer')
    await render('9')
    expect(seasonOf('route-7')).toBe('summer')
    await render('5')
    expect(seasonOf('route-7')).toBe('winter')
  })

  it('ignores a stored value that is not a season', async () => {
    localStorage.setItem('lockley:season:5', 'monsoon')
    await render('5')
    expect(['spring', 'summer', 'autumn', 'winter']).toContain(seasonOf('route-6'))
    expect(seasonOf('route-6')).not.toBe('monsoon')
  })
})
