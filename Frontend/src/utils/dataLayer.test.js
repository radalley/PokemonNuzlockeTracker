import { beforeEach, describe, expect, it, vi } from 'vitest'
import { getTrainerList } from './dataLayer'
import { apiFetch } from './api'
import * as guest from './guestStorage'

vi.mock('./api', () => ({
  apiFetch: vi.fn(),
}))

vi.mock('./guestStorage', () => ({
  getTrainersDefeated: vi.fn(),
}))

describe('getTrainerList', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    apiFetch.mockResolvedValue({
      json: () => Promise.resolve([
        { trainer_id: 7, encounter_name: 'TRAINER_A' },
        { trainer_id: 9, encounter_name: 'TRAINER_B' },
      ]),
    })
  })

  it('sends game context instead of run identity for guest runs', async () => {
    guest.getTrainersDefeated.mockReturnValue([7])

    const trainers = await getTrainerList(100, 'local_3', 1, undefined, {
      gameId: 17,
      versionGroupId: 11,
    })

    expect(apiFetch).toHaveBeenCalledWith(
      '/api/trainer-list/100?game_id=17&version_group_id=11',
      { signal: undefined },
    )
    expect(trainers).toEqual([
      { trainer_id: 7, encounter_name: 'TRAINER_A', is_defeated: true },
      { trainer_id: 9, encounter_name: 'TRAINER_B', is_defeated: false },
    ])
  })

  it('omits missing guest context params rather than sending empty values', async () => {
    guest.getTrainersDefeated.mockReturnValue([])

    await getTrainerList(100, 'local_3', 1, undefined, { gameId: 17 })

    expect(apiFetch).toHaveBeenCalledWith(
      '/api/trainer-list/100?game_id=17',
      { signal: undefined },
    )
  })

  it('requests rematches and special battles only when asked', async () => {
    guest.getTrainersDefeated.mockReturnValue([])

    await getTrainerList(100, 'local_3', 1, undefined, {
      gameId: 17,
      versionGroupId: 11,
      includeRematches: true,
      includeEvents: true,
    })

    expect(apiFetch).toHaveBeenCalledWith(
      '/api/trainer-list/100?game_id=17&version_group_id=11&include_rematches=1&include_events=1',
      { signal: undefined },
    )
  })

  it('sends run identity for authenticated runs', async () => {
    const trainers = await getTrainerList(100, 42, 2, undefined, {
      gameId: 17,
      versionGroupId: 11,
    })

    expect(apiFetch).toHaveBeenCalledWith(
      '/api/trainer-list/100?run_id=42&attempt_number=2',
      { signal: undefined },
    )
    expect(guest.getTrainersDefeated).not.toHaveBeenCalled()
    expect(trainers).toEqual([
      { trainer_id: 7, encounter_name: 'TRAINER_A' },
      { trainer_id: 9, encounter_name: 'TRAINER_B' },
    ])
  })
})
