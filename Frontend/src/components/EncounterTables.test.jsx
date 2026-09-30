import React, { act } from 'react'
import { createRoot } from 'react-dom/client'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import EncounterTables from './EncounterTables'
import { buildEncounterView, slotKey } from '../utils/encounterTables'

vi.mock('./Sprite', () => ({
  default: ({ speciesId }) => <span data-species={speciesId} />,
}))

const METHODS = [
  { key: 'grass', label: 'Tall grass', group: 'grass', is_rare: false, sort_order: 10, description: "Doc: 'Grass, Normal'." },
  { key: 'grass-spots', label: 'Shaking grass', group: 'grass', is_rare: true, sort_order: 30, description: 'Rustling patches.' },
  { key: 'sand', label: 'Desert sand', group: 'ground', is_rare: false, sort_order: 70, description: 'Desert.' },
  { key: 'surf-spots', label: 'Rippling water', group: 'water', is_rare: true, sort_order: 130, description: 'Ripples.' },
  { key: 'static', label: 'Static encounter', group: 'special', is_rare: false, sort_order: 160, description: 'Scripted.' },
]

const row = (over) => ({
  species_id: 1, name: 'X', method: 'sand', area: null, area_sort: 0, condition: null,
  slot_kind: 'slot', tag: null, rate: 20, min_level: null, max_level: null, note: null, ...over,
})

const RELIC = [
  row({ species_id: 551, name: 'Sandile', area: '1F', area_sort: 1, rate: 60 }),
  row({ species_id: 27, name: 'Sandshrew', area: '1F', area_sort: 1, rate: 40 }),
  row({ species_id: 552, name: 'Krokorok', area: 'B2F, B3F, B4F, B5F', area_sort: 2, rate: 100 }),
  row({ species_id: 377, name: 'Regirock', area: 'B2F, B3F, B4F, B5F', area_sort: 2, rate: 1, slot_kind: 'overlay', tag: 'legendary', min_level: 50, max_level: 50, note: 'deep down' }),
  row({ species_id: 637, name: 'Volcarona', method: 'static', area: 'Volcarona Room', area_sort: 3, rate: null, slot_kind: 'static', tag: 'special', min_level: 75, max_level: 75 }),
]

const SEASONAL = [
  row({ species_id: 420, name: 'Cherubi', method: 'grass', condition: 'season:spring,summer,autumn', rate: 100 }),
  row({ species_id: 459, name: 'Snover', method: 'grass', condition: 'season:winter', rate: 100 }),
  row({ species_id: 531, name: 'Audino', method: 'grass-spots', rate: 100 }),
  row({ species_id: 382, name: 'Kyogre', method: 'surf-spots', condition: 'season:summer', rate: 1, slot_kind: 'overlay', tag: 'legendary', min_level: 70, max_level: 70 }),
  row({ species_id: 226, name: 'Mantine', method: 'surf-spots', rate: 100 }),
]

describe('EncounterTables', () => {
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

  const render = async (props) => {
    await act(async () => { root.render(<EncounterTables {...props} />) })
  }
  const click = async (el) => act(async () => { el.dispatchEvent(new MouseEvent('click', { bubbles: true })) })
  const rows = () => [...container.querySelectorAll('.encounter-tables__row')]
  const names = () => rows().map(r => r.querySelector('.encounter-tables__name').textContent)
  const tabs = () => [...container.querySelectorAll('[role="tab"]')]
  const tabLabels = () => tabs().map(t => t.textContent.replace(/\d+$/, ''))
  const activeTab = () => tabs().find(t => t.getAttribute('aria-selected') === 'true')
  const areaPills = () => [...container.querySelectorAll('.encounter-tables__area')]
  const button = (text) => [...container.querySelectorAll('button')].find(b => b.textContent.trim() === text)
  const tabNamed = (label) => tabs().find(t => t.textContent.startsWith(label))

  it('shows one area and one method at a time, and a tap selects a row', async () => {
    const onSelect = vi.fn()
    const onAreaChange = vi.fn()
    const view = buildEncounterView(RELIC, METHODS)
    await render({ view, locationName: 'Relic Castle', dupedFamilyIds: new Set([27]), onSelect, onAreaChange, season: 'spring' })

    // area pills in doc order, first active by default
    expect(areaPills().map(t => t.textContent)).toEqual(['1F', 'B2F, B3F, B4F, B5F', 'Volcarona Room'])
    expect(areaPills()[0].getAttribute('aria-pressed')).toBe('true')
    // one method here: one tab, with its row count
    expect(tabLabels()).toEqual(['Desert sand'])
    expect(activeTab().textContent).toContain('2')
    // the method's description is not shown: the tab already names it
    expect(container.querySelector('[role="tabpanel"]').textContent).not.toContain('Desert.')
    expect(names()).toEqual(['Sandile', 'Sandshrew'])
    expect(rows()[0].textContent).toContain('60%')
    // the dupe is dimmed and tagged, still selectable
    expect(rows()[1].style.opacity).toBe('0.35')
    expect(rows()[1].textContent).toContain('Dupe')
    expect(rows()[1].disabled).toBe(false)

    await click(rows()[0])
    expect(onSelect).toHaveBeenCalledTimes(1)
    expect(onSelect.mock.calls[0][0]).toMatchObject({ species_id: 551, name: 'Sandile', method: 'sand', area: '1F', rate: 60 })

    // the owner marks the selection; a selected dupe is shown at full strength
    await render({ view, locationName: 'Relic Castle', dupedFamilyIds: new Set([27]), onSelect, onAreaChange, season: 'spring', selectedKey: slotKey(RELIC[1]) })
    expect(rows()[1].getAttribute('aria-pressed')).toBe('true')
    expect(rows()[1].className).toContain('encounter-tables__row--selected')
    expect(rows()[1].style.opacity).toBe('1')
    expect(rows()[0].getAttribute('aria-pressed')).toBe('false')

    // another area is a request to the owner, who re-renders with it
    await click(areaPills()[1])
    expect(onAreaChange).toHaveBeenCalledWith('B2F, B3F, B4F, B5F')
    await render({ view, locationName: 'Relic Castle', onSelect, onAreaChange, area: 'B2F, B3F, B4F, B5F', season: 'spring' })
    expect(names()).toEqual(['Krokorok', 'Regirock'])
    const overlay = rows()[1]
    expect(overlay.className).toContain('encounter-tables__row--overlay')
    expect(overlay.textContent).toContain('Legendary')
    expect(overlay.textContent).toContain('1%')
    expect(overlay.textContent).toContain('Lv 50')
    expect(overlay.getAttribute('title')).toBe('deep down')
  })

  it('switches tables with the method tabs, by click and by arrow key', async () => {
    const view = buildEncounterView(SEASONAL, METHODS)
    await render({ view, locationName: 'Route 6', season: 'winter', onSelect: () => {} })

    // all-seasons tables first, then the season's own
    expect(tabLabels()).toEqual(['Shaking grass', 'Rippling water', 'Tall grass'])
    expect(activeTab().textContent).toContain('Shaking grass')
    expect(names()).toEqual(['Audino'])
    // a rare spot carries no label of its own: the tab's sparkle says it
    expect(container.querySelector('[role="tabpanel"]').textContent).not.toContain('Rare spot')

    await click(tabNamed('Tall grass'))
    expect(names()).toEqual(['Snover'])
    expect(container.querySelector('[role="tabpanel"]').textContent).toContain('Winter')

    await act(async () => {
      activeTab().dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowRight', bubbles: true }))
    })
    expect(activeTab().textContent).toContain('Shaking grass')
    expect(document.activeElement).toBe(activeTab())
  })

  it('opens on the tab holding the selected species', async () => {
    const view = buildEncounterView(SEASONAL, METHODS)
    const mantine = SEASONAL[4]
    await render({ view, locationName: 'Undella Bay', season: 'winter', onSelect: () => {}, selectedKey: slotKey(mantine) })
    expect(activeTab().textContent).toContain('Rippling water')
    expect(rows().find(r => r.textContent.includes('Mantine')).getAttribute('aria-pressed')).toBe('true')
    // a tab the player picks still wins over the selection
    await click(tabNamed('Tall grass'))
    expect(activeTab().textContent).toContain('Tall grass')
  })

  it('offers a season switch on seasonal locations and filters tables and overlays by it', async () => {
    const onSeasonChange = vi.fn()
    const view = buildEncounterView(SEASONAL, METHODS)
    await render({ view, locationName: 'Route 6', season: 'winter', onSeasonChange, onSelect: () => {} })

    const seasons = [...container.querySelectorAll('.encounter-tables__season')]
    expect(seasons.map(s => s.textContent)).toEqual(['Spring', 'Summer', 'Autumn', 'Winter'])
    expect(seasons[3].getAttribute('aria-pressed')).toBe('true')
    await click(tabNamed('Rippling water'))
    expect(names()).toEqual(['Mantine'])

    await click(seasons[1])
    expect(onSeasonChange).toHaveBeenCalledWith('summer')
    await render({ view, locationName: 'Route 6', season: 'summer', onSeasonChange, onSelect: () => {} })
    // the chosen tab survives the season change; Kyogre joins it in summer
    expect(activeTab().textContent).toContain('Rippling water')
    expect(names()).toEqual(['Mantine', 'Kyogre'])
    await click(tabNamed('Tall grass'))
    expect(names()).toEqual(['Cherubi'])
  })

  it('lists legendaries and statics in the rare strip; a static selects, an overlay jumps to its table', async () => {
    const onSelect = vi.fn()
    const onAreaChange = vi.fn()
    const view = buildEncounterView(RELIC, METHODS)
    await render({ view, locationName: 'Relic Castle', onSelect, onAreaChange, season: 'spring' })

    const chips = [...container.querySelectorAll('.encounter-tables__chip')]
    expect(chips.map(c => c.textContent)).toEqual([
      'Regirock1%B2F, B3F, B4F, B5FLv 50',
      'VolcaronaStaticVolcarona RoomLv 75',
    ])
    await click(chips[1])
    expect(onSelect).toHaveBeenCalledWith(expect.objectContaining({ species_id: 637, slot_kind: 'static' }))
    await click(chips[0])
    expect(onAreaChange).toHaveBeenCalledWith('B2F, B3F, B4F, B5F')
    expect(onSelect).toHaveBeenCalledTimes(1)

    // a selected static chip says so
    await render({ view, locationName: 'Relic Castle', onSelect, onAreaChange, season: 'spring', selectedKey: slotKey(RELIC[4]) })
    const volcarona = [...container.querySelectorAll('.encounter-tables__chip')][1]
    expect(volcarona.getAttribute('aria-pressed')).toBe('true')
  })

  it('peeks at a legendary season from the strip without changing the chosen season', async () => {
    const onSeasonChange = vi.fn()
    const view = buildEncounterView(SEASONAL, METHODS)
    await render({ view, locationName: 'Route 6', season: 'winter', onSeasonChange, onSelect: () => {} })
    expect(names()).not.toContain('Kyogre')

    const kyogre = [...container.querySelectorAll('.encounter-tables__chip')].find(c => c.textContent.includes('Kyogre'))
    await click(kyogre)
    // the table is shown in its season, on its tab, but the run's season is untouched
    expect(onSeasonChange).not.toHaveBeenCalled()
    expect(activeTab().textContent).toContain('Rippling water')
    expect(names()).toContain('Kyogre')
    expect(button('Summer').getAttribute('aria-pressed')).toBe('true')
    // a season the player picks ends the peek and is a real change
    await click(button('Autumn'))
    expect(onSeasonChange).toHaveBeenCalledWith('autumn')
    await render({ view, locationName: 'Route 6', season: 'winter', onSeasonChange, onSelect: () => {} })
    expect(button('Winter').getAttribute('aria-pressed')).toBe('true')
  })

  it('tags an overlay with its season when it is narrower than its table', async () => {
    const view = buildEncounterView(SEASONAL, METHODS)
    await render({ view, locationName: 'Undella Bay', season: 'summer', onSelect: () => {} })
    await click(tabNamed('Rippling water'))
    const kyogre = rows().find(r => r.textContent.includes('Kyogre'))
    expect(kyogre.textContent).toContain('Summer')
    // an overlay on a table of the same season needs no tag of its own
    const winterOnly = buildEncounterView([
      row({ species_id: 459, name: 'Snover', method: 'grass', condition: 'season:winter', rate: 100 }),
      row({ species_id: 144, name: 'Articuno', method: 'grass', condition: 'season:winter', rate: 1, slot_kind: 'overlay', tag: 'legendary' }),
    ], METHODS)
    await render({ view: winterOnly, locationName: 'Dragonspiral Tower', season: 'winter', onSelect: () => {} })
    const articuno = rows().find(r => r.textContent.includes('Articuno'))
    expect(articuno.textContent).not.toContain('Winter')
  })

  it('does not report an empty season on a location whose only encounter is a static', async () => {
    const view = buildEncounterView([
      row({ species_id: 494, name: 'Victini', method: 'static', area: 'Liberty Tower Basement', area_sort: 1, rate: null, slot_kind: 'static', tag: 'special', min_level: 15, max_level: 15 }),
    ], METHODS)
    await render({ view, locationName: 'Liberty Garden', season: 'spring', onSelect: () => {} })
    expect(container.textContent).toContain('Victini')
    expect(container.textContent).not.toContain('Nothing documented here in')
    expect(container.textContent).toContain('static encounter above')
    expect(tabs()).toEqual([])
  })

  it('renders a species listed twice at the same rate without key collisions', async () => {
    const errors = vi.spyOn(console, 'error').mockImplementation(() => {})
    try {
      const view = buildEncounterView([
        row({ species_id: 16, name: 'Pidgey', method: 'grass', rate: 20, min_level: 2, max_level: 3 }),
        row({ species_id: 16, name: 'Pidgey', method: 'grass', rate: 20, min_level: 4, max_level: 5 }),
        row({ species_id: 19, name: 'Rattata', method: 'grass', rate: 60 }),
      ], METHODS)
      await render({ view, locationName: 'Route 1', season: 'spring', onSelect: () => {} })
      expect(names()).toEqual(['Pidgey', 'Pidgey', 'Rattata'])
      expect(errors.mock.calls.filter(call => String(call[0]).includes('same key'))).toEqual([])
      // the two Pidgey slots are separate selections
      expect(slotKey(view.tables[0].rows[0])).not.toBe(slotKey(view.tables[0].rows[1]))
    } finally {
      errors.mockRestore()
    }
  })

  it('renders one legendary twice in the rare strip without key collisions', async () => {
    const errors = vi.spyOn(console, 'error').mockImplementation(() => {})
    try {
      const view = buildEncounterView([
        row({ species_id: 16, name: 'Pidgey', method: 'grass', rate: 99 }),
        row({ species_id: 144, name: 'Articuno', method: 'grass', rate: 1, slot_kind: 'overlay', tag: 'legendary', min_level: 50, max_level: 50 }),
        row({ species_id: 144, name: 'Articuno', method: 'grass', rate: 1, slot_kind: 'overlay', tag: 'legendary', min_level: 60, max_level: 60 }),
      ], METHODS)
      await render({ view, locationName: 'Route 1', season: 'spring', onSelect: () => {} })
      expect([...container.querySelectorAll('.encounter-tables__chip')]).toHaveLength(2)
      expect(errors.mock.calls.filter(call => String(call[0]).includes('same key'))).toEqual([])
    } finally {
      errors.mockRestore()
    }
  })

  it('says when the chosen season has no table, and keeps the season switch', async () => {
    const view = buildEncounterView([row({ species_id: 459, name: 'Snover', method: 'grass', condition: 'season:winter', rate: 100 })], METHODS)
    await render({ view, locationName: 'Route 9', season: 'spring', onSelect: () => {} })
    expect(container.querySelector('.encounter-tables__empty').textContent).toBe('Nothing documented here in Spring.')
    expect(button('Winter')).toBeTruthy()
    expect(tabs()).toEqual([])
  })

  it('ends a season peek when the area changes or the run season changes', async () => {
    const onAreaChange = vi.fn()
    const rows2 = [
      ...SEASONAL,
      row({ species_id: 50, name: 'Diglett', method: 'grass', area: 'Cave', area_sort: 1, rate: 100 }),
      row({ species_id: 459, name: 'Snover', method: 'grass', area: 'Cave', area_sort: 1, condition: 'season:winter', rate: 100 }),
    ]
    const view = buildEncounterView(rows2, METHODS)
    await render({ view, locationName: 'Route 6', season: 'winter', onSelect: () => {}, onAreaChange })
    const kyogre = () => [...container.querySelectorAll('.encounter-tables__chip')].find(c => c.textContent.includes('Kyogre'))

    // peek, then pick another area: back to the run's winter
    await click(kyogre())
    expect(button('Summer').getAttribute('aria-pressed')).toBe('true')
    await click(areaPills().find(p => p.textContent === 'Cave'))
    expect(onAreaChange).toHaveBeenLastCalledWith('Cave')
    await render({ view, locationName: 'Route 6', season: 'winter', area: 'Cave', onSelect: () => {}, onAreaChange })
    expect(button('Winter').getAttribute('aria-pressed')).toBe('true')

    // peek again, then the run season changes elsewhere: that season shows
    await render({ view, locationName: 'Route 6', season: 'winter', area: '', onSelect: () => {}, onAreaChange })
    await click(kyogre())
    expect(button('Summer').getAttribute('aria-pressed')).toBe('true')
    await render({ view, locationName: 'Route 6', season: 'autumn', area: '', onSelect: () => {}, onAreaChange })
    expect(button('Autumn').getAttribute('aria-pressed')).toBe('true')
  })

  it('disables every row and chip when the attempt has ended', async () => {
    const onSelect = vi.fn()
    await render({ view: buildEncounterView(RELIC, METHODS), disabled: true, onSelect, season: 'spring' })
    expect(rows().every(r => r.disabled)).toBe(true)
    expect([...container.querySelectorAll('.encounter-tables__chip')].every(c => c.disabled)).toBe(true)
    await click(rows()[0])
    expect(onSelect).not.toHaveBeenCalled()
  })

  it('falls back to the plain pool without odds, or says there is nothing documented', async () => {
    const onSelect = vi.fn()
    await render({ view: buildEncounterView([], METHODS), fallbackPool: [{ species_id: 16, name: 'PIDGEY' }, { species_id: 19, name: 'RATTATA' }], onSelect, season: 'spring' })
    expect(tabs()).toEqual([])
    expect(container.textContent).toContain('Encounters')
    expect(names()).toEqual(['PIDGEY', 'RATTATA'])
    expect(rows()[0].textContent).toContain('—')
    await click(rows()[1])
    expect(onSelect).toHaveBeenCalledWith(expect.objectContaining({ species_id: 19, name: 'RATTATA', method: null, source: 'pool' }))

    await render({ view: buildEncounterView([], METHODS), fallbackPool: [], locationName: 'Nimbasa City', season: 'spring' })
    expect(container.textContent).toContain('No wild encounters documented for Nimbasa City')
    expect(button('Spring')).toBeUndefined()
  })
})
