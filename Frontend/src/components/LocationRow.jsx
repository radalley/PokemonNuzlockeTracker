import { useEffect, useMemo, useRef, useState } from 'react'
import { apiFetch } from '../utils/api'
import Sprite from './Sprite'
import TrainerCard from './TrainerCard'
import { TypeIconRow } from './TypeIcon'
import {
  saveEncounter,
  deleteEncounterById,
  getTrainerList,
  addBonusLocation,
  deleteBonusLocation,
  renameBonusLocation,
  addToParty,
  removeFromParty,
} from '../utils/dataLayer'

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
  border: '1px solid var(--border-strong)',
  borderRadius: '14px',
  background: 'var(--surface)',
  boxShadow: '0 2px 6px rgba(0,0,0,0.4)',
}

const SUMMARY_BUTTON_STYLE = {
  minHeight: '34px',
  padding: '6px 10px',
  border: '1px solid var(--border-strong)',
  borderRadius: '999px',
  background: 'transparent',
  color: 'var(--text-secondary)',
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
        background: active ? 'var(--surface-mid)' : 'var(--surface-deep)',
        borderColor: active ? '#7ec8e3' : 'var(--border-strong)',
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

function LocationRow({ row, savedEncounter, runId, attemptNumber, gameId = null, generation = null, pool = [], allSpecies = [], dupedFamilyIds = new Set(), onEncounterChange, onStatusChange, onPartyChange, onStructureChange, partyPokemonIds = new Set(), onVictoryRecorded = null, viewMode = 'master', attemptEnded = false }) {
  const searchRef = useRef(null)
  const menuRef = useRef(null)
  const natureRef = useRef(null)
  const locationNameInputRef = useRef(null)
  const skipNextEncounterSaveRef = useRef(false)
  const saveStatusImmediatelyRef = useRef(false)
  const encounterSaveSequenceRef = useRef(0)
  const pokemonIdRef = useRef(null)

  const [trainers, setTrainers] = useState([])
  const [trainersLoaded, setTrainersLoaded] = useState(false)
  // A venue whose whole roster is rematch/event trainers (stadiums, the
  // cruise, League rematches) opens straight onto its special groups
  // instead of an empty "No trainers" state.
  const [showSpecialTrainers, setShowSpecialTrainers] = useState(
    Number(row.trainer_count ?? 0) === 0 && Number(row.special_trainer_count ?? 0) > 0)

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
  const [ability, setAbility] = useState('')
  const [abilityOptions, setAbilityOptions] = useState([])
  const [saveNonce, setSaveNonce] = useState(0)
  const [isShiny, setIsShiny] = useState(false)
  const [gender, setGender] = useState('male')
  const [isSavingEncounter, setIsSavingEncounter] = useState(false)
  const [encounterSaveError, setEncounterSaveError] = useState('')
  const [forms, setForms] = useState([])
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
      renameBonusLocation(runId, attemptNumber, row.event_id, row.secondary_sort_order || 0, trimmedName)
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
    pokemonIdRef.current = savedEncounter.pokemon_id || null
    setPokemonId(savedEncounter.pokemon_id || null)
    setNickname(savedEncounter.nickname || '')
    setNature(savedEncounter.nature || '')
    setStatus(savedEncounter.status || '')
    setAbility(savedEncounter.ability || '')
    setIsShiny(savedEncounter.shiny === 'True' || savedEncounter.shiny === true)
    setGender(savedEncounter.gender || 'male')
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
    if (!encounter?.species_id) { setForms([]); return }
    const controller = new AbortController()
    apiFetch(`/api/species/${encounter.species_id}/forms`, { signal: controller.signal })
      .then(res => res.json())
      .then(data => setForms(Array.isArray(data) ? data : []))
      .catch(err => { if (err.name !== 'AbortError') setForms([]) })
    return () => controller.abort()
  }, [encounter?.species_id])

  // Ability choices resolve version-group-aware (a hack's override layer
  // wins), unlike the generation-only species summary.
  useEffect(() => {
    if (!encounter?.species_id) { setAbilityOptions([]); return }
    const controller = new AbortController()
    const query = gameId ? `?game_id=${gameId}` : ''
    apiFetch(`/api/species/${encounter.species_id}/abilities${query}`, { signal: controller.signal })
      .then(res => res.json())
      .then(data => setAbilityOptions(Array.isArray(data) ? data : []))
      .catch(err => { if (err.name !== 'AbortError') setAbilityOptions([]) })
    return () => controller.abort()
  }, [encounter?.species_id, gameId])

  // Set gender default from species data when selecting a new (unsaved) encounter
  useEffect(() => {
    if (!encounterDetails || pokemonId) return
    if (encounterDetails.has_gender === 'false') {
      setGender('none')
    } else if (encounterDetails.default_gender === 'female') {
      setGender('female')
    } else {
      setGender('male')
    }
  }, [encounterDetails?.species_id])

  useEffect(() => {
    if (!encounter?.species_id) return
    if (!['Captured', 'Dead', 'Missed'].includes(status)) return
    if (skipNextEncounterSaveRef.current) {
      skipNextEncounterSaveRef.current = false
      return
    }
    const saveSequence = ++encounterSaveSequenceRef.current
    const saveDelay = saveStatusImmediatelyRef.current ? 0 : 600
    saveStatusImmediatelyRef.current = false

    if (saveDelay === 0) {
      setIsSavingEncounter(true)
      setEncounterSaveError('')
    }

    const persistEncounter = () => {
      const wasCreating = !pokemonIdRef.current
      setIsSavingEncounter(true)
      setEncounterSaveError('')
      saveEncounter(
        runId,
        attemptNumber,
        row.event_id,
        row.secondary_sort_order || 0,
        encounter.species_id,
        encounter.name,
        nickname,
        nature,
        status,
        isShiny,
        pokemonIdRef.current,
        gender,
        ability,
      )
        .then(data => {
          if (!data?.pokemon_id) {
            throw new Error(data?.error || 'Encounter save did not return a Pokemon ID')
          }
          if (saveSequence !== encounterSaveSequenceRef.current) return
          pokemonIdRef.current = data.pokemon_id
          setPokemonId(data.pokemon_id)
          if (onEncounterChange) onEncounterChange()
          if (onPartyChange) onPartyChange()
        })
        .catch(err => {
          console.error('Failed to save encounter:', err)
          if (saveSequence === encounterSaveSequenceRef.current) {
            setEncounterSaveError('Encounter could not be saved. Please try again.')
            // A failed CREATE means the parent's optimistic status entry is
            // a phantom -- roll it back so dupe graying stays truthful.
            if (wasCreating && status && encounter?.species_id && onStatusChange) {
              onStatusChange(row.encounter_key, encounter.species_id, '')
            }
          }
        })
        .finally(() => {
          if (saveSequence === encounterSaveSequenceRef.current) {
            setIsSavingEncounter(false)
          }
        })
    }

    if (saveDelay === 0) {
      persistEncounter()
      return undefined
    }

    const timer = setTimeout(persistEncounter, saveDelay)
    return () => clearTimeout(timer)
  }, [encounter, nickname, nature, status, isShiny, gender, ability, saveNonce, runId, attemptNumber, row.event_id, row.secondary_sort_order, onEncounterChange, onPartyChange])

  useEffect(() => {
    const canShowTrainerView = viewMode === 'master' || viewMode === 'trainers'
    if (row.is_bonus_location) return
    if (trainersLoaded) return
    if (activePanel !== 'trainers') return
    if (!canShowTrainerView) return
    const controller = new AbortController()
    getTrainerList(row.event_id, runId, attemptNumber, controller.signal, {
      gameId,
      versionGroupId: row.version_group_id,
      includeRematches: showSpecialTrainers,
      includeEvents: showSpecialTrainers,
    })
      .then(data => {
        setTrainers(data)
        setTrainersLoaded(true)
      })
      .catch(err => {
        if (err.name !== 'AbortError') console.error(err)
      })
    return () => controller.abort()
  }, [trainersLoaded, activePanel, viewMode, row.event_id, row.is_bonus_location, runId, attemptNumber, gameId, row.version_group_id, showSpecialTrainers])

  useEffect(() => {
    if (searchQuery.length < 2) {
      setSearchResults(pool)
      return
    }
    if (allSpecies.length > 0) {
      const q = searchQuery.toLowerCase()
      setSearchResults(allSpecies.filter(s => s.name.toLowerCase().includes(q)))
      return
    }
    // fallback to API if species list not yet loaded
    const timer = setTimeout(() => {
      apiFetch(`/api/species/search?q=${searchQuery}`)
        .then(res => res.json())
        .then(data => setSearchResults(data))
        .catch(() => {})
    }, 300)
    return () => clearTimeout(timer)
  }, [searchQuery, allSpecies, pool])

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

  // Regular trainers drive the counts; rematches and one-off event battles
  // arrive only when the toggle asks for them and render as their own groups.
  const availableTrainers = trainers.filter(t => !t.is_event && !t.is_rematch)
  const specialTrainers = trainers.filter(t => t.is_event || t.is_rematch)
  // Group by sub-area (gym, building, cave floor). The backend already orders
  // area-less trainers first, then areas by their sort order, so insertion
  // order here is the display order.
  const trainerGroups = useMemo(() => {
    const groups = []
    const byArea = new Map()
    for (const trainer of availableTrainers) {
      const key = trainer.area_id ?? null
      if (!byArea.has(key)) {
        const group = { key, name: trainer.area_name || null, kind: trainer.area_kind || null, trainers: [] }
        byArea.set(key, group)
        groups.push(group)
      }
      byArea.get(key).trainers.push(trainer)
    }
    return groups
  }, [availableTrainers])
  const hasNamedAreas = trainerGroups.some(g => g.name)
  const specialGroups = useMemo(() => {
    const rematches = specialTrainers.filter(t => t.is_rematch)
    const events = specialTrainers.filter(t => t.is_event && !t.is_rematch)
    const groups = []
    if (rematches.length) groups.push({ key: 'rematches', name: 'Rematches', trainers: rematches })
    if (events.length) groups.push({ key: 'events', name: 'Special Battles', trainers: events })
    return groups
  }, [specialTrainers])
  // Use the loaded value if trainers are loaded, otherwise use the seed value from row
  const defeatedTrainerCount = trainersLoaded
    ? availableTrainers.filter(t => Boolean(t.is_defeated)).length
    : Number(row.trainer_count ?? 0) - Number(row.available_trainer_count ?? 0)
  const hasSeedTrainerCount = row.trainer_count != null
  const initialTrainerCount = Number(row.trainer_count ?? 0)
  const initialSpecialCount = Number(row.special_trainer_count ?? 0)
  const trainerCount = trainersLoaded ? availableTrainers.length : initialTrainerCount
  // Allow first load only when trainer counts are unknown; honor explicit zero
  // counts. A location whose roster is all rematch/event trainers (stadiums,
  // the cruise, League rematches) still opens its panel for the special groups.
  const trainerButtonDisabled = trainersLoaded
    ? (availableTrainers.length === 0 && specialTrainers.length === 0 && initialSpecialCount === 0)
    : (hasSeedTrainerCount && initialTrainerCount === 0 && initialSpecialCount === 0)
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
    // Invalidate any in-flight save so a pending create cannot resurrect
    // the row after it was cleared.
    encounterSaveSequenceRef.current += 1
    // A status that never reached the server left an optimistic entry in
    // the parent (dupe graying); roll it back.
    if (!pokemonIdRef.current && status && encounter?.species_id && onStatusChange) {
      onStatusChange(row.encounter_key, encounter.species_id, '')
    }
    if (pokemonId) {
      deleteEncounterById(runId, attemptNumber, pokemonId)
        .then(() => { if (onEncounterChange) onEncounterChange() })
        .catch(err => console.error('Failed to delete encounter:', err))
    }
    setEncounter(null)
    setEncounterDetails(null)
    setSearchQuery('')
    setSearchResults(pool)
    pokemonIdRef.current = null
    setPokemonId(null)
    setNickname('')
    setNature('')
    setStatus('')
    setAbility('')
    setIsShiny(false)
    setGender('male')
    setForms([])
    setShowMenu(false)
    setActivePanel(null)
  }

  const handleAddLocation = () => {
    addBonusLocation(runId, attemptNumber, row.event_id, row.secondary_sort_order || 0)
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
    deleteBonusLocation(runId, attemptNumber, row.event_id, row.secondary_sort_order || 0)
      .then(data => {
        if (!data.success) {
          throw new Error(data.error || 'Failed to delete bonus location')
        }
        setShowMenu(false)
        if (onStructureChange) onStructureChange()
      })
      .catch(err => console.error('Failed to delete bonus location:', err))
  }

  const updateEncounterStatus = (nextStatus) => {
    saveStatusImmediatelyRef.current = true
    setStatus(nextStatus)
    if (encounter?.species_id && onStatusChange) {
      onStatusChange(row.encounter_key, encounter.species_id, nextStatus)
    }
  }

  const handleDeath = () => {
    updateEncounterStatus('Dead')
    if (pokemonId) {
      removeFromParty(runId, attemptNumber, pokemonId)
        .then(() => { if (onPartyChange) onPartyChange() })
        .catch(err => console.error('Failed to remove from party on death:', err))
    }
  }

  const handleRevive = () => {
    updateEncounterStatus('Captured')
  }

  const handleCatch = () => {
    if (!encounter?.species_id) return
    updateEncounterStatus('Captured')
  }

  const handleMiss = () => {
    if (!encounter?.species_id) return
    updateEncounterStatus('Missed')
    // A mon corrected from Captured to Missed cannot stay in the party.
    if (pokemonId && partyPokemonIds.has(pokemonId)) {
      removeFromParty(runId, attemptNumber, pokemonId)
        .then(() => { if (onPartyChange) onPartyChange() })
        .catch(err => console.error('Failed to remove from party on miss:', err))
    }
  }

  const handleSelectAbility = (value) => {
    saveStatusImmediatelyRef.current = true
    setAbility(value)
    // Bump the parent's encounters version (same status, no visible change)
    // so a stale in-flight refetch cannot revert the just-picked ability.
    if (encounter?.species_id && status && onStatusChange) {
      onStatusChange(row.encounter_key, encounter.species_id, status)
    }
  }

  const handleAddToParty = () => {
    if (!pokemonId) return
    addToParty(runId, attemptNumber, pokemonId)
      .then(() => { if (onPartyChange) onPartyChange() })
      .catch(err => console.error('Failed to add to party:', err))
  }

  const handleRemoveFromParty = () => {
    if (!pokemonId) return
    removeFromParty(runId, attemptNumber, pokemonId)
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

  const formatAbility = (value) => value
    ? String(value).replace(/^ABILITY_/i, '').replace(/_/g, ' ').toLowerCase().replace(/\b\w/g, c => c.toUpperCase())
    : ''

  const requestImmediateSave = () => {
    saveStatusImmediatelyRef.current = true
    setEncounterSaveError('')
    setSaveNonce(n => n + 1)
    // Retrying a failed create must re-register the optimistic status the
    // failure rolled back.
    if (encounter?.species_id && status && onStatusChange) {
      onStatusChange(row.encounter_key, encounter.species_id, status)
    }
  }

  // One state machine for both action sites (summary row and open panel):
  // no species -> disabled choice; saved-status-pending -> Saving/Retry;
  // unset -> Caught/Missed choice; Captured -> Party/Dead/Evolve;
  // Missed -> muted chip + Caught + Undo; Dead -> Revive.
  const renderEncounterActions = (variant) => {
    const compact = variant === 'summary'
    const groupStyle = compact
      ? ROW_ACTION_GROUP_STYLE
      : { display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '10px', width: '100%' }
    const buttonStyle = compact ? { whiteSpace: 'nowrap' } : { minHeight: '42px' }

    if (!encounter?.species_id) {
      // Also covers a status-bearing row mid species-edit: no live buttons
      // may act on a species that is no longer selected. The summary row
      // stays quiet; the decision lives inside the encounter card.
      if (compact) return null
      return (
        <div className={`encounter-actions encounter-actions--${variant}`} style={{ ...groupStyle, gridTemplateColumns: 'repeat(2, minmax(0, 1fr))' }}>
          <SummaryButton disabled title="Pick a species first" style={{ ...buttonStyle, color: '#52c97a', borderColor: '#52c97a', background: 'rgba(82,201,122,0.12)' }}>
            Caught
          </SummaryButton>
          <SummaryButton disabled title="Pick a species first" style={{ ...buttonStyle, color: '#d4a017', borderColor: '#d4a017', background: 'rgba(212,160,23,0.08)' }}>
            Missed
          </SummaryButton>
        </div>
      )
    }

    if (status && !pokemonId) {
      // The status was chosen but the row hasn't been created server-side
      // (save in flight, or it failed): offer retry instead of dead buttons.
      return (
        <div className={`encounter-actions encounter-actions--${variant}`} style={{ ...groupStyle, gridTemplateColumns: 'repeat(2, minmax(0, 1fr))' }}>
          {isSavingEncounter ? (
            <SummaryButton disabled style={{ ...buttonStyle, gridColumn: '1 / -1', width: '100%' }}>
              Saving...
            </SummaryButton>
          ) : (
            <>
              <SummaryButton onClick={requestImmediateSave} style={{ ...buttonStyle, color: '#e05252', borderColor: '#e05252', background: 'rgba(224,82,82,0.12)' }}>
                Retry Save
              </SummaryButton>
              <SummaryButton onClick={handleClear} title="Discard this encounter" style={buttonStyle}>
                Cancel
              </SummaryButton>
            </>
          )}
        </div>
      )
    }

    if (status === 'Dead') {
      return (
        <div className={`encounter-actions encounter-actions--${variant}`} style={{ ...groupStyle, gridTemplateColumns: compact ? groupStyle.gridTemplateColumns : '1fr' }}>
          <SummaryButton disabled={isSavingEncounter || !pokemonId} onClick={handleRevive} style={{ ...buttonStyle, gridColumn: '1 / -1', minWidth: 0, width: '100%', color: '#d4a017', borderColor: '#d4a017', background: 'rgba(212,160,23,0.12)' }}>
            Revive
          </SummaryButton>
        </div>
      )
    }
    if (status === 'Captured') {
      return (
        <div className={`encounter-actions encounter-actions--${variant}`} style={groupStyle}>
          <SummaryButton disabled={isSavingEncounter || !pokemonId} onClick={handlePartyToggle} style={{ ...buttonStyle, color: inParty ? '#7ec8e3' : '#52c97a', borderColor: inParty ? '#7ec8e3' : '#52c97a', background: inParty ? 'rgba(126,200,227,0.12)' : 'rgba(82,201,122,0.12)' }}>
            {compact ? `Party ${inParty ? '-' : '+'}` : (inParty ? 'Party -' : 'Party')}
          </SummaryButton>
          <SummaryButton disabled={isSavingEncounter || !pokemonId} onClick={handleDeath} style={{ ...buttonStyle, color: '#e05252', borderColor: '#e05252', background: 'rgba(224,82,82,0.12)' }}>
            Dead
          </SummaryButton>
          <SummaryButton disabled={isSavingEncounter || !pokemonId || !hasEvolutions} onClick={() => setShowEvolve(true)} style={{ ...buttonStyle, color: 'var(--accent)', borderColor: 'var(--accent-border)', background: 'var(--accent-bg)' }}>
            Evolve
          </SummaryButton>
        </div>
      )
    }
    if (status === 'Missed') {
      return (
        <div className={`encounter-actions encounter-actions--${variant}`} style={groupStyle}>
          <div style={{ ...buttonStyle, minHeight: compact ? '34px' : '42px', display: 'inline-flex', alignItems: 'center', justifyContent: 'center', padding: '6px 10px', fontSize: '0.8em', color: '#d4a017', border: '1px dashed #d4a017', borderRadius: '999px', background: 'rgba(212,160,23,0.08)', boxSizing: 'border-box', opacity: 0.9 }}>
            Missed
          </div>
          <SummaryButton disabled={isSavingEncounter} onClick={handleCatch} style={{ ...buttonStyle, color: '#52c97a', borderColor: '#52c97a', background: 'rgba(82,201,122,0.12)' }}>
            Caught
          </SummaryButton>
          <SummaryButton disabled={isSavingEncounter} onClick={handleClear} title="Undo: clear this encounter" style={buttonStyle}>
            Undo
          </SummaryButton>
        </div>
      )
    }
    // No status yet: the two decisions that start an encounter's story,
    // offered only inside the encounter card.
    if (compact) return null
    return (
      <div className={`encounter-actions encounter-actions--${variant}`} style={{ ...groupStyle, gridTemplateColumns: 'repeat(2, minmax(0, 1fr))' }}>
        <SummaryButton disabled={isSavingEncounter} onClick={handleCatch} style={{ ...buttonStyle, color: '#52c97a', borderColor: '#52c97a', background: 'rgba(82,201,122,0.12)' }}>
          Caught
        </SummaryButton>
        <SummaryButton disabled={isSavingEncounter} onClick={handleMiss} style={{ ...buttonStyle, color: '#d4a017', borderColor: '#d4a017', background: 'rgba(212,160,23,0.08)' }}>
          Missed
        </SummaryButton>
      </div>
    )
  }

  // An ability belongs to one species: every species change clears it
  // rather than silently carrying it onto a Pokemon that cannot have it.
  const handleEncounterSelect = (species) => {
    setEncounter(species)
    setAbility('')
    setSearchQuery(species.name)
    setShowSearch(false)
    setActivePanel('encounter')
  }

  const handleEvolveSelect = (evo) => {
    setEncounter({ species_id: evo.to_species_id, name: evo.name })
    setAbility('')
    setSearchQuery(evo.name)
    setShowEvolve(false)
    setEvolutions(null)
  }

  const handleFormSelect = (form) => {
    setEncounter({ species_id: form.species_id, name: form.name })
    setAbility('')
    setSearchQuery(form.name)
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
        <div style={{ fontWeight: 'bold', color: 'var(--text-primary)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }} title={row.display_name}>
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
          color: 'var(--text-primary)',
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
    <div className="location-row" style={{ marginBottom: '14px' }}>
      {showEvolve && (
        // z-index clears the fixed header and footer, which both sit at
        // 1000; the panel scrolls because a species with many evolutions
        // (Eevee has eight) is taller than a phone viewport and was being
        // clipped at both edges with no way to reach the buttons.
        <div
          onClick={() => setShowEvolve(false)}
          style={{
            position: 'fixed',
            inset: 0,
            backgroundColor: 'rgba(0,0,0,0.7)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: '16px',
            overflowY: 'auto',
            overscrollBehavior: 'contain',
            zIndex: 3000
          }}
        >
          <div
            onClick={event => event.stopPropagation()}
            style={{
              background: 'var(--surface)',
              border: '1px solid var(--border-strong)',
              borderRadius: '10px',
              padding: '28px 32px',
              maxWidth: '420px',
              width: '100%',
              maxHeight: 'calc(100svh - 32px)',
              overflowY: 'auto',
              boxSizing: 'border-box',
              textAlign: 'center'
            }}
          >
            <h2 style={{ marginTop: 0, color: 'var(--text-primary)' }}>Evolve {encounter?.name}?</h2>
            {evolutions === null ? (
              <p style={{ color: 'var(--text-secondary)' }}>Loading...</p>
            ) : evolutions.length === 0 ? (
              <p style={{ color: 'var(--text-secondary)' }}>No evolutions available.</p>
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
              onClick={() => setShowEvolve(false)}
              style={{ marginTop: '20px', padding: '6px 16px', cursor: 'pointer', fontSize: '0.85em' }}
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      <div className={`location-row__summary${showEncounterView ? ' has-encounter-view' : ''}`} style={{
        display: 'flex',
        alignItems: 'center',
        gap: '8px',
        minWidth: 0,
        padding: '2px 0',
        flexWrap: 'wrap',
      }}>
        <div className="location-row__name" style={{ minWidth: 0, flex: '0 1 220px' }}>
          {renderLocationCell()}
        </div>

        {showEncounterView && (
          <>
            <div className="location-row__encounter-sprite" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', width: '46px', height: '46px', flex: '0 0 auto', visibility: activePanel === 'encounter' ? 'hidden' : 'visible' }}>
              {encounter?.species_id ? (
                <Sprite speciesId={encounter.species_id} size={52} shiny={isShiny} female={gender === 'female' && encounterDetails?.has_female === 'true'} style={status === 'Dead' ? { filter: 'grayscale(1)', opacity: 0.5 } : status === 'Missed' ? { opacity: 0.4 } : undefined} />
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

            <SummaryButton className="location-row__encounter-button" active={activePanel === 'encounter'} onClick={() => togglePanel('encounter')} style={{ flex: '0 1 240px', width: '240px', minWidth: 0, textAlign: 'left', color: 'var(--text-primary)' }}>
              <span style={{ fontWeight: 'bold', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', display: 'block' }}>
                {summaryName}
              </span>
            </SummaryButton>
          </>
        )}

        {showTrainerView && !row.is_bonus_location && (
          <SummaryButton className="location-row__trainer-button" disabled={trainerButtonDisabled} active={activePanel === 'trainers'} onClick={() => togglePanel('trainers')} style={{ whiteSpace: 'nowrap' }}>
            Trainers {defeatedTrainerCount}/{trainerCount}{(() => {
              const special = trainersLoaded && showSpecialTrainers ? specialTrainers.length : initialSpecialCount
              return special > 0 ? ` +${special}★` : ''
            })()}
          </SummaryButton>
        )}

        {showEncounterView && activePanel !== 'encounter' && renderEncounterActions('summary')}

        <div ref={menuRef} className="location-row__menu" style={{ position: 'relative', marginLeft: 'auto' }}>
          <SummaryButton onClick={() => setShowMenu(current => !current)} style={{ minWidth: 0, padding: '6px 10px' }}>
            ...
          </SummaryButton>
          {showMenu && (
            <div style={{
              position: 'absolute',
              // Tracks the trigger instead of a hardcoded desktop row
              // height, which left the menu floating ~28px adrift on a phone.
              top: 'calc(100% + 6px)',
              right: 0,
              maxHeight: '50svh',
              overflowY: 'auto',
              background: 'var(--surface-mid)',
              border: '1px solid var(--border-strong)',
              borderRadius: '8px',
              zIndex: 1000,
              minWidth: '140px',
              // overflowX, not the shorthand: `overflow: hidden` written
              // after overflowY would reset it and clip the scroll.
              overflowX: 'hidden'
            }}>
              <div
                onClick={handleAddLocation}
                style={{ padding: '10px 12px', cursor: 'pointer', color: '#7ec8e3', borderBottom: '1px solid var(--border-strong)' }}
              >
                Add location
              </div>
              {row.is_bonus_location && (
                <div
                  onClick={handleDeleteLocation}
                  style={{ padding: '10px 12px', cursor: 'pointer', color: '#e55', borderBottom: '1px solid var(--border-strong)' }}
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
              {status === 'Captured' && pokemonId && (
                <div
                  onClick={() => { setShowMenu(false); handleMiss() }}
                  style={{ padding: '10px 12px', cursor: 'pointer', color: '#d4a017' }}
                >
                  Mark as Missed
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {showEncounterView && activePanel === 'encounter' && (
        <div className="location-row__panel location-row__panel--encounter" style={{ ...PANEL_STYLE, marginTop: '10px', padding: '16px' }}>
          <div className="encounter-editor" style={{
            display: 'grid',
            gridTemplateColumns: 'minmax(220px, 1.05fr) minmax(220px, 1fr) minmax(220px, 1fr)',
            gap: '14px',
            alignItems: 'stretch',
          }}>
            <div className="encounter-editor__column encounter-editor__column--identity" style={{ display: 'grid', gridTemplateRows: 'auto 1fr auto', gap: '14px', minHeight: '320px', padding: '14px', border: 'none', background: 'transparent' }}>
              <div ref={searchRef} style={{ position: 'relative' }}>
                <input
                  type="text"
                  placeholder="Encounter"
                  value={searchQuery}
                  onChange={(e) => {
                    setSearchQuery(e.target.value)
                    setEncounter(null)
                    setEncounterDetails(null)
                    setAbility('')
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
                    border: '1px solid var(--border-strong)',
                    background: 'var(--surface-deep)',
                    color: 'var(--text-secondary)',
                    padding: '0 12px',
                    fontSize: '0.9em',
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
                    background: 'var(--surface-mid)',
                    border: '1px solid var(--border-strong)',
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
                          borderBottom: '1px solid var(--border-strong)',
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

              <div className="encounter-editor__sprite-card" style={{
                position: 'relative',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                border: '1px solid var(--border-strong)',
                borderRadius: '12px',
                background: 'var(--surface-mid)',
                aspectRatio: '1 / 1',
                overflow: 'hidden',
              }}>
                <div style={{ position: 'absolute', top: '8px', left: '44px', right: '44px', height: '28px', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1 }}>
                  <TypeIconRow types={[type1, type2]} height={22} gap={8} placeholder justifyContent="center" />
                </div>
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
                    border: '1px solid var(--border-strong)',
                    borderRadius: '8px',
                    background: 'var(--surface-deep)',
                    color: isShiny ? '#f4d35e' : 'var(--text-secondary)',
                    cursor: 'pointer',
                    fontSize: '0.9em',
                    lineHeight: 1
                  }}
                >
                  ★
                </button>
                {encounterDetails?.has_gender === 'true' && (
                  <button
                    type="button"
                    onClick={() => {
                      if (encounterDetails?.one_gender === 'true') return
                      setGender(g => g === 'female' ? 'male' : 'female')
                    }}
                    title={encounterDetails?.one_gender === 'true' ? `Always ${gender}` : `Toggle gender`}
                    style={{
                      position: 'absolute',
                      top: '8px',
                      right: '8px',
                      width: '28px',
                      height: '28px',
                      border: '1px solid var(--border-strong)',
                      borderRadius: '8px',
                      background: 'var(--surface-deep)',
                      color: gender === 'female' ? '#e84d8a' : '#4d8fe8',
                      cursor: encounterDetails?.one_gender === 'true' ? 'default' : 'pointer',
                      fontSize: '1em',
                      lineHeight: 1,
                    }}
                  >
                    {gender === 'female' ? '♀' : '♂'}
                  </button>
                )}
                {encounter?.species_id ? (
                  <Sprite speciesId={encounter.species_id} size={200} shiny={isShiny} female={gender === 'female' && encounterDetails?.has_female === 'true'} style={status === 'Dead' ? { filter: 'grayscale(1)', opacity: 0.5 } : status === 'Missed' ? { opacity: 0.4 } : undefined} />
                ) : (
                  <img
                    src="/sprites/Standard/substitute.png"
                    width="160"
                    height="160"
                    alt="No encounter"
                    style={{ imageRendering: 'pixelated', objectFit: 'contain', opacity: 0.78 }}
                  />
                )}

                {(() => {
                  const raw = savedEncounter?.badges_earned
                  if (!raw) return null
                  let ids = []
                  if (Array.isArray(raw)) {
                    ids = raw.map(Number).filter(Number.isFinite)
                  } else if (typeof raw === 'string' && raw.trim()) {
                    try {
                      const p = JSON.parse(raw)
                      if (Array.isArray(p)) ids = p.map(Number).filter(Number.isFinite)
                    } catch {
                      ids = raw.split(',').map(s => Number(s.trim())).filter(Number.isFinite)
                    }
                  }
                  if (ids.length === 0) return null
                  return (
                    <div style={{ position: 'absolute', bottom: '8px', left: 0, right: 0, display: 'flex', flexWrap: 'wrap', gap: '4px', justifyContent: 'center', padding: '0 8px' }}>
                      {ids.map(id => (
                        <img
                          key={id}
                          src={`/sprites/Badges/${id}.png`}
                          alt={`Badge ${id}`}
                          title={`Badge ${id}`}
                          style={{ width: '28px', height: '28px', imageRendering: 'pixelated' }}
                          onError={e => { e.currentTarget.style.display = 'none' }}
                        />
                      ))}
                    </div>
                  )
                })()}
              </div>

              {forms.length > 0 && (
                <div style={{
                  display: 'flex',
                  gap: '6px',
                  justifyContent: 'center',
                  overflowX: forms.length > 4 ? 'auto' : 'visible',
                  padding: '4px 2px',
                }}>
                  {forms.map(form => {
                    const isCurrent = form.species_id === encounter?.species_id
                    return (
                      <button
                        key={form.species_id}
                        type="button"
                        onClick={() => !isCurrent && handleFormSelect(form)}
                        title={form.name}
                        style={{
                          flexShrink: 0,
                          width: '44px',
                          height: '44px',
                          border: isCurrent ? '1px solid var(--accent)' : '1px solid var(--border-strong)',
                          borderRadius: '8px',
                          background: isCurrent ? 'var(--accent-bg)' : 'var(--surface-deep)',
                          cursor: isCurrent ? 'default' : 'pointer',
                          padding: 0,
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                        }}
                      >
                        <Sprite speciesId={form.species_id} size={32} />
                      </button>
                    )
                  })}
                </div>
              )}

            </div>

            <div className="encounter-editor__column encounter-editor__column--stats" style={{ display: 'grid', gridTemplateRows: 'auto auto 1fr', gap: '14px', minHeight: '320px', padding: '14px', border: 'none', background: 'transparent' }}>
              <div ref={natureRef} style={{ position: 'relative' }}>
                <button
                  type="button"
                  onClick={() => setShowNature(current => !current)}
                  style={{
                    width: '100%',
                    height: '40px',
                    boxSizing: 'border-box',
                    borderRadius: '10px',
                    border: '1px solid var(--border-strong)',
                    background: 'var(--surface-deep)',
                    color: 'var(--text-secondary)',
                    padding: '0 12px',
                    fontSize: '0.9em',
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
                    background: 'var(--surface-mid)',
                    border: '1px solid var(--border-strong)',
                    borderRadius: '10px',
                    maxHeight: '220px',
                    overflowY: 'auto'
                  }}>
                    <div
                      onClick={() => { setNature(''); setShowNature(false) }}
                      style={{ padding: '8px 12px', cursor: 'pointer', borderBottom: '1px solid var(--border-strong)', color: 'var(--text-secondary)', fontSize: '0.85em' }}
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
                          borderBottom: '1px solid var(--border-strong)',
                          backgroundColor: nature === entry.name ? 'var(--border-strong)' : 'transparent'
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

              <div style={{ border: '1px solid var(--border-strong)', borderRadius: '12px', background: 'var(--surface-mid)', padding: '14px' }}>
                <div style={{ display: 'grid', gridTemplateColumns: '60px 30px 1fr', gap: '8px', alignItems: 'center', paddingBottom: '8px', marginBottom: '10px', borderBottom: '1px solid var(--border-strong)' }}>
                  <span style={{ fontSize: '0.85em', fontWeight: 'bold', color: 'var(--text-secondary)' }}>BST</span>
                  <span style={{ fontSize: '0.85em', fontWeight: 'bold', color: 'var(--text-secondary)', textAlign: 'right', whiteSpace: 'nowrap' }}>{encounterDetails?.bst ?? '—'}</span>
                  <span />
                </div>
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
                          <span style={{ width: '28px', fontSize: '0.72em', color: 'var(--text-secondary)', textAlign: 'left' }}>{stat.label}</span>
                          <span style={{ width: '38px', fontSize: '0.72em', color: natureModifier?.color || 'transparent', textAlign: 'left' }}>
                            {natureModifier?.text || '+10%'}
                          </span>
                        </span>
                        <span style={{ fontSize: '0.75em', color: 'var(--text-secondary)', textAlign: 'right', whiteSpace: 'nowrap' }}>{value ?? '—'}</span>
                        <div style={{ position: 'relative', height: '8px', background: 'var(--surface-mid)', borderRadius: '999px', overflow: 'hidden' }}>
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
            </div>

            <div className="encounter-editor__column encounter-editor__column--details" style={{ display: 'grid', gridTemplateRows: 'auto auto auto 1fr', gap: '14px', minHeight: '320px', padding: '14px', border: 'none', background: 'transparent' }}>
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
                  border: '1px solid var(--border-strong)',
                  background: 'var(--surface-deep)',
                  color: 'var(--text-secondary)',
                  padding: '0 12px',
                  fontSize: '0.9em',
                }}
              />


              {(isSavingEncounter || encounterSaveError) && (
                <div
                  role={encounterSaveError ? 'alert' : 'status'}
                  style={{
                    minHeight: '18px',
                    color: encounterSaveError ? '#e05252' : 'var(--text-secondary)',
                    fontSize: '0.78em',
                  }}
                >
                  {encounterSaveError || 'Saving encounter...'}
                </div>
              )}

              <div style={{ border: '1px solid var(--border-strong)', borderRadius: '12px', background: 'var(--surface-mid)', padding: '14px' }}>
                <div style={{ fontSize: '0.85em', fontWeight: 'bold', color: 'var(--text-secondary)', paddingBottom: '8px', marginBottom: '10px', borderBottom: '1px solid var(--border-strong)' }}>
                  Known Abilities
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                  {/* vg-aware options only: the generation-only species summary
                      would show vanilla abilities on a hack run. Rows are the
                      picker: press one to record it, press again to unset. */}
                  {(() => {
                    const entries = [...abilityOptions]
                    if (ability && !entries.some(option => option.name === ability)) {
                      entries.push({ name: ability, hidden: false })
                    }
                    if (!entries.length) {
                      return <span style={{ fontSize: '0.8em', color: 'var(--text-secondary)' }}>—</span>
                    }
                    const clickable = status === 'Captured'
                    return entries.map(option => {
                      const chosen = ability && option.name === ability
                      return (
                        <button
                          key={option.name}
                          type="button"
                          disabled={!clickable || isSavingEncounter}
                          onClick={() => handleSelectAbility(chosen ? '' : option.name)}
                          title={clickable ? (chosen ? 'Press to unset' : 'Press to record this ability') : undefined}
                          style={{
                            textAlign: 'left',
                            font: 'inherit',
                            fontSize: '0.8em',
                            padding: '7px 10px',
                            borderRadius: '8px',
                            border: chosen ? '1px solid #52c97a' : '1px solid var(--border-strong)',
                            background: chosen ? 'rgba(82,201,122,0.12)' : 'var(--surface-deep)',
                            color: chosen ? '#52c97a' : 'var(--text-secondary)',
                            fontWeight: chosen ? 'bold' : 'normal',
                            fontStyle: option.hidden ? 'italic' : 'normal',
                            cursor: clickable && !isSavingEncounter ? 'pointer' : 'default',
                            opacity: clickable ? 1 : 0.75,
                          }}
                        >
                          {formatAbility(option.name)}{option.hidden ? ' (Hidden)' : ''}{chosen ? ' ✓' : ''}
                        </button>
                      )
                    })
                  })()}
                </div>
              </div>

              <div className="encounter-editor__actions" style={{ display: 'flex', alignItems: 'flex-end' }}>
                {renderEncounterActions('panel')}
              </div>
            </div>
          </div>
        </div>
      )}

      {showTrainerView && activePanel === 'trainers' && (
        <div className="location-row__panel location-row__panel--trainers" style={{ ...PANEL_STYLE, background: 'var(--surface)', marginTop: '10px', padding: '16px' }}>
          <label style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.78em', color: 'var(--text-secondary)', marginBottom: '10px', cursor: 'pointer' }}>
            <input
              type="checkbox"
              checked={showSpecialTrainers}
              onChange={event => {
                setShowSpecialTrainers(event.target.checked)
                setTrainersLoaded(false)
              }}
            />
            Show rematches &amp; special battles
          </label>
          {!trainersLoaded ? (
            <div style={{ color: 'var(--text-secondary)', fontSize: '0.85em' }}>Loading trainers...</div>
          ) : availableTrainers.length === 0 && specialTrainers.length === 0 ? (
            <div style={{ color: 'var(--text-secondary)', fontSize: '0.85em' }}>No trainers at this location.</div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: hasNamedAreas || specialGroups.length ? '14px' : '8px' }}>
              {[...trainerGroups, ...specialGroups].map(group => (
                <div key={group.key ?? 'location'} style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                  {group.name && (
                    <div style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '8px',
                      fontSize: '0.72em',
                      letterSpacing: '0.08em',
                      textTransform: 'uppercase',
                      color: group.kind === 'gym' ? 'var(--accent)' : 'var(--text-secondary)',
                    }}>
                      <span>{group.name}</span>
                      <span style={{ flex: 1, height: '1px', background: 'var(--border-strong)' }} />
                      <span style={{ opacity: 0.7 }}>
                        {group.trainers.filter(t => t.is_defeated).length}/{group.trainers.length}
                      </span>
                    </div>
                  )}
                  {group.trainers.map(trainer => (
                    <TrainerCard
                      key={trainer.trainer_id}
                      encounterName={trainer.encounter_name}
                      trainerName={trainer.trainer_name}
                      trainerClass={trainer.trainer_class}
                      trainerPic={trainer.trainer_pic}
                      trainerItems={trainer.trainer_items}
                      gameId={gameId}
                      generation={generation}
                      versionGroupId={trainer.version_group_id}
                      runId={runId}
                      attemptId={attemptNumber}
                      trainerId={trainer.trainer_id}
                      enableBattle
                      isDefeated={Boolean(trainer.is_defeated)}
                      onVictoryRecorded={() => handleTrainerVictoryRecorded(trainer.trainer_id)}
                      attemptEnded={attemptEnded}
                      battleType={Number(trainer.is_double) ? 'double' : null}
                    />
                  ))}
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default LocationRow
