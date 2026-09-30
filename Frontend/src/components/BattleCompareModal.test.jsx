import React, { act } from 'react'
import { createRoot } from 'react-dom/client'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import BattleCompareModal from './BattleCompareModal'

// The modal imports damageCalc -> api -> lib/supabase, which throws at
// import when the Supabase env is absent (as on CI).
vi.mock('../utils/api', () => ({
  apiFetch: vi.fn(),
}))

vi.mock('./Sprite', () => ({
  default: () => <span />,
}))

// Move details arrive title-cased from the server (backend _format_label).
const mv = (name, extra = {}) => ({
  move_id: name,
  move_name: name,
  type: 'Normal',
  damage_class: 'Physical',
  power: 40,
  accuracy: 100,
  ...extra,
})

const hoothoot = () => ({
  slot: 1,
  species_id: 163,
  species_name: 'Hoothoot',
  lvl: 9,
  type1: 'NORMAL',
  type2: 'FLYING',
  ability1: 'ABILITY_INSOMNIA',
  bst: 262, hp: 60, atk: 30, def: 30, spa: 36, spd: 56, spe: 50,
  moves_estimated: true,
  observed_moves: [mv('Tackle')],
  resolved_moves: [
    mv('Tackle'),
    mv('Hypnosis', { type: 'Psychic', damage_class: 'Status', power: null, accuracy: 60 }),
    mv('Growl'), mv('Foresight'), mv('Night Shade'),
  ],
})

// A trainer-authored set (not estimated) with one observed move whose
// name never resolved to details — the bare {move_name} the server sends.
const pidove = () => ({
  slot: 2,
  species_id: 519,
  species_name: 'Pidove',
  lvl: 10,
  type1: 'NORMAL',
  type2: 'FLYING',
  bst: 264, hp: 50, atk: 55, def: 50, spa: 36, spd: 30, spe: 43,
  moves_estimated: false,
  observed_moves: [{ move_name: 'Peck' }],
  resolved_moves: [
    mv('Gust', { type: 'Flying', damage_class: 'Special' }),
    mv('Leer', { damage_class: 'Status', power: null }),
  ],
})

const snivy = () => ({
  pokemon_id: 1,
  species_id: 495,
  species_name: 'SNIVY',
  nickname: 'Smug',
  nature: 'Quiet',
  type1: 'GRASS',
  bst: 308, hp: 45, atk: 45, def: 55, spa: 45, spd: 55, spe: 63,
})

describe('BattleCompareModal: opponent moves', () => {
  let container
  let root

  beforeEach(() => {
    globalThis.IS_REACT_ACT_ENVIRONMENT = true
    container = document.createElement('div')
    document.body.appendChild(container)
    root = createRoot(container)
  })

  afterEach(async () => {
    await act(async () => root.unmount())
    container.remove()
  })

  const render = async (props = {}) => {
    await act(async () => {
      root.render(
        <BattleCompareModal
          playerParty={[]}
          opponentParty={[hoothoot(), pidove()]}
          trainerName="JIMMY"
          onClose={() => {}}
          onMarkVictory={() => {}}
          {...props}
        />
      )
    })
  }

  const opponentColumn = () => container.querySelector('.battle-compare__opponent')
  const opponentButtons = () => [...opponentColumn().querySelectorAll('button')]
  const comparison = () => container.querySelector('.battle-compare__comparison')
  const detail = () => comparison().querySelector('.battle-compare__move-detail')
  const partyButton = (column, text) => [...column.querySelectorAll('button')].find(b => b.textContent.includes(text))
  const click = async (el) => act(async () => { el.dispatchEvent(new MouseEvent('click', { bubbles: true })) })
  const listRows = (button) => [...button.querySelectorAll('.battle-compare__moves > div')]
  const names = (rows) => rows.map(r => r.querySelector('.battle-compare__move-name').textContent)
  const isSeen = (row) => Boolean(row.querySelector('.battle-compare__seen'))
  const detailRows = () => [...detail().querySelectorAll('.battle-compare__move-row')]

  it('lists each opponent’s own four moves: seen first, estimates fill the rest', async () => {
    await render()
    const [first, second] = opponentButtons()

    const hoot = listRows(first)
    expect(names(hoot)).toEqual(['Tackle', 'Hypnosis', 'Growl', 'Foresight'])
    expect(first.textContent).not.toContain('Night Shade')
    expect(hoot.map(isSeen)).toEqual([true, false, false, false])
    expect(hoot[0].getAttribute('title')).toBe('Tackle (seen in play)')
    expect(hoot[1].getAttribute('title')).toBe('Hypnosis')
    expect(hoot[0].querySelector('img[alt="Normal"]')).toBeTruthy()
    expect(hoot[1].querySelector('img[alt="Psychic"]')).toBeTruthy()
    // learnset estimates are flagged next to the level
    expect(first.textContent).toContain('est. moves')

    const dove = listRows(second)
    expect(names(dove)).toEqual(['Peck', 'Gust', 'Leer'])
    expect(dove.map(isSeen)).toEqual([true, false, false])
    // an observed move with no details renders without a type icon
    expect(dove[0].querySelector('img')).toBeNull()
    expect(dove[1].querySelector('img[alt="Flying"]')).toBeTruthy()
    // a trainer-authored set is not an estimate
    expect(second.textContent).not.toContain('est. moves')
  })

  it('shows only the sightings, unflagged, once four moves have been seen', async () => {
    await render({ opponentParty: [{ ...hoothoot(), observed_moves: [mv('A'), mv('B'), mv('C'), mv('D')] }] })
    const rows = listRows(opponentButtons()[0])
    expect(names(rows)).toEqual(['A', 'B', 'C', 'D'])
    expect(rows.every(isSeen)).toBe(true)
    expect(opponentColumn().textContent).not.toContain('est. moves')

    await click(opponentButtons()[0])
    expect(detail().textContent).not.toContain('*Estimated')
    expect(detailRows().every(r => r.querySelector('.battle-compare__seen'))).toBe(true)
  })

  it('says so when there is no move data, in the list and in the detail', async () => {
    await render({ opponentParty: [{ ...hoothoot(), observed_moves: [], resolved_moves: [], moves_estimated: false }] })
    expect(opponentColumn().textContent).toContain('No moves')
    expect(opponentColumn().textContent).not.toContain('est. moves')

    await click(opponentButtons()[0])
    expect(detail().textContent).toContain('No moves')
    expect(detailRows()).toHaveLength(0)
  })

  it('shows full move rows for whichever opponent is selected', async () => {
    await render()
    expect(detail()).toBeNull()

    await click(opponentButtons()[1])
    expect(detail().textContent).toContain('Pidove moves')
    expect(detail().textContent).not.toContain('*Estimated')
    let rows = detailRows()
    expect(names(rows)).toEqual(['Peck', 'Gust', 'Leer'])
    // the unresolved sighting: seen tag, no type or category icon, dashes
    expect(isSeen(rows[0])).toBe(true)
    expect(rows[0].querySelector('img')).toBeNull()
    expect(rows[0].textContent).toContain('Pow —')
    expect(rows[0].textContent).toContain('Acc —')
    // a resolved estimate: type icon, category sprite, power and accuracy
    expect(isSeen(rows[1])).toBe(false)
    expect(rows[1].querySelector('img[alt="Flying"]')).toBeTruthy()
    expect(rows[1].querySelector('img[alt="Special"]').getAttribute('src')).toBe('/sprites/types/special.png')
    expect(rows[1].textContent).toContain('Pow 40')
    expect(rows[1].textContent).toContain('Acc 100')

    // switching opponents switches the detail
    await click(opponentButtons()[0])
    expect(detail().textContent).toContain('Hoothoot moves')
    expect(detail().textContent).toContain('*Estimated')
    rows = detailRows()
    expect(names(rows)).toEqual(['Tackle', 'Hypnosis', 'Growl', 'Foresight'])
    expect(rows.map(isSeen)).toEqual([true, false, false, false])
    expect(rows[1].querySelector('img[alt="Status"]').getAttribute('src')).toBe('/sprites/types/status.png')
    expect(rows[1].textContent).toContain('Pow —')
    expect(rows[1].textContent).toContain('Acc 60')

    // toggling the selected opponent off hides the rows again
    await click(opponentButtons()[0])
    expect(detail()).toBeNull()
  })

  it('keeps the opponent’s moves under the head-to-head comparison', async () => {
    await render({ playerParty: [snivy()] })
    await click(partyButton(container.querySelector('.battle-compare__player'), 'Smug'))
    // only the player selected: player mons carry no move data
    expect(detail()).toBeNull()

    await click(opponentButtons()[0])
    expect(comparison().textContent).toContain('vs')
    expect(detail().textContent).toContain('Hoothoot moves')
    expect(detail().textContent).not.toContain('SNIVY moves')
    expect(names(detailRows())).toEqual(['Tackle', 'Hypnosis', 'Growl', 'Foresight'])
    expect(detailRows().map(isSeen)).toEqual([true, false, false, false])
  })
})
