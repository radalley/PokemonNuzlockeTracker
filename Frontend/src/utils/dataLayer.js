import { apiFetch } from './api'
import * as guest from './guestStorage'

export function isLocalRun(runId) {
  return String(runId).startsWith('local_')
}

export async function getRuns(isAuthenticated) {
  if (!isAuthenticated) return guest.getRuns()
  const res = await apiFetch('/api/runs')
  return res.json()
}

export async function createRun(isAuthenticated, gameId, runName, gameData = {}) {
  if (!isAuthenticated) {
    return guest.createRun({ game_id: gameId, ...gameData }, runName)
  }
  const res = await apiFetch('/api/runs', {
    method: 'POST',
    body: JSON.stringify({ game_id: gameId, run_name: runName }),
  })
  return res.json()
}

export async function deleteRun(runId) {
  if (isLocalRun(runId)) {
    guest.deleteRun(runId)
    return { success: true }
  }
  const res = await apiFetch('/api/delete-run', {
    method: 'POST',
    body: JSON.stringify({ run_id: runId }),
  })
  return res.json()
}

export async function getAttempts(runId) {
  if (isLocalRun(runId)) return guest.getAttempts(runId)
  const res = await apiFetch(`/api/runs/${runId}/attempts`)
  return res.json()
}

export async function createAttempt(runId) {
  if (isLocalRun(runId)) {
    const attempt_number = guest.createAttempt(runId)
    return { attempt_number }
  }
  const res = await apiFetch(`/api/runs/${runId}/attempts`, { method: 'POST' })
  return res.json()
}

export async function updateStarter(runId, attemptNumber, starter) {
  if (isLocalRun(runId)) {
    guest.updateStarter(runId, attemptNumber, starter)
    return { success: true }
  }
  const res = await apiFetch('/api/update-starter', {
    method: 'POST',
    body: JSON.stringify({ run_id: runId, attempt_id: attemptNumber, starter }),
  })
  return res.json()
}

export async function getRunDetails(runId, attemptNumber) {
  if (isLocalRun(runId)) return guest.getRunDetails(runId, attemptNumber)
  const res = await apiFetch(`/api/runs/${runId}/${attemptNumber}`)
  return res.json()
}

export async function getAttemptPageData(runId, attemptNumber) {
  if (isLocalRun(runId)) {
    const runDetails = guest.getRunDetails(runId, attemptNumber)
    if (!runDetails) return null

    const params = new URLSearchParams({
      game_id: String(runDetails.game_id),
      starter: runDetails.starter || 'Fire',
      version_group_id: String(runDetails.version_group_id || 0),
    })
    const scriptRes = await apiFetch(`/api/guest-script?${params.toString()}`)
    if (!scriptRes.ok) {
      const text = await scriptRes.text().catch(() => '')
      throw new Error(`guest-script failed ${scriptRes.status}: ${text.slice(0, 200)}`)
    }
    const scriptData = await scriptRes.json()

    const encounters = guest.getEncounters(runId, attemptNumber)
    const defeatedSet = new Set(guest.getTrainersDefeated(runId, attemptNumber).map(Number))
    const bonusRows = guest.getBonusLocations(runId, attemptNumber)

    const script = (scriptData.script || []).map(row => ({
      ...row,
      is_defeated: defeatedSet.has(Number(row.event_id)),
      secondary_sort_order: Number(row.secondary_sort_order || 0),
      is_bonus_location: Boolean(row.is_bonus_location),
      encounter_key: `${row.event_id}:${Number(row.secondary_sort_order || 0)}`,
      trainer_count: Number(row.trainer_count || 0),
      available_trainer_count: Number(row.available_trainer_count || 0),
    }))

    const injectedBonus = bonusRows
      .map(b => {
        const canonical = script.find(s => Number(s.event_id) === Number(b.canonical_location_id))
        if (!canonical) return null
        return {
          ...canonical,
          display_name: b.canonical_name || canonical.display_name,
          secondary_sort_order: Number(b.secondary_sort_order || 0),
          is_bonus_location: true,
          encounter_key: `${b.canonical_location_id}:${Number(b.secondary_sort_order || 0)}`,
        }
      })
      .filter(Boolean)

    const fullScript = [...script, ...injectedBonus].sort((a, b) => {
      const primary = Number(a.sort_order || 0) - Number(b.sort_order || 0)
      if (primary !== 0) return primary
      return Number(a.secondary_sort_order || 0) - Number(b.secondary_sort_order || 0)
    })

    return {
      run: runDetails,
      script: fullScript,
      pools: scriptData.pools || {},
      encounters,
    }
  }

  const res = await apiFetch(`/api/attempt-page/${runId}/${attemptNumber}`)
  return res.json()
}

export async function getPokebank(runId, attemptNumber) {
  if (isLocalRun(runId)) return Object.values(guest.getEncounters(runId, attemptNumber))
  const res = await apiFetch(`/api/pokebank/${runId}/${attemptNumber}`)
  return res.json()
}

export async function saveEncounter(runId, attemptNumber, locationId, bonusLocation, speciesId, speciesName, nickname, nature, status, shiny, pokemonId) {
  if (isLocalRun(runId)) {
    const localId = guest.upsertEncounter(
      runId,
      attemptNumber,
      locationId,
      bonusLocation,
      speciesId,
      speciesName,
      nickname,
      nature,
      status,
      shiny,
      pokemonId
    )
    return { success: true, pokemon_id: localId }
  }

  const res = await apiFetch('/api/pokebank/save', {
    method: 'POST',
    body: JSON.stringify({
      run_id: runId,
      attempt_number: attemptNumber,
      location_id: locationId,
      bonus_location: bonusLocation || 0,
      species_id: speciesId,
      nickname: nickname || null,
      nature: nature || null,
      status: status || null,
      shiny: shiny ? 'True' : null,
      pokemon_id: pokemonId || null,
    }),
  })
  return res.json()
}

export async function deleteEncounterById(runId, attemptNumber, pokemonId) {
  if (isLocalRun(runId)) {
    guest.deleteEncounter(runId, attemptNumber, pokemonId)
    return { success: true }
  }
  const res = await apiFetch(`/api/pokebank/${pokemonId}`, { method: 'DELETE' })
  return res.json()
}

export async function getParty(runId, attemptNumber) {
  if (isLocalRun(runId)) return guest.getParty(runId, attemptNumber)
  const res = await apiFetch(`/api/runs/${runId}/attempts/${attemptNumber}/party`)
  return res.json()
}

export async function addToParty(runId, attemptNumber, pokemonId) {
  if (isLocalRun(runId)) {
    const party_slot = guest.addToParty(runId, attemptNumber, pokemonId)
    return party_slot == null ? { error: 'Party full or attempt not found' } : { party_slot }
  }
  const res = await apiFetch(`/api/runs/${runId}/attempts/${attemptNumber}/party`, {
    method: 'POST',
    body: JSON.stringify({ pokemon_id: pokemonId }),
  })
  return res.json()
}

export async function removeFromParty(runId, attemptNumber, pokemonId) {
  if (isLocalRun(runId)) {
    guest.removeFromParty(runId, attemptNumber, pokemonId)
    return { success: true }
  }
  const res = await apiFetch(`/api/runs/${runId}/attempts/${attemptNumber}/party/${pokemonId}`, { method: 'DELETE' })
  return res.json()
}

export async function markTrainerVictory(runId, attemptNumber, trainerId, trainerName, trainerClass, encounterTitle) {
  if (isLocalRun(runId)) {
    let badgeId = null
    try {
      const params = new URLSearchParams({
        trainer_name: trainerName || '',
        trainer_class: trainerClass || '',
        encounter_title: encounterTitle || '',
      })
      const res = await apiFetch(`/api/trainer-badge-info?${params.toString()}`)
      if (res.ok) {
        const payload = await res.json()
        badgeId = payload.badge_id ?? null
      }
    } catch {
      badgeId = null
    }
    return guest.markTrainerVictory(runId, attemptNumber, trainerId, badgeId)
  }

  const res = await apiFetch(`/api/runs/${runId}/attempts/${attemptNumber}/trainer-victory`, {
    method: 'POST',
    body: JSON.stringify({
      trainer_id: trainerId,
      trainer_name: trainerName,
      trainer_class: trainerClass,
      encounter_title: encounterTitle,
    }),
  })
  return res.json()
}

export async function getTrainerList(locationId, runId, attemptNumber, signal) {
  const params = isLocalRun(runId) ? '' : `?run_id=${runId}&attempt_number=${attemptNumber}`
  const res = await apiFetch(`/api/trainer-list/${locationId}${params}`, { signal })
  const trainers = await res.json()

  if (isLocalRun(runId)) {
    const defeated = new Set(guest.getTrainersDefeated(runId, attemptNumber).map(Number))
    return trainers.map(trainer => ({
      ...trainer,
      is_defeated: defeated.has(Number(trainer.trainer_id)),
    }))
  }

  return trainers
}

export async function getSessionStats(runId, attemptNumber, signal) {
  if (isLocalRun(runId)) return guest.getSessionStats(runId, attemptNumber)
  const res = await apiFetch(`/api/runs/${runId}/attempts/${attemptNumber}/session-stats`, { signal })
  return res.json()
}

export async function addBonusLocation(runId, attemptNumber, canonicalLocationId) {
  if (isLocalRun(runId)) return guest.addBonusLocation(runId, attemptNumber, canonicalLocationId)
  const res = await apiFetch(`/api/runs/${runId}/attempts/${attemptNumber}/bonus-locations`, {
    method: 'POST',
    body: JSON.stringify({ canonical_location_id: canonicalLocationId }),
  })
  return res.json()
}

export async function deleteBonusLocation(runId, attemptNumber, canonicalLocationId, secondarySortOrder) {
  if (isLocalRun(runId)) return guest.deleteBonusLocation(runId, attemptNumber, canonicalLocationId, secondarySortOrder)
  const res = await apiFetch(`/api/runs/${runId}/attempts/${attemptNumber}/bonus-locations`, {
    method: 'DELETE',
    body: JSON.stringify({
      canonical_location_id: canonicalLocationId,
      secondary_sort_order: secondarySortOrder,
    }),
  })
  return res.json()
}

export async function renameBonusLocation(runId, attemptNumber, canonicalLocationId, secondarySortOrder, canonicalName) {
  if (isLocalRun(runId)) return guest.renameBonusLocation(runId, attemptNumber, canonicalLocationId, secondarySortOrder, canonicalName)
  const res = await apiFetch(`/api/runs/${runId}/attempts/${attemptNumber}/bonus-locations`, {
    method: 'PATCH',
    body: JSON.stringify({
      canonical_location_id: canonicalLocationId,
      secondary_sort_order: secondarySortOrder,
      canonical_name: canonicalName,
    }),
  })
  return res.json()
}

export async function getBox(runId, attemptNumber) {
  if (isLocalRun(runId)) {
    const rows = Object.values(guest.getEncounters(runId, attemptNumber))
    return rows.filter(row => row.status === 'Captured' || row.status === 'Dead')
  }
  const res = await apiFetch(`/api/box/${runId}/${attemptNumber}`)
  return res.json()
}

export async function updateEncounterStatus(runId, attemptNumber, pokemon) {
  return saveEncounter(
    runId,
    attemptNumber,
    pokemon.location_id,
    pokemon.bonus_location || 0,
    pokemon.species_id,
    pokemon.species_name,
    pokemon.nickname,
    pokemon.nature,
    pokemon.status,
    pokemon.shiny,
    pokemon.pokemon_id
  )
}
