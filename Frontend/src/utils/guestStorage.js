const STORAGE_KEY = 'lockley_guest'

function defaultState() {
  return {
    runs: [],
    attempts: {},
    encounters: {},
    party: {},
    trainers_defeated: {},
    badges: {},
    bonus_locations: {},
    counters: { run: 1, pokemon: 1, bonus: 1 },
  }
}

function attemptKey(runId, attemptNumber) {
  return `${runId}::${Number(attemptNumber)}`
}

export function _getState() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return defaultState()
    const parsed = JSON.parse(raw)
    return { ...defaultState(), ...parsed }
  } catch {
    return defaultState()
  }
}

export function _setState(nextState) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(nextState))
}

export function hasLocalData() {
  const state = _getState()
  return Array.isArray(state.runs) && state.runs.length > 0
}

export function clearLocalData() {
  localStorage.removeItem(STORAGE_KEY)
}

export function getAllLocalData() {
  return _getState()
}

function nextRunId(state) {
  const id = `local_${state.counters.run}`
  state.counters.run += 1
  return id
}

function nextPokemonId(state) {
  const id = 1000000 + state.counters.pokemon
  state.counters.pokemon += 1
  return id
}

function nextBonusSort(state, runId, attemptNumber, canonicalLocationId, baseSecondarySortOrder) {
  const key = attemptKey(runId, attemptNumber)
  const rows = (state.bonus_locations[key] || [])
    .filter(row => Number(row.canonical_location_id) === Number(canonicalLocationId))
  // Floor at the canonical row's own secondary sort: placement can give the
  // base location a non-zero secondary (e.g. Dreamyard), and a bonus slot
  // that reuses it collides on encounter_key. Mirrors create_bonus_location.
  const max = rows.reduce(
    (acc, row) => Math.max(acc, Number(row.secondary_sort_order || 0)),
    Number(baseSecondarySortOrder || 0),
  )
  return max + 1
}

export function getRuns() {
  const state = _getState()
  return (state.runs || []).map(run => {
    const attempts = state.attempts[run.run_id] || []
    const latestAttempt = attempts.length ? Math.max(...attempts.map(a => Number(a.attempt_number))) : null
    const key = latestAttempt ? attemptKey(run.run_id, latestAttempt) : null
    const latestParty = key ? (state.party[key] || []) : []
    const badges = key ? (state.badges[key] || []) : []
    const stats = key ? getSessionStats(run.run_id, latestAttempt) : null

    return {
      ...run,
      latest_attempt: latestAttempt,
      total_attempts: attempts.length,
      latest_party: latestParty,
      latest_attempt_badges: badges,
      latest_attempt_stats: stats,
      victory_item: run.victory_item || '',
    }
  })
}

export function getMenuSummary() {
  const state = _getState()
  const runs = state.runs || []
  if (runs.length === 0) return { has_runs: false, latest_run: null }

  const latestRun = [...runs].sort((left, right) => {
    const leftTime = Date.parse(left.last_opened_at || left.created_at || '') || 0
    const rightTime = Date.parse(right.last_opened_at || right.created_at || '') || 0
    if (rightTime !== leftTime) return rightTime - leftTime
    return String(right.run_id).localeCompare(String(left.run_id), undefined, { numeric: true })
  })[0]
  const attempts = state.attempts[latestRun.run_id] || []
  const fallbackAttempt = attempts.length
    ? Math.max(...attempts.map(attempt => Number(attempt.attempt_number)))
    : null
  const requestedAttempt = Number(latestRun.last_opened_attempt_number)
  const attemptNumber = attempts.some(attempt => Number(attempt.attempt_number) === requestedAttempt)
    ? requestedAttempt
    : fallbackAttempt
  if (!attemptNumber) return { has_runs: true, latest_run: null }

  const key = attemptKey(latestRun.run_id, attemptNumber)
  return {
    has_runs: true,
    latest_run: {
      ...latestRun,
      attempt_number: attemptNumber,
      party: state.party[key] || [],
      badges: state.badges[key] || [],
    },
  }
}

export function markRunOpened(runId, attemptNumber) {
  const state = _getState()
  const run = (state.runs || []).find(candidate => String(candidate.run_id) === String(runId))
  const attemptExists = (state.attempts[runId] || []).some(
    attempt => Number(attempt.attempt_number) === Number(attemptNumber)
  )
  if (!run || !attemptExists) return false
  run.last_opened_at = new Date().toISOString()
  run.last_opened_attempt_number = Number(attemptNumber)
  _setState(state)
  return true
}

export function createRun(gameData, runName) {
  const state = _getState()
  const run_id = nextRunId(state)
  const now = new Date().toISOString()
  const run = {
    run_id,
    run_name: runName,
    game_id: Number(gameData.game_id),
    game_name: gameData.game_name || gameData.name || 'Unknown',
    generation: Number(gameData.generation || 0),
    version_group_id: Number(gameData.version_group_id || 0),
    created_at: now,
    beaten_at: null,
    victory_item: '',
    last_opened_at: now,
    last_opened_attempt_number: 1,
  }

  state.runs.push(run)
  state.attempts[run_id] = [{ attempt_number: 1, starter: 'Fire' }]
  _setState(state)
  return { success: true, run_id, attempt_number: 1 }
}

export function deleteRun(runId) {
  const state = _getState()
  state.runs = (state.runs || []).filter(r => String(r.run_id) !== String(runId))
  const attempts = state.attempts[runId] || []
  attempts.forEach(a => {
    const key = attemptKey(runId, a.attempt_number)
    delete state.encounters[key]
    delete state.party[key]
    delete state.trainers_defeated[key]
    delete state.badges[key]
    delete state.bonus_locations[key]
  })
  delete state.attempts[runId]
  _setState(state)
}

export function getAttempts(runId) {
  const state = _getState()
  return state.attempts[runId] || []
}

export function createAttempt(runId) {
  const state = _getState()
  const existing = state.attempts[runId] || []
  const next = existing.length ? Math.max(...existing.map(a => Number(a.attempt_number))) + 1 : 1
  const attempt = { attempt_number: next, starter: 'Fire' }
  state.attempts[runId] = [...existing, attempt]
  _setState(state)
  return next
}

export function updateStarter(runId, attemptNumber, starter) {
  const state = _getState()
  const attempts = state.attempts[runId] || []
  const row = attempts.find(a => Number(a.attempt_number) === Number(attemptNumber))
  if (row) row.starter = starter
  _setState(state)
}

export function endAttempt(runId, attemptNumber, { trainerId = null, trainerName = null, trainerClass = null, note = null } = {}) {
  const state = _getState()
  const row = (state.attempts[runId] || []).find(a => Number(a.attempt_number) === Number(attemptNumber))
  if (!row) return { success: false, error: 'Attempt not found' }
  if (row.outcome) return { success: false, error: `Attempt already ended (${row.outcome})` }
  row.outcome = 'dead'
  row.ended_at = new Date().toISOString()
  row.ended_by_trainer_id = trainerId != null ? Number(trainerId) : null
  row.ended_by_trainer_name = trainerName || null
  row.ended_by_trainer_class = trainerClass || null
  row.death_note = (note || '').trim().slice(0, 500) || null
  _setState(state)
  return { success: true, outcome: 'dead' }
}

export function reopenAttempt(runId, attemptNumber) {
  const state = _getState()
  const row = (state.attempts[runId] || []).find(a => Number(a.attempt_number) === Number(attemptNumber))
  if (!row || !row.outcome) return { success: false, error: 'Attempt is not ended' }
  delete row.outcome
  delete row.ended_at
  delete row.ended_by_trainer_id
  delete row.ended_by_trainer_name
  delete row.ended_by_trainer_class
  delete row.death_note
  _setState(state)
  return { success: true }
}

export function getAttemptOutcome(runId, attemptNumber) {
  const row = (_getState().attempts[runId] || []).find(a => Number(a.attempt_number) === Number(attemptNumber))
  if (!row) return null
  return {
    attempt_number: Number(row.attempt_number),
    outcome: row.outcome || null,
    ended_at: row.ended_at || null,
    ended_by_trainer_id: row.ended_by_trainer_id ?? null,
    death_note: row.death_note || null,
  }
}

export function getAttemptSummary(runId, attemptNumber) {
  const state = _getState()
  const run = (state.runs || []).find(r => String(r.run_id) === String(runId))
  const attempt = (state.attempts[runId] || []).find(a => Number(a.attempt_number) === Number(attemptNumber))
  if (!run || !attempt) return null
  const encounters = Object.values(getEncounters(runId, attemptNumber) || {})
  const byStatus = status => encounters.filter(e => e.status === status)
  // state.badges[key] is the authoritative attempt-level award record;
  // per-encounter badges_earned only tags party members at victory time.
  const badgeIds = new Set((state.badges[attemptKey(runId, attemptNumber)] || []).map(Number).filter(Number.isFinite))
  const partySlots = new Map(
    (state.party[attemptKey(runId, attemptNumber)] || [])
      .map(member => [String(member.pokemon_id), member.party_slot ?? null]))
  const asMon = e => ({
    pokemon_id: e.pokemon_id ?? null,
    species_id: e.species_id ?? null,
    species_name: e.species_name || null,
    nickname: e.nickname || null,
    level_met: e.level_met ?? null,
    location_name: null,
    party_slot: partySlots.get(String(e.pokemon_id)) ?? null,
  })
  return {
    run: { run_id: run.run_id, name: run.run_name, game_id: run.game_id, game_name: run.game_name, generation: run.generation },
    attempt: {
      attempt_number: Number(attemptNumber),
      starter: attempt.starter || 'Fire',
      started_at: attempt.started_at || null,
      outcome: attempt.outcome || null,
      ended_at: attempt.ended_at || null,
      ended_by_trainer_id: attempt.ended_by_trainer_id ?? null,
      death_note: attempt.death_note || null,
    },
    killer: attempt.ended_by_trainer_id != null || attempt.ended_by_trainer_name
      ? {
          trainer_id: attempt.ended_by_trainer_id ?? null,
          trainer_name: attempt.ended_by_trainer_name || null,
          trainer_class: attempt.ended_by_trainer_class || null,
          trainer_pic: null,
          location_name: null,
        }
      : null,
    badges: [...badgeIds].sort((a, b) => a - b).map(id => ({ badge_id: id, badge_name: null, earned_at: null })),
    deaths: byStatus('Dead').map(asMon),
    survivors: byStatus('Captured').map(asMon),
    counts: {
      captured: byStatus('Captured').length,
      missed: byStatus('Missed').length,
      dead: byStatus('Dead').length,
      trainers_defeated: getTrainersDefeated(runId, attemptNumber).length,
    },
  }
}

export function getRunDetails(runId, attemptNumber) {
  const state = _getState()
  const run = (state.runs || []).find(r => String(r.run_id) === String(runId))
  if (!run) return null
  const attempt = (state.attempts[runId] || []).find(a => Number(a.attempt_number) === Number(attemptNumber))
  if (!attempt) return null
  return {
    ...run,
    name: run.run_name,
    starter: attempt.starter || 'Fire',
    attempt_number: Number(attemptNumber),
  }
}

export function getEncounters(runId, attemptNumber) {
  return _getState().encounters[attemptKey(runId, attemptNumber)] || {}
}

export function upsertEncounter(runId, attemptNumber, locationId, bonusLocation, speciesId, speciesName, nickname, nature, status, shiny, existingPokemonId, gender, ability) {
  const state = _getState()
  const key = attemptKey(runId, attemptNumber)
  const encounterKey = `${locationId}:${Number(bonusLocation || 0)}`
  const pokemon_id = existingPokemonId || nextPokemonId(state)

  state.encounters[key] = state.encounters[key] || {}
  const existingEncounter = state.encounters[key][encounterKey] || {}
  state.encounters[key][encounterKey] = {
    ...existingEncounter,
    pokemon_id,
    species_id: Number(speciesId),
    species_name: speciesName,
    location_id: Number(locationId),
    bonus_location: Number(bonusLocation || 0),
    secondary_sort_order: Number(bonusLocation || 0),
    encounter_key: encounterKey,
    nickname: nickname || null,
    nature: nature || null,
    status: status || null,
    shiny: Boolean(shiny),
    gender: gender || null,
    ability: ability || null,
  }

  // Keep party display data in sync when an encounter evolves or is edited.
  state.party[key] = (state.party[key] || []).map(member => {
    if (String(member.pokemon_id) !== String(pokemon_id)) return member
    return {
      ...member,
      species_id: Number(speciesId),
      species_name: speciesName,
      nickname: nickname || null,
      shiny: Boolean(shiny),
    }
  })

  _setState(state)
  return pokemon_id
}

export function deleteEncounter(runId, attemptNumber, pokemonId) {
  const state = _getState()
  const key = attemptKey(runId, attemptNumber)
  const encounters = state.encounters[key] || {}
  for (const encounterKey of Object.keys(encounters)) {
    if (String(encounters[encounterKey].pokemon_id) === String(pokemonId)) {
      delete encounters[encounterKey]
    }
  }
  state.encounters[key] = encounters
  state.party[key] = (state.party[key] || []).filter(p => String(p.pokemon_id) !== String(pokemonId))
  _setState(state)
}

export function getParty(runId, attemptNumber) {
  const state = _getState()
  const key = attemptKey(runId, attemptNumber)
  const party = state.party[key] || []
  const encounters = Object.values(state.encounters[key] || {})
  const byPokemonId = new Map(encounters.map(e => [String(e.pokemon_id), e]))

  let changed = false
  const syncedParty = party.map(member => {
    const current = byPokemonId.get(String(member.pokemon_id))
    if (!current) return member

    const nextMember = {
      ...member,
      species_id: Number(current.species_id),
      species_name: current.species_name,
      nickname: current.nickname || null,
      shiny: Boolean(current.shiny),
    }

    if (
      Number(member.species_id) !== Number(nextMember.species_id)
      || String(member.species_name || '') !== String(nextMember.species_name || '')
      || String(member.nickname || '') !== String(nextMember.nickname || '')
      || Boolean(member.shiny) !== Boolean(nextMember.shiny)
    ) {
      changed = true
    }

    return nextMember
  })

  if (changed) {
    state.party[key] = syncedParty
    _setState(state)
  }

  return syncedParty
}

export function addToParty(runId, attemptNumber, pokemonId) {
  const state = _getState()
  const key = attemptKey(runId, attemptNumber)
  const party = state.party[key] || []
  if (party.some(p => String(p.pokemon_id) === String(pokemonId))) {
    return party.find(p => String(p.pokemon_id) === String(pokemonId)).party_slot
  }
  if (party.length >= 6) return null

  const encounters = state.encounters[key] || {}
  const found = Object.values(encounters).find(e => String(e.pokemon_id) === String(pokemonId))
  if (!found) return null

  const usedSlots = new Set(party.map(p => Number(p.party_slot)))
  let slot = 1
  while (usedSlots.has(slot) && slot <= 6) slot += 1

  party.push({
    pokemon_id: found.pokemon_id,
    species_id: found.species_id,
    species_name: found.species_name,
    nickname: found.nickname,
    shiny: found.shiny,
    party_slot: slot,
  })
  state.party[key] = party
  _setState(state)
  return slot
}

export function removeFromParty(runId, attemptNumber, pokemonId) {
  const state = _getState()
  const key = attemptKey(runId, attemptNumber)
  state.party[key] = (state.party[key] || []).filter(p => String(p.pokemon_id) !== String(pokemonId))
  _setState(state)
}

export function getTrainersDefeated(runId, attemptNumber) {
  return _getState().trainers_defeated[attemptKey(runId, attemptNumber)] || []
}

export function markTrainerVictory(runId, attemptNumber, trainerId, badgeId = null) {
  const state = _getState()
  const key = attemptKey(runId, attemptNumber)
  const defeated = new Set(state.trainers_defeated[key] || [])
  const isNewVictory = !defeated.has(Number(trainerId))
  defeated.add(Number(trainerId))
  state.trainers_defeated[key] = Array.from(defeated)

  if (isNewVictory && badgeId != null) {
    const badges = new Set((state.badges[key] || []).map(Number))
    badges.add(Number(badgeId))
    state.badges[key] = Array.from(badges)

    const partyPokemonIds = new Set((state.party[key] || []).map(member => String(member.pokemon_id)))
    Object.values(state.encounters[key] || {}).forEach(encounter => {
      if (!partyPokemonIds.has(String(encounter.pokemon_id))) return
      const earned = Array.isArray(encounter.badges_earned)
        ? encounter.badges_earned.map(Number)
        : String(encounter.badges_earned || '').split(',').filter(Boolean).map(Number).filter(Number.isFinite)
      encounter.badges_earned = Array.from(new Set([...earned, Number(badgeId)])).sort((a, b) => a - b)
    })
  }

  _setState(state)
  return {
    success: true,
    badge_awarded: isNewVictory && badgeId ? { badge_id: Number(badgeId) } : null,
  }
}

export function getSessionStats(runId, attemptNumber) {
  const key = attemptKey(runId, attemptNumber)
  const encounters = Object.values(_getState().encounters[key] || {})
  const trainersDefeated = getTrainersDefeated(runId, attemptNumber)
  const badgeIds = (_getState().badges[key] || []).map(Number).sort((a, b) => a - b)

  return {
    run_id: runId,
    attempt_number: Number(attemptNumber),
    badges_earned: badgeIds.length,
    badge_ids: badgeIds,
    trainers_defeated: trainersDefeated.length,
    pokemon_caught: encounters.filter(e => e.status === 'Captured').length,
    pokemon_dead: encounters.filter(e => e.status === 'Dead').length,
    pokemon_missed: encounters.filter(e => e.status === 'Missed').length,
  }
}

export function getBonusLocations(runId, attemptNumber) {
  return _getState().bonus_locations[attemptKey(runId, attemptNumber)] || []
}

/**
 * Aggregate all Captured/Dead pokemon across every local run and attempt
 * into a flat feed-compatible list. Each Pokemon carries only badges earned
 * while it was in the party.
 */
export function getLocalFeedPokemon() {
  const state = _getState()
  const runs = state.runs || []
  const result = []

  for (const run of runs) {
    const attempts = state.attempts[run.run_id] || []
    for (const attempt of attempts) {
      const key = attemptKey(run.run_id, attempt.attempt_number)
      const encounters = Object.values(state.encounters[key] || {})
      for (const enc of encounters) {
        if (enc.status !== 'Captured' && enc.status !== 'Dead') continue
        const badgeIds = Array.isArray(enc.badges_earned)
          ? enc.badges_earned.map(Number).filter(Number.isFinite).sort((a, b) => a - b)
          : []
        result.push({
          species_id: enc.species_id,
          nickname: enc.nickname || null,
          shiny: Boolean(enc.shiny),
          status: enc.status,
          badges_earned: badgeIds.length > 0 ? JSON.stringify(badgeIds) : null,
          fromUser: true,
        })
      }
    }
  }

  return result
}

export function addBonusLocation(runId, attemptNumber, canonicalLocationId, baseSecondarySortOrder = 0) {
  const state = _getState()
  const key = attemptKey(runId, attemptNumber)
  const rows = state.bonus_locations[key] || []
  const secondary_sort_order = nextBonusSort(state, runId, attemptNumber, canonicalLocationId, baseSecondarySortOrder)
  rows.push({
    canonical_location_id: Number(canonicalLocationId),
    secondary_sort_order,
    canonical_name: null,
  })
  state.bonus_locations[key] = rows
  _setState(state)
  return { success: true, secondary_sort_order }
}

export function deleteBonusLocation(runId, attemptNumber, canonicalLocationId, secondarySortOrder) {
  const state = _getState()
  const key = attemptKey(runId, attemptNumber)
  state.bonus_locations[key] = (state.bonus_locations[key] || []).filter(row => {
    return !(Number(row.canonical_location_id) === Number(canonicalLocationId) && Number(row.secondary_sort_order) === Number(secondarySortOrder))
  })
  _setState(state)
  return { success: true }
}

export function renameBonusLocation(runId, attemptNumber, canonicalLocationId, secondarySortOrder, canonicalName) {
  const state = _getState()
  const key = attemptKey(runId, attemptNumber)
  const row = (state.bonus_locations[key] || []).find(item => (
    Number(item.canonical_location_id) === Number(canonicalLocationId) && Number(item.secondary_sort_order) === Number(secondarySortOrder)
  ))
  if (row) row.canonical_name = canonicalName || null
  _setState(state)
  return { success: true }
}
