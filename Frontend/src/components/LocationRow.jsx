import { useEffect, useRef, useState } from 'react'
import { apiFetch } from '../utils/api'
import Sprite from './Sprite'
import TrainerCard from './TrainerCard'
import { TypeIconRow } from './TypeIcon'

const NATURES = [
  { name: 'Adamant', up: 'Atk', down: 'SpA' },
  { name: 'Bashful', up: null, down: null },
  { name: 'Bold', up: 'Def', down: 'Atk' },
  { name: 'Brave', up: 'Atk', down: 'Spe' },
  { name: 'Calm', up: 'SpD', down: 'Atk' },
  { name: 'Careful', up: 'SpD', down: 'SpA' },
  { name: 'Docile', up: null, down: null },
  { name: 'Gentle', up: 'SpD', down: 'Def' },
  { name: 'Hardy', up: null, down: null },
  { name: 'Hasty', up: 'Spe', down: 'Def' },
  { name: 'Impish', up: 'Def', down: 'SpA' },
  { name: 'Jolly', up: 'Spe', down: 'SpA' },
  { name: 'Lax', up: 'Def', down: 'SpD' },
  { name: 'Lonely', up: 'Atk', down: 'Def' },
  { name: 'Mild', up: 'SpA', down: 'Def' },
  { name: 'Modest', up: 'SpA', down: 'Atk' },
  { name: 'Naive', up: 'Spe', down: 'SpD' },
  { name: 'Naughty', up: 'Atk', down: 'SpD' },
  { name: 'Quiet', up: 'SpA', down: 'Spe' },
  { name: 'Quirky', up: null, down: null },
  { name: 'Rash', up: 'SpA', down: 'SpD' },
  { name: 'Relaxed', up: 'Def', down: 'Spe' },
  { name: 'Sassy', up: 'SpD', down: 'Spe' },
  { name: 'Serious', up: null, down: null },
  { name: 'Timid', up: 'Spe', down: 'Atk' },
]

const PANEL_STYLE = {
  border: '1px solid #343a47',
  borderRadius: '14px',
  background: '#141821',
}

const SUMMARY_BUTTON_STYLE = {
  minHeight: '34px',
  padding: '6px 10px',
  border: '1px solid #343a47',
  borderRadius: '999px',
  background: 'transparent',
  color: '#e7ebf3',
  cursor: 'pointer',
  font: 'inherit',
}

const ROW_ACTION_GROUP_STYLE = {
  display: 'grid',
  gridTemplateColumns: 'repeat(3, minmax(0, 1fr))',
  gap: '8px',
  width: '312px',
  maxWidth: '100%',
  marginLeft: 'auto',
}

const STAT_ROWS = [
  { key: 'hp', label: 'HP' },
  { key: 'atk', label: 'Atk' },
  { key: 'def', label: 'Def' },
  { key: 'spa', label: 'SpA' },
  { key: 'spd', label: 'SpD' },
  { key: 'spe', label: 'Spe' },
]

function getNatureLabel(nature) {
  const selectedNature = NATURES.find(entry => entry.name === nature)
  if (!selectedNature) return 'Nature'
  return selectedNature.name
}

function getNatureDetails(nature) {
  return NATURES.find(entry => entry.name === nature) || null
}

function getNatureModifierForStat(nature, statLabel) {
  const selectedNature = getNatureDetails(nature)
  if (!selectedNature || !selectedNature.up || !selectedNature.down) return null
  if (selectedNature.up === statLabel) return { text: '+10%', color: '#e55' }
  if (selectedNature.down === statLabel) return { text: '-10%', color: '#66a8ff' }
  return null
}

function getNatureAdjustedStatValue(nature, statLabel, value) {
  if (value == null) return null
  const numericValue = Number(value)
  if (!Number.isFinite(numericValue)) return null

  const modifier = getNatureModifierForStat(nature, statLabel)
  if (!modifier) return numericValue
  if (modifier.text === '+10%') return Math.round(numericValue * 1.1)
  if (modifier.text === '-10%') return Math.round(numericValue * 0.9)
  return numericValue
}

function getStatBarColor(value) {
  if (value == null) return '#3a4050'
  if (value <= 50) return '#e55'
  if (value <= 80) return '#e98b3a'
  if (value <= 100) return '#d4c02a'
  if (value <= 120) return '#8ccf3f'
  return '#5ba85b'
}

function SummaryButton({ active = false, disabled = false, style = {}, children, ...props }) {
  return (
    <button
      type="button"
      disabled={disabled}
      style={{
        ...SUMMARY_BUTTON_STYLE,
        background: active ? '#1d2430' : '#141821',
        borderColor: active ? '#7ec8e3' : '#343a47',
        color: disabled ? '#687286' : '#e7ebf3',
        cursor: disabled ? 'not-allowed' : 'pointer',
        opacity: disabled ? 0.55 : 1,
        ...style,
      }}
      {...props}
    >
      {children}
    </button>
  )
}

function LocationRow({ row, savedEncounter, runId, attemptNumber, gameId = null, pool = [], dupedFamilyIds = new Set(), onEncounterChange, onStatusChange, onPartyChange, onStructureChange, partyPokemonIds = new Set(), onVictoryRecorded = null, viewMode = 'master' }) {
  const searchRef = useRef(null)
  const menuRef = useRef(null)
  const natureRef = useRef(null)
  const locationNameInputRef = useRef(null)
  const skipNextEncounterSaveRef = useRef(false)

  const [trainers, setTrainers] = useState([])
  const [trainersLoaded, setTrainersLoaded] = useState(false)

  const [encounter, setEncounter] = useState(null)
  const [encounterDetails, setEncounterDetails] = useState(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [searchResults, setSearchResults] = useState(pool)
  const [showSearch, setShowSearch] = useState(false)
  const [activePanel, setActivePanel] = useState(null)

  const [pokemonId, setPokemonId] = useState(null)
  const [nickname, setNickname] = useState('')
  const [nature, setNature] = useState('')
  const [status, setStatus] = useState('')
  const [isShiny, setIsShiny] = useState(false)
  const [showMenu, setShowMenu] = useState(false)

  const [evolutions, setEvolutions] = useState(null)
  const [showEvolve, setShowEvolve] = useState(false)
  const [hasEvolutions, setHasEvolutions] = useState(false)
  const [showNature, setShowNature] = useState(false)

  const [locationName, setLocationName] = useState(row.display_name || '')
  const [isEditingLocationName, setIsEditingLocationName] = useState(false)

  useEffect(() => {
    setLocationName(row.display_name || '')
  }, [row.display_name])

  useEffect(() => {
    if (!isEditingLocationName || !locationNameInputRef.current) return
    locationNameInputRef.current.focus()
    locationNameInputRef.current.select()
  }, [isEditingLocationName])

  useEffect(() => {
    if (!row.is_bonus_location) return
    const trimmedName = locationName.trim()
    const originalName = (row.display_name || '').trim()
    if (!trimmedName || trimmedName === originalName) return

    const timer = setTimeout(() => {
      apiFetch(`/api/runs/${runId}/attempts/${attemptNumber}/bonus-locations`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          canonical_location_id: row.event_id,
          secondary_sort_order: row.secondary_sort_order || 0,
          canonical_name: trimmedName,
        })
      })
        .then(res => res.json())
        .then(data => {
          if (!data.success) {
            throw new Error(data.error || 'Failed to rename bonus location')
          }
        })
        .catch(err => console.error('Failed to rename bonus location:', err))
    }, 600)

    return () => clearTimeout(timer)
  }, [locationName, row.is_bonus_location, row.display_name, row.event_id, row.secondary_sort_order, runId, attemptNumber])

  useEffect(() => {
    if (!savedEncounter) return
    skipNextEncounterSaveRef.current = true
    setEncounter({ species_id: savedEncounter.species_id, name: savedEncounter.species_name })
    setSearchQuery(savedEncounter.species_name || '')
    setPokemonId(savedEncounter.pokemon_id || null)
    setNickname(savedEncounter.nickname || '')
    setNature(savedEncounter.nature || '')
    setStatus(savedEncounter.status || '')
    setIsShiny(savedEncounter.shiny === 'True' || savedEncounter.shiny === true)
  }, [savedEncounter?.pokemon_id])

  useEffect(() => {
    if (!encounter?.species_id) {
      setEncounterDetails(null)
      return
    }
    const controller = new AbortController()
    const query = gameId ? `?game_id=${gameId}` : ''
    apiFetch(`/api/species/${encounter.species_id}/summary${query}`, { signal: controller.signal })
      .then(res => res.json())
      .then(data => setEncounterDetails(data))
      .catch(err => {
        if (err.name !== 'AbortError') {
          console.error('Failed to load species summary:', err)
          setEncounterDetails(null)
        }
      })
    return () => controller.abort()
  }, [encounter?.species_id, gameId])

  useEffect(() => {
    if (!encounter?.species_id) return
    if (!['Captured', 'Dead', 'Missed'].includes(status)) return
    if (skipNextEncounterSaveRef.current) {
      skipNextEncounterSaveRef.current = false
      return
    }
    const timer = setTimeout(() => {
      apiFetch('/api/pokebank/save', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          run_id: runId,
          attempt_number: attemptNumber,
          location_id: row.event_id,
          bonus_location: row.secondary_sort_order || 0,
          species_id: encounter.species_id,
          nickname: nickname || null,
          nature: nature || null,
          status: status || null,
          shiny: isShiny ? 'True' : null,
          pokemon_id: pokemonId || null,
        })
      })
        .then(res => res.json())
        .then(data => {
          if (data.pokemon_id) setPokemonId(data.pokemon_id)
          if (onEncounterChange) onEncounterChange()
        })
        .catch(err => console.error('Failed to save encounter:', err))
    }, 600)
    return () => clearTimeout(timer)
  }, [encounter, nickname, nature, status, isShiny, runId, attemptNumber, row.event_id, row.secondary_sort_order, pokemonId, onEncounterChange])

  useEffect(() => {
    const canShowTrainerView = viewMode === 'master' || viewMode === 'trainers'
    if (trainersLoaded) return
    if (activePanel !== 'trainers') return
    if (!canShowTrainerView) return
    const controller = new AbortController()
    apiFetch(`/api/trainer-list/${row.event_id}?run_id=${runId}&attempt_number=${attemptNumber}`, { signal: controller.signal })
      .then(res => res.json())
      .then(data => {
        setTrainers(data)
        setTrainersLoaded(true)
      })
      .catch(err => {
        if (err.name !== 'AbortError') console.error(err)
      })
    return () => controller.abort()
  }, [trainersLoaded, activePanel, viewMode, row.event_id, runId, attemptNumber])

  useEffect(() => {
    if (searchQuery.length < 2) {
      setSearchResults(pool)
      return
    }
    const timer = setTimeout(() => {
      apiFetch(`/api/species/search?q=${searchQuery}`)
        .then(res => res.json())
        .then(data => setSearchResults(data))
    }, 300)
    return () => clearTimeout(timer)
  }, [searchQuery, pool])

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (searchRef.current && !searchRef.current.contains(event.target)) {
        setShowSearch(false)
      }
      if (menuRef.current && !menuRef.current.contains(event.target)) {
        setShowMenu(false)
      }
      if (natureRef.current && !natureRef.current.contains(event.target)) {
        setShowNature(false)
      }
    }

    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  useEffect(() => {
    if (!encounter?.species_id) {
      setHasEvolutions(false)
      setEvolutions(null)
      return
    }
    apiFetch(`/api/evolutions/${encounter.species_id}`)
      .then(res => res.json())
      .then(data => {
        setEvolutions(data)
        setHasEvolutions(data.length > 0)
      })
      .catch(() => {
        setHasEvolutions(false)
        setEvolutions([])
      })
  }, [encounter?.species_id])

  const availableTrainers = trainers.filter(t => !t.is_event)
  const defeatedTrainerCount = availableTrainers.filter(t => Boolean(t.is_defeated)).length
  const initialTrainerCount = Number(row.trainer_count || 0)
  const trainerCount = trainersLoaded ? availableTrainers.length : initialTrainerCount
  const trainerButtonDisabled = trainersLoaded ? availableTrainers.length === 0 : initialTrainerCount === 0
  const inParty = pokemonId ? partyPokemonIds.has(pokemonId) : false
  const summaryName = nickname || encounter?.name || 'Encounter'
  const type1 = encounterDetails?.type1 || null
  const type2 = encounterDetails?.type2 || null
  const showEncounterView = viewMode === 'master' || viewMode === 'encounters'
  const showTrainerView = viewMode === 'master' || viewMode === 'trainers'
  const scaleStat = Math.max(
    150,
    ...STAT_ROWS.map(stat => {
      const baseValue = Number(encounterDetails?.[stat.key]) || 0
      const adjustedValue = getNatureAdjustedStatValue(nature, stat.label, baseValue) || 0
      return Math.max(baseValue, adjustedValue)
    })
  )

  const togglePanel = (panelName) => {
    setActivePanel(currentPanel => currentPanel === panelName ? null : panelName)
  }

  useEffect(() => {
    if (activePanel === 'encounter' && !showEncounterView) {
      setActivePanel(null)
      return
    }
    if (activePanel === 'trainers' && !showTrainerView) {
      setActivePanel(null)
    }
  }, [activePanel, showEncounterView, showTrainerView])

  const handleClear = () => {
    if (pokemonId) {
      apiFetch(`/api/pokebank/${pokemonId}`, { method: 'DELETE' })
        .then(() => { if (onEncounterChange) onEncounterChange() })
        .catch(err => console.error('Failed to delete encounter:', err))
    }
    setEncounter(null)
    setEncounterDetails(null)
    setSearchQuery('')
    setSearchResults(pool)
    setPokemonId(null)
    setNickname('')
    setNature('')
    setStatus('')
    setIsShiny(false)
    setShowMenu(false)
    setActivePanel(null)
  }

  const handleAddLocation = () => {
    apiFetch(`/api/runs/${runId}/attempts/${attemptNumber}/bonus-locations`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ canonical_location_id: row.event_id })
    })
      .then(res => res.json())
      .then(data => {
        if (!data.success) {
          throw new Error(data.error || 'Failed to add bonus location')
        }
        setShowMenu(false)
        if (onStructureChange) onStructureChange()
      })
      .catch(err => console.error('Failed to add bonus location:', err))
  }

  const handleDeleteLocation = () => {
    apiFetch(`/api/runs/${runId}/attempts/${attemptNumber}/bonus-locations`, {
      method: 'DELETE',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        canonical_location_id: row.event_id,
        secondary_sort_order: row.secondary_sort_order || 0,
      })
    })
      .then(res => res.json())
      .then(data => {
        if (!data.success) {
          throw new Error(data.error || 'Failed to delete bonus location')
        }
        setShowMenu(false)
        if (onStructureChange) onStructureChange()
      })
      .catch(err => console.error('Failed to delete bonus location:', err))
  }

  const handleDeath = () => {
    setStatus('Dead')
    if (encounter?.species_id && onStatusChange) {
      onStatusChange(row.encounter_key, encounter.species_id, 'Dead')
    }
    if (pokemonId) {
      apiFetch(`/api/runs/${runId}/attempts/${attemptNumber}/party/${pokemonId}`, { method: 'DELETE' })
        .then(() => { if (onPartyChange) onPartyChange() })
        .catch(err => console.error('Failed to remove from party on death:', err))
    }
  }

  const handleRevive = () => {
    setStatus('Captured')
    if (encounter?.species_id && onStatusChange) {
      onStatusChange(row.encounter_key, encounter.species_id, 'Captured')
    }
  }

  const handleAddToParty = () => {
    if (!pokemonId) return
    apiFetch(`/api/runs/${runId}/attempts/${attemptNumber}/party`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ pokemon_id: pokemonId })
    })
      .then(res => res.json())
      .then(() => { if (onPartyChange) onPartyChange() })
      .catch(err => console.error('Failed to add to party:', err))
  }

  const handleRemoveFromParty = () => {
    if (!pokemonId) return
    apiFetch(`/api/runs/${runId}/attempts/${attemptNumber}/party/${pokemonId}`, { method: 'DELETE' })
      .then(() => { if (onPartyChange) onPartyChange() })
      .catch(err => console.error('Failed to remove from party:', err))
  }

  const handlePartyToggle = () => {
    if (!pokemonId || status !== 'Captured') return
    if (inParty) {
      handleRemoveFromParty()
      return
    }
    handleAddToParty()
  }

  const handleEncounterSelect = (species) => {
    setEncounter(species)
    setSearchQuery(species.name)
    setShowSearch(false)
    setActivePanel('encounter')
  }

  const handleEvolveSelect = (evo) => {
    setEncounter({ species_id: evo.to_species_id, name: evo.name })
    setSearchQuery(evo.name)
    setShowEvolve(false)
    setEvolutions(null)
  }

  const handleTrainerVictoryRecorded = (trainerId) => {
    setTrainers(prev => prev.map(trainer => (
      trainer.trainer_id === trainerId
        ? { ...trainer, is_defeated: 1 }
        : trainer
    )))
    if (typeof onVictoryRecorded === 'function') {
      onVictoryRecorded()
    }
  }

  const renderLocationCell = () => {
    if (!row.is_bonus_location) {
      return (
        <div style={{ fontWeight: 'bold', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }} title={row.display_name}>
          {row.display_name}
        </div>
      )
    }

    if (isEditingLocationName) {
      return (
        <input
          ref={locationNameInputRef}
          type="text"
          value={locationName}
          onChange={e => setLocationName(e.target.value)}
          onBlur={() => {
            const trimmedName = locationName.trim()
            setLocationName(trimmedName || row.display_name || '')
            setIsEditingLocationName(false)
          }}
          onKeyDown={e => {
            if (e.key === 'Enter') {
              e.currentTarget.blur()
            }
            if (e.key === 'Escape') {
              setLocationName(row.display_name || '')
              setIsEditingLocationName(false)
            }
          }}
          style={{ width: '100%', height: '36px', boxSizing: 'border-box', fontWeight: 'bold', borderRadius: '10px' }}
        />
      )
    }

    return (
      <button
        type="button"
        onClick={() => setIsEditingLocationName(true)}
        title="Rename location"
        style={{
          width: '100%',
          padding: 0,
          border: 'none',
          background: 'transparent',
          color: 'inherit',
          fontWeight: 'bold',
          textAlign: 'left',
          cursor: 'text',
          whiteSpace: 'nowrap',
          overflow: 'hidden',
          textOverflow: 'ellipsis'
        }}
      >
        {locationName || row.display_name}
      </button>
    )
  }

  return (
    <div style={{ marginBottom: '14px' }}>
      {showEvolve && (
        <div style={{
          position: 'fixed',
          inset: 0,
          backgroundColor: 'rgba(0,0,0,0.7)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 1000
        }}>
          <div style={{
            background: '#1e1f26',
            border: '1px solid #444',
            borderRadius: '10px',
            padding: '28px 32px',
            maxWidth: '420px',
            width: '90%',
            textAlign: 'center'
          }}>
            <h2 style={{ marginTop: 0, color: '#f3f4f6' }}>Evolve {encounter?.name}?</h2>
            {evolutions === null ? (
              <p style={{ color: '#aaa' }}>Loading...</p>
            ) : evolutions.length === 0 ? (
              <p style={{ color: '#aaa' }}>No evolutions available.</p>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', marginTop: '16px' }}>
                {evolutions.map(evo => (
                  <button
                    key={evo.to_species_id}
                    onClick={() => handleEvolveSelect(evo)}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      gap: '10px',
                      padding: '8px 16px',
                      fontSize: '0.9em',
                      cursor: 'pointer',
                      color: '#7ec8e3',
                      borderColor: '#7ec8e3'
                    }}
                  >
                    <Sprite speciesId={evo.to_species_id} size={48} />
                    {evo.name}
                  </button>
                ))}
              </div>
            )}
            <button
              onClick={() => { setShowEvolve(false); setEvolutions(null) }}
              style={{ marginTop: '20px', padding: '6px 16px', cursor: 'pointer', fontSize: '0.85em' }}
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: '8px',
        minWidth: 0,
        padding: '2px 0',
        flexWrap: 'wrap',
      }}>
        <div style={{ minWidth: 0, flex: '0 1 220px' }}>
          {renderLocationCell()}
        </div>

        {showEncounterView && (
          <>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', width: '46px', height: '46px', flex: '0 0 auto', visibility: activePanel === 'encounter' ? 'hidden' : 'visible' }}>
              {encounter?.species_id ? (
                <Sprite speciesId={encounter.species_id} size={52} shiny={isShiny} />
              ) : (
                <img
                  src="/sprites/Standard/substitute.png"
                  width="52"
                  height="52"
                  alt="No encounter"
                  style={{ imageRendering: 'pixelated', objectFit: 'contain', flexShrink: 0, opacity: 0.7 }}
                />
              )}
            </div>

            <SummaryButton active={activePanel === 'encounter'} onClick={() => togglePanel('encounter')} style={{ flex: '0 1 240px', width: '240px', minWidth: 0, textAlign: 'left' }}>
              <span style={{ fontWeight: 'bold', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', display: 'block' }}>
                {summaryName}
              </span>
            </SummaryButton>
          </>
        )}

        {showTrainerView && (
          <SummaryButton disabled={trainerButtonDisabled} active={activePanel === 'trainers'} onClick={() => togglePanel('trainers')} style={{ whiteSpace: 'nowrap' }}>
            Trainers {defeatedTrainerCount}/{trainerCount}
          </SummaryButton>
        )}

        {showEncounterView && activePanel !== 'encounter' && (
          <>
            {status === 'Dead' ? (
              <div style={ROW_ACTION_GROUP_STYLE}>
                <SummaryButton disabled={!pokemonId} onClick={handleRevive} style={{ gridColumn: '1 / -1', minWidth: 0, width: '100%', whiteSpace: 'nowrap' }}>
                  Revive
                </SummaryButton>
              </div>
            ) : (
              <div style={ROW_ACTION_GROUP_STYLE}>
                <SummaryButton disabled={!pokemonId || status !== 'Captured'} onClick={handlePartyToggle} style={{ whiteSpace: 'nowrap' }}>
                  Party {inParty ? '-' : '+'}
                </SummaryButton>

                <SummaryButton disabled={!pokemonId || status !== 'Captured'} onClick={handleDeath} style={{ whiteSpace: 'nowrap' }}>
                  Dead
                </SummaryButton>

                <SummaryButton disabled={!hasEvolutions || status !== 'Captured'} onClick={() => setShowEvolve(true)} style={{ whiteSpace: 'nowrap' }}>
                  Evolve
                </SummaryButton>
              </div>
            )}
          </>
        )}

        <div ref={menuRef} style={{ position: 'relative', marginLeft: 'auto' }}>
          <SummaryButton onClick={() => setShowMenu(current => !current)} style={{ minWidth: 0, padding: '6px 10px' }}>
            ...
          </SummaryButton>
          {showMenu && (
            <div style={{
              position: 'absolute',
              top: '62px',
              right: 0,
              background: '#1e1f26',
              border: '1px solid #555',
              borderRadius: '8px',
              zIndex: 1000,
              minWidth: '140px',
              overflow: 'hidden'
            }}>
              <div
                onClick={handleAddLocation}
                style={{ padding: '10px 12px', cursor: 'pointer', color: '#7ec8e3', borderBottom: '1px solid #333' }}
              >
                Add location
              </div>
              {row.is_bonus_location && (
                <div
                  onClick={handleDeleteLocation}
                  style={{ padding: '10px 12px', cursor: 'pointer', color: '#e55', borderBottom: '1px solid #333' }}
                >
                  Delete location
                </div>
              )}
              <div
                onClick={handleClear}
                style={{ padding: '10px 12px', cursor: 'pointer', color: '#e55' }}
              >
                Clear encounter
              </div>
            </div>
          )}
        </div>
      </div>

      {showEncounterView && activePanel === 'encounter' && (
        <div style={{ ...PANEL_STYLE, marginTop: '10px', padding: '16px' }}>
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'minmax(220px, 1.05fr) minmax(220px, 1fr) minmax(220px, 1fr)',
            gap: '14px',
            alignItems: 'stretch',
          }}>
            <div style={{ display: 'grid', gridTemplateRows: 'auto 1fr auto', gap: '14px', minHeight: '320px', padding: '14px', border: 'none', background: 'transparent' }}>
              <div ref={searchRef} style={{ position: 'relative' }}>
                <input
                  type="text"
                  placeholder="Encounter"
                  value={searchQuery}
                  onChange={(e) => {
                    setSearchQuery(e.target.value)
                    setEncounter(null)
                    setEncounterDetails(null)
                    setShowSearch(true)
                  }}
                  onFocus={() => {
                    setShowSearch(true)
                    setActivePanel('encounter')
                  }}
                  style={{
                    width: '100%',
                    height: '40px',
                    boxSizing: 'border-box',
                    borderRadius: '10px',
                    border: '1px solid #3a4050',
                    background: '#0f131a',
                    color: '#eef2f7',
                    padding: '0 12px'
                  }}
                />

                {showSearch && searchResults.length > 0 && (
                  <div style={{
                    position: 'absolute',
                    top: '46px',
                    left: 0,
                    right: 0,
                    maxHeight: '190px',
                    overflowY: 'auto',
                    background: '#1a1f29',
                    border: '1px solid #3a4050',
                    borderRadius: '10px',
                    zIndex: 1000
                  }}>
                    {searchResults.map(species => (
                      <div
                        key={species.species_id}
                        onClick={() => handleEncounterSelect(species)}
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          gap: '8px',
                          padding: '8px 10px',
                          cursor: 'pointer',
                          borderBottom: '1px solid #262d39',
                          ...(dupedFamilyIds.has(species.species_id) && species.species_id !== savedEncounter?.species_id ? { opacity: 0.35, color: '#888' } : {})
                        }}
                      >
                        <Sprite speciesId={species.species_id} size={26} useIcon />
                        <span>{species.name}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              <div style={{
                position: 'relative',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                border: '1px solid #2f3744',
                borderRadius: '12px',
                background: '#0f131a',
                minHeight: '200px'
              }}>
                <button
                  type="button"
                  onClick={() => setIsShiny(current => !current)}
                  title="Toggle shiny"
                  style={{
                    position: 'absolute',
                    top: '8px',
                    left: '8px',
                    width: '28px',
                    height: '28px',
                    border: '1px solid #4a5363',
                    borderRadius: '8px',
                    background: isShiny ? '#2d2410' : '#171b23',
                    color: isShiny ? '#f4d35e' : '#7b8494',
                    cursor: 'pointer',
                    fontSize: '0.9em',
                    lineHeight: 1
                  }}
                >
                  ★
                </button>
                {encounter?.species_id ? (
                  <Sprite speciesId={encounter.species_id} size={200} shiny={isShiny} />
                ) : (
                  <img
                    src="/sprites/Standard/substitute.png"
                    width="160"
                    height="160"
                    alt="No encounter"
                    style={{ imageRendering: 'pixelated', objectFit: 'contain', opacity: 0.78 }}
                  />
                )}
              </div>

              <TypeIconRow
                types={[type1, type2]}
                height={22}
                gap={8}
                placeholder
                justifyContent="center"
                style={{ minHeight: '28px' }}
              />
            </div>

            <div style={{ display: 'grid', gridTemplateRows: 'auto 1fr auto', gap: '14px', minHeight: '320px', padding: '14px', border: 'none', background: 'transparent' }}>
              <div style={{ border: '1px solid #2f3744', borderRadius: '12px', background: '#0f131a', padding: '14px', textAlign: 'center' }}>
                <div style={{ fontSize: '0.72em',  color: '#8d97ab', marginBottom: '4px' }}>BST</div>
                <div style={{ fontSize: '1.7em', fontWeight: 'bold', color: '#f5f7fb' }}>{encounterDetails?.bst ?? '—'}</div>
              </div>

              <div style={{ border: '1px solid #2f3744', borderRadius: '12px', background: '#0f131a', padding: '14px' }}>
                <div style={{ fontSize: '0.72em', color: '#8d97ab', marginBottom: '10px' }}>Stat Spread</div>
                <div style={{ display: 'grid', gap: '8px' }}>
                  {STAT_ROWS.map(stat => {
                    const value = encounterDetails?.[stat.key]
                    const widthPct = value != null ? Math.min(100, Math.round((value / scaleStat) * 100)) : 0
                    const natureModifier = getNatureModifierForStat(nature, stat.label)
                    const adjustedValue = getNatureAdjustedStatValue(nature, stat.label, value)
                    const adjustedWidthPct = adjustedValue != null ? Math.min(100, Math.round((adjustedValue / scaleStat) * 100)) : 0
                    const deltaLeftPct = Math.min(widthPct, adjustedWidthPct)
                    const deltaWidthPct = Math.max(0, Math.abs(adjustedWidthPct - widthPct))
                    return (
                      <div key={stat.key} style={{ display: 'grid', gridTemplateColumns: '60px 30px 1fr', gap: '8px', alignItems: 'center' }}>
                        <span style={{ display: 'flex', justifyContent: 'flex-start', alignItems: 'center', gap: '4px', whiteSpace: 'nowrap' }}>
                          <span style={{ width: '28px', fontSize: '0.72em', color: '#9ca0ad', textAlign: 'left' }}>{stat.label}</span>
                          <span style={{ width: '38px', fontSize: '0.72em', color: natureModifier?.color || 'transparent', textAlign: 'left' }}>
                            {natureModifier?.text || '+10%'}
                          </span>
                        </span>
                        <span style={{ fontSize: '0.75em', color: '#eef2f7', textAlign: 'right', whiteSpace: 'nowrap' }}>{value ?? '—'}</span>
                        <div style={{ position: 'relative', height: '8px', background: '#252c38', borderRadius: '999px', overflow: 'hidden' }}>
                          <div
                            style={{
                              position: 'absolute',
                              left: 0,
                              top: '1px',
                              width: `${widthPct}%`,
                              height: '6px',
                              background: getStatBarColor(value),
                              borderRadius: '999px'
                            }}
                          />
                          {natureModifier && deltaWidthPct > 0 && (
                            <div
                              style={{
                                position: 'absolute',
                                left: `${deltaLeftPct}%`,
                                top: '1px',
                                width: `${deltaWidthPct}%`,
                                height: '6px',
                                background: natureModifier.color,
                                opacity: 0.45,
                                borderRadius: '999px'
                              }}
                            />
                          )}
                        </div>
                      </div>
                    )
                  })}
                </div>
              </div>

              <div ref={natureRef} style={{ position: 'relative' }}>
                <button
                  type="button"
                  onClick={() => setShowNature(current => !current)}
                  style={{
                    width: '100%',
                    minHeight: '42px',
                    borderRadius: '10px',
                    border: '1px solid #3a4050',
                    background: '#0f131a',
                    color: '#eef2f7',
                    padding: '8px 12px',
                    textAlign: 'left',
                    cursor: 'pointer'
                  }}
                >
                  {getNatureLabel(nature)}
                </button>
                {showNature && (
                  <div style={{
                    position: 'absolute',
                    top: '48px',
                    left: 0,
                    right: 0,
                    zIndex: 1000,
                    background: '#1e1f26',
                    border: '1px solid #555',
                    borderRadius: '10px',
                    maxHeight: '220px',
                    overflowY: 'auto'
                  }}>
                    <div
                      onClick={() => { setNature(''); setShowNature(false) }}
                      style={{ padding: '8px 12px', cursor: 'pointer', borderBottom: '1px solid #333', color: '#888', fontSize: '0.85em' }}
                    >
                      - Clear -
                    </div>
                    {NATURES.map(entry => (
                      <div
                        key={entry.name}
                        onClick={() => { setNature(entry.name); setShowNature(false) }}
                        style={{
                          display: 'flex',
                          justifyContent: 'space-between',
                          alignItems: 'center',
                          padding: '8px 12px',
                          cursor: 'pointer',
                          borderBottom: '1px solid #2a2b33',
                          backgroundColor: nature === entry.name ? '#2e2f3a' : 'transparent'
                        }}
                      >
                        <span style={{ fontSize: '0.9em' }}>{entry.name}</span>
                        <span style={{ fontSize: '0.75em', marginLeft: '12px', display: 'flex', gap: '6px', alignItems: 'center' }}>
                          {entry.up ? (
                            <>
                              <span style={{ color: '#e55' }}>+{entry.up}</span>
                              <span style={{ color: '#66a8ff' }}>-{entry.down}</span>
                            </>
                          ) : (
                            <span style={{ color: '#888' }}>Neutral</span>
                          )}
                        </span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>

            <div style={{ display: 'grid', gridTemplateRows: 'auto auto 1fr', gap: '14px', minHeight: '320px', padding: '14px', border: 'none', background: 'transparent' }}>
              <input
                type="text"
                placeholder="Nickname"
                value={nickname}
                onChange={e => setNickname(e.target.value)}
                style={{
                  width: '100%',
                  height: '40px',
                  boxSizing: 'border-box',
                  borderRadius: '10px',
                  border: '1px solid #3a4050',
                  background: '#0f131a',
                  color: '#eef2f7',
                  padding: '0 12px'
                }}
              />

              <select
                value={status}
                onChange={e => {
                  const newStatus = e.target.value
                  setStatus(newStatus)
                  if (encounter?.species_id && onStatusChange) {
                    onStatusChange(row.encounter_key, encounter.species_id, newStatus)
                  }
                }}
                style={{
                  width: '100%',
                  height: '40px',
                  boxSizing: 'border-box',
                  borderRadius: '10px',
                  border: '1px solid #3a4050',
                  background: '#0f131a',
                  color: '#eef2f7',
                  padding: '0 12px'
                }}
              >
                <option value="">Status</option>
                <option value="Captured">Captured</option>
                <option value="Missed">Missed</option>
                <option value="Dead">Dead</option>
              </select>

              <div style={{ display: 'flex', alignItems: 'flex-end' }}>
                {status === 'Dead' ? (
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr', gap: '10px', width: '100%' }}>
                    <SummaryButton disabled={!pokemonId} onClick={handleRevive} style={{ minHeight: '42px' }}>
                      Revive
                    </SummaryButton>
                  </div>
                ) : (
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '10px', width: '100%' }}>
                    <SummaryButton disabled={!pokemonId || status !== 'Captured'} onClick={handlePartyToggle} style={{ minHeight: '42px' }}>
                      {inParty ? 'Party -' : 'Party'}
                    </SummaryButton>
                    <SummaryButton disabled={!pokemonId || status !== 'Captured'} onClick={handleDeath} style={{ minHeight: '42px' }}>
                      Dead
                    </SummaryButton>
                    <SummaryButton disabled={!hasEvolutions || status !== 'Captured'} onClick={() => setShowEvolve(true)} style={{ minHeight: '42px' }}>
                      Evolve
                    </SummaryButton>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {showTrainerView && activePanel === 'trainers' && (
        <div style={{ ...PANEL_STYLE, marginTop: '10px', padding: '16px' }}>
          {!trainersLoaded ? (
            <div style={{ color: '#888', fontSize: '0.85em' }}>Loading trainers...</div>
          ) : availableTrainers.length === 0 ? (
            <div style={{ color: '#888', fontSize: '0.85em' }}>No trainers at this location.</div>
          ) : (
            <div>
              {availableTrainers.map(trainer => (
                <TrainerCard
                  key={trainer.trainer_id}
                  encounterName={trainer.encounter_name}
                  trainerName={trainer.trainer_name}
                  trainerClass={trainer.trainer_class}
                  trainerItems={trainer.trainer_items}
                  gameId={gameId}
                  runId={runId}
                  attemptId={attemptNumber}
                  trainerId={trainer.trainer_id}
                  enableBattle
                  isDefeated={Boolean(trainer.is_defeated)}
                  onVictoryRecorded={() => handleTrainerVictoryRecorded(trainer.trainer_id)}
                />
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default LocationRow