import { beforeEach, describe, expect, it, vi } from 'vitest'
import { apiFetch } from './api'
import { getAttemptPageData } from './dataLayer'

vi.mock('./api', () => ({
  apiFetch: vi.fn(),
}))

vi.mock('./guestStorage', () => ({
  getRunDetails: vi.fn(() => ({ game_id: 1001, version_group_id: 1001, starter: 'Fire' })),
  getEncounters: vi.fn(() => ({})),
  getTrainersDefeated: vi.fn(() => []),
  getBonusLocations: vi.fn(() => []),
  getAttemptOutcome: vi.fn(() => null),
}))

describe('getAttemptPageData for a guest run', () => {
  beforeEach(() => {
    apiFetch.mockReset()
  })

  it('passes the encounter tables and the method registry through', async () => {
    const tables = { 240: [{ species_id: 551, name: 'SANDILE', method: 'sand', slot_kind: 'slot', rate: 60 }] }
    const methods = [{ key: 'sand', label: 'Desert sand', group: 'ground', is_rare: false, sort_order: 70 }]
    apiFetch.mockResolvedValue({
      ok: true,
      json: async () => ({ script: [], pools: { 240: [] }, pool_tables: tables, encounter_methods: methods }),
    })

    const data = await getAttemptPageData('local_1', 1)

    expect(apiFetch.mock.calls[0][0]).toContain('/api/guest-script?')
    expect(data.pool_tables).toEqual(tables)
    expect(data.encounter_methods).toEqual(methods)
  })

  it('answers with empty tables when an older backend sends none', async () => {
    apiFetch.mockResolvedValue({ ok: true, json: async () => ({ script: [], pools: {} }) })
    const data = await getAttemptPageData('local_1', 1)
    expect(data.pool_tables).toEqual({})
    expect(data.encounter_methods).toEqual([])
  })
})
