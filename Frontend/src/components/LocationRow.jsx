import { useEffect, useMemo, useRef, useState } from 'react'
import { apiFetch } from '../utils/api'
import { useEditMode } from '../contexts/EditModeContext'
import { moveBy, moveRelative, reorderWithinGroup, sameOrder } from '../utils/trainerOrder'
import { resolveEvolvedAbility } from '../utils/evolveAbility'
import Sprite from './Sprite'
import { IV_MIN, IV_MAX, emptyIvs, normalizeIvs } from '../utils/pokemonFormat'
import TrainerCard from './TrainerCard'
import { TypeIconRow } from './TypeIcon'
import EncounterTables from './EncounterTables'
import MethodIcon from './MethodIcon'
import { buildEncounterView, conditionLabel, methodMeta, rememberSeason, rememberedSeason, slotKey } from '../utils/encounterTables'
import { lockedTrainerCount, splitPhrase, tableAvailability } from '../utils/splitFeed'
import OpensInPicker from './OpensInPicker'
import { Button, MenuItem } from './Button'
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

const EMPTY_TABLES = []
const EMPTY_METHODS = []

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

const ROW_ACTION_GROUP_STYLE = {
  display: 'grid',
  gridTemplateColumns: 'repeat(3, minmax(0, 1fr))',
  gap: '8px',
  width: '312px',
  maxWidth: '100%',
  marginLeft: 'auto',
}

// Label, base value, bar, IV entry.
const STAT_GRID_COLUMNS = '60px 30px 1fr 54px'

const IV_INPUT_STYLE = {
  width: '100%',
  height: '30px',
  boxSizing: 'border-box',
  padding: '0 4px',
  border: '1px solid var(--border-strong)',
  borderRadius: '8px',
  background: 'var(--surface-deep)',
  color: 'var(--text-primary)',
  font: 'inherit',
  fontSize: '0.8em',
  textAlign: 'center',
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


const EMPTY_INDEX = new Map()
const EMPTY_GATES = []
const NO_SPLITS = []

function LocationRow({ row, savedEncounter, runId, attemptNumber, gameId = null, generation = null, pool = [], poolTables = EMPTY_TABLES, encounterMethods = EMPTY_METHODS, season: seasonProp = null, onSeasonChange: onSeasonChangeProp = null, allSpecies = [], dupedFamilyIds = new Set(), onEncounterChange, onStatusChange, onPartyChange, onStructureChange, partyPokemonIds = new Set(), onVictoryRecorded = null, viewMode = 'master', attemptEnded = false,
  // Split layout (Blaze Black): the split index and the run's current
  // split ordinal decide what is reachable; a jump from a split's returns
  // list arrives as openRequest; admins get the Opens-in controls.
  splitLayout = false, splitIndex = EMPTY_INDEX, currentOrdinal = Number.POSITIVE_INFINITY, splits = NO_SPLITS, gates = EMPTY_GATES, openRequest = null, onAvailabilityChange = null }) {
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
  // Admin reorder, shown while the header's edit mode is on: a drag from a
  // card's handle
  // can only land on a sibling in the same group (area) of this location.
  // The drag source lives in a ref so dragstart never re-renders the
  // element being dragged, which would cancel the drag.
  const { editMode } = useEditMode()
  const draggingRef = useRef(null)
  const [draggingId, setDraggingId] = useState(null)
  const [dropTarget, setDropTarget] = useState(null)
  const [reorderSaving, setReorderSaving] = useState(false)
  const [reorderError, setReorderError] = useState('')
  // A venue whose whole roster is rematch/event trainers (stadiums, the
  // cruise, League rematches) opens straight onto its special groups
  // instead of an empty "No trainers" state.
  const [showSpecialTrainers, setShowSpecialTrainers] = useState(
    Number(row.trainer_count ?? 0) === 0 && Number(row.special_trainer_count ?? 0) > 0)

  const [encounter, setEncounter] = useState(null)
  // The encounter tables (blank state): the slot a species was claimed
  // from (UI-only until Phase 4 persists it), the area tab and the season.
  const [claimedSlot, setClaimedSlot] = useState(null)
  // Option A flow: a tap on the tables only SELECTS a slot; the confirm bar
  // turns the selection into a Caught or Missed encounter.
  const [selectedSlot, setSelectedSlot] = useState(null)
  const [tablesArea, setTablesArea] = useState(null)
  // The season is one per run: Attempt owns it and passes it down so every
  // row agrees. A row rendered on its own keeps (and remembers) its own.
  const [localSeason, setLocalSeason] = useState(() => (seasonProp ? null : rememberedSeason(runId)))
  const tablesSeason = seasonProp ?? localSeason
  // Retyping the species in the editor keeps the editor mounted (and the
  // input focused) even while no species is chosen; the player goes back
  // to the tables with 'Back to tables' or Change.
  const [keepEditor, setKeepEditor] = useState(false)
  const encounterView = useMemo(() => buildEncounterView(poolTables, encounterMethods), [poolTables, encounterMethods])
  const hasTables = encounterView.tables.length > 0 || encounterView.rare.length > 0
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
  const [ivs, setIvs] = useState(emptyIvs)
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

  // A jump from a later split's returns list: which split's content is new
  // here (badged NEW / highlighted) and the method tab to land on.
  const [focusSplitKey, setFocusSplitKey] = useState(null)
  const [tablesFocus, setTablesFocus] = useState(null)
  const [highlightTrainerIds, setHighlightTrainerIds] = useState(new Set())
  useEffect(() => {
    if (!openRequest?.nonce) return
    setActivePanel(openRequest.panel === 'trainers' ? 'trainers' : 'encounter')
    setFocusSplitKey(openRequest.splitKey || null)
    setTablesFocus(openRequest.panel === 'encounter' ? { nonce: openRequest.nonce, methods: openRequest.methods || [], areas: openRequest.areas || [] } : null)
    setHighlightTrainerIds(new Set((openRequest.trainerIds || []).map(Number)))
  }, [openRequest?.nonce]) // eslint-disable-line react-hooks/exhaustive-deps

  const homeSplit = splitLayout ? splitIndex.get(row.home_split) || null : null
  const homeOrdinal = homeSplit ? homeSplit.ordinal : 0
  const availabilityOf = splitLayout ? (entry => tableAvailability(entry, splitIndex, currentOrdinal)) : null
  const trainerSplitOf = trainer => (splitLayout && trainer?.opens_in ? splitIndex.get(trainer.opens_in) || null : null)
  const trainerLocked = trainer => {
    const split = trainerSplitOf(trainer)
    return Boolean(split) && split.ordinal > currentOrdinal
  }

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
    // Only a row the server knows hydrates the editor: Attempt also holds
    // optimistic {species_id, status} entries with no pokemon behind them.
    if (!savedEncounter?.pokemon_id) return
    skipNextEncounterSaveRef.current = true
    setEncounter({ species_id: savedEncounter.species_id, name: savedEncounter.species_name })
    setSearchQuery(savedEncounter.species_name || '')
    pokemonIdRef.current = savedEncounter.pokemon_id || null
    setPokemonId(savedEncounter.pokemon_id || null)
    setNickname(savedEncounter.nickname || '')
    setNature(savedEncounter.nature || '')
    setStatus(savedEncounter.status || '')
    setAbility(savedEncounter.ability || '')
    setIvs(normalizeIvs(savedEncounter.ivs))
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
        normalizeIvs(ivs),
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
  }, [encounter, nickname, nature, status, isShiny, gender, ability, ivs, saveNonce, runId, attemptNumber, row.event_id, row.secondary_sort_order, onEncounterChange, onPartyChange])

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
  // order here is the display order. In the split layout, trainers that
  // open in a later split than this row's home leave their area group for
  // a "New in <leader>'s split" group at the end, one per split.
  const trainerGroups = useMemo(() => {
    const groups = []
    const byArea = new Map()
    const bySplit = new Map()
    for (const trainer of availableTrainers) {
      const later = trainerSplitOf(trainer)
      if (later && later.ordinal > homeOrdinal) {
        if (!bySplit.has(later.split_key)) {
          bySplit.set(later.split_key, { key: `split:${later.split_key}`, name: `New in ${splitPhrase(later)}`, kind: null, split: later, later: true, trainers: [] })
        }
        bySplit.get(later.split_key).trainers.push(trainer)
        continue
      }
      const key = trainer.area_id ?? null
      if (!byArea.has(key)) {
        const group = { key, name: trainer.area_name || null, kind: trainer.area_kind || null, trainers: [] }
        byArea.set(key, group)
        groups.push(group)
      }
      byArea.get(key).trainers.push(trainer)
    }
    return [...groups, ...[...bySplit.values()].sort((a, b) => a.split.ordinal - b.split.ordinal)]
  }, [availableTrainers, splitLayout, splitIndex, homeOrdinal]) // eslint-disable-line react-hooks/exhaustive-deps
  const hasNamedAreas = trainerGroups.some(g => g.name)
  const specialGroups = useMemo(() => {
    const rematches = specialTrainers.filter(t => t.is_rematch)
    const events = specialTrainers.filter(t => t.is_event && !t.is_rematch)
    const groups = []
    if (rematches.length) groups.push({ key: 'rematches', name: 'Rematches', trainers: rematches, special: true })
    if (events.length) groups.push({ key: 'events', name: 'Special Battles', trainers: events, special: true })
    return groups
  }, [specialTrainers])
  // Use the loaded value if trainers are loaded, otherwise use the seed value from row.
  // The pill counts only trainers reachable so far; ones locked behind a
  // later split are left out until it opens.
  const defeatedTrainerCount = trainersLoaded
    ? availableTrainers.filter(t => Boolean(t.is_defeated)).length
    : Number(row.trainer_count ?? 0) - Number(row.available_trainer_count ?? 0)
  const hasSeedTrainerCount = row.trainer_count != null
  const initialTrainerCount = Number(row.trainer_count ?? 0)
  const initialSpecialCount = Number(row.special_trainer_count ?? 0)
  const lockedCount = splitLayout
    ? (trainersLoaded ? availableTrainers.filter(trainerLocked).length : lockedTrainerCount(row, splitIndex, currentOrdinal))
    : 0
  const trainerCount = Math.max(0, (trainersLoaded ? availableTrainers.length : initialTrainerCount) - lockedCount)
  // Allow first load only when trainer counts are unknown; honor explicit zero
  // counts. A location whose roster is all rematch/event trainers (stadiums,
  // the cruise, League rematches) still opens its panel for the special groups.
  const trainerButtonDisabled = trainersLoaded
    ? (availableTrainers.length === 0 && specialTrainers.length === 0 && initialSpecialCount === 0)
    : (hasSeedTrainerCount && initialTrainerCount === 0 && initialSpecialCount === 0)
  const inParty = pokemonId ? partyPokemonIds.has(pokemonId) : false
  const summaryName = nickname || encounter?.name || (hasTables ? 'Choose encounter' : 'Log encounter')
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

  useEffect(() => {
    if (activePanel !== 'encounter') {
      setKeepEditor(false)
      // nothing was saved by a selection, so closing the panel drops it
      setSelectedSlot(null)
    }
  }, [activePanel])

  // A status chosen for a pick the server never stored (the create failed):
  // drop it, invalidate the pending save, and roll back Attempt's
  // optimistic entry, so no later pick inherits it.
  const discardUnsavedStatus = () => {
    if (pokemonIdRef.current || !status) return
    encounterSaveSequenceRef.current += 1
    if (encounter?.species_id && onStatusChange) {
      onStatusChange(row.encounter_key, encounter.species_id, '')
    }
    setStatus('')
    setEncounterSaveError('')
    setIsSavingEncounter(false)
  }

  // Everything entered for an unsaved pick, back to blank.
  const resetDraft = () => {
    setEncounter(null)
    setEncounterDetails(null)
    setSearchQuery('')
    setSearchResults(pool)
    setShowSearch(false)
    setNickname('')
    setNature('')
    setAbility('')
    setIsShiny(false)
    setGender('male')
    setIvs(emptyIvs())
    setForms([])
    setClaimedSlot(null)
    setKeepEditor(false)
    setEncounterSaveError('')
  }

  const handleClear = () => {
    // Invalidate any in-flight save so a pending create cannot resurrect
    // the row after it was cleared. Its finally block will now skip the
    // saving flag, so clear it here or the row stays locked.
    encounterSaveSequenceRef.current += 1
    setIsSavingEncounter(false)
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
    resetDraft()
    pokemonIdRef.current = null
    setPokemonId(null)
    setStatus('')
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
    // The summary row's actions are the default size; the open card's are
    // the large confirm size.
    const size = compact ? 'md' : 'lg'

    if (!encounter?.species_id) {
      // Also covers a status-bearing row mid species-edit: no live buttons
      // may act on a species that is no longer selected. The summary row
      // stays quiet; the decision lives inside the encounter card.
      if (compact) return null
      return (
        <div className={`encounter-actions encounter-actions--${variant}`} style={{ ...groupStyle, gridTemplateColumns: 'repeat(2, minmax(0, 1fr))' }}>
          <Button size={size} tone="success" disabled title="Pick a species first">Caught</Button>
          <Button size={size} tone="warning" disabled title="Pick a species first">Missed</Button>
        </div>
      )
    }

    if (status && !pokemonId) {
      // The status was chosen but the row hasn't been created server-side
      // (save in flight, or it failed): offer retry instead of dead buttons.
      return (
        <div className={`encounter-actions encounter-actions--${variant}`} style={{ ...groupStyle, gridTemplateColumns: 'repeat(2, minmax(0, 1fr))' }}>
          {isSavingEncounter ? (
            <Button size={size} disabled style={{ gridColumn: '1 / -1', width: '100%' }}>Saving...</Button>
          ) : (
            <>
              <Button size={size} tone="danger" onClick={requestImmediateSave}>Retry Save</Button>
              <Button size={size} onClick={claimedSlot ? handleUndoDecision : handleClear} title="Discard this encounter">Cancel</Button>
            </>
          )}
        </div>
      )
    }

    if (status === 'Dead') {
      return (
        <div className={`encounter-actions encounter-actions--${variant}`} style={{ ...groupStyle, gridTemplateColumns: compact ? groupStyle.gridTemplateColumns : '1fr' }}>
          <Button size={size} tone="warning" disabled={isSavingEncounter || !pokemonId} onClick={handleRevive} style={{ gridColumn: '1 / -1', minWidth: 0, width: '100%' }}>
            Revive
          </Button>
        </div>
      )
    }
    if (status === 'Captured') {
      return (
        <div className={`encounter-actions encounter-actions--${variant}`} style={groupStyle}>
          <Button size={size} tone={inParty ? 'info' : 'success'} disabled={isSavingEncounter || !pokemonId} onClick={handlePartyToggle}>
            {compact ? `Party ${inParty ? '-' : '+'}` : (inParty ? 'Party -' : 'Party')}
          </Button>
          <Button size={size} tone="danger" disabled={isSavingEncounter || !pokemonId} onClick={handleDeath}>Dead</Button>
          <Button size={size} tone="accent" disabled={isSavingEncounter || !pokemonId || !hasEvolutions} onClick={() => setShowEvolve(true)}>Evolve</Button>
        </div>
      )
    }
    if (status === 'Missed') {
      return (
        <div className={`encounter-actions encounter-actions--${variant}`} style={groupStyle}>
          {/* A status, not an action: the dashed chip says what was logged. */}
          <div className="encounter-actions__status" style={{ minHeight: compact ? '36px' : '44px', display: 'inline-flex', alignItems: 'center', justifyContent: 'center', padding: '0 10px', fontSize: compact ? '0.82rem' : '0.9rem', color: 'var(--warning)', border: '1px dashed var(--warning)', borderRadius: '999px', background: 'color-mix(in srgb, var(--warning) 8%, transparent)', boxSizing: 'border-box' }}>
            Missed
          </div>
          <Button size={size} tone="success" disabled={isSavingEncounter} onClick={handleCatch}>Caught</Button>
          <Button size={size} disabled={isSavingEncounter} onClick={claimedSlot ? handleUndoDecision : handleClear} title="Undo: clear this encounter">Undo</Button>
        </div>
      )
    }
    // No status yet: the two decisions that start an encounter's story,
    // offered only inside the encounter card.
    if (compact) return null
    return (
      <div className={`encounter-actions encounter-actions--${variant}`} style={{ ...groupStyle, gridTemplateColumns: 'repeat(2, minmax(0, 1fr))' }}>
        <Button size={size} tone="success" disabled={isSavingEncounter} onClick={handleCatch}>Caught</Button>
        <Button size={size} tone="warning" disabled={isSavingEncounter} onClick={handleMiss}>Missed</Button>
      </div>
    )
  }

  // An ability belongs to one species: every species change clears it
  // rather than silently carrying it onto a Pokemon that cannot have it.
  const handleEncounterSelect = (species) => {
    // A different species never inherits a status that failed to save.
    if (species.species_id !== encounter?.species_id) discardUnsavedStatus()
    setEncounter(species)
    setAbility('')
    setSearchQuery(species.name)
    setShowSearch(false)
    setActivePanel('encounter')
    setClaimedSlot(null)
    setKeepEditor(false)
  }

  // A tap on a table row, a static, a plain-pool row or a search result
  // selects it; a second tap on the same entry clears the selection.
  const handleSelectSlot = (slot) => {
    if (attemptEnded || !slot?.species_id) return
    // A table that has not opened yet cannot take the location's one
    // encounter; searched species carry no table and are never blocked.
    if (availabilityOf && slot.source !== 'search' && availabilityOf(slot).state !== 'open') return
    setSelectedSlot(current => (current && slotKey(current) === slotKey(slot) ? null : slot))
  }

  // Admin Opens-in controls (edit mode, split layout only).
  const renderOpensIn = (kind, key, label, current, inheritedLabel, align = 'left') => (
    <OpensInPicker
      gameId={gameId}
      subjectKind={kind}
      subjectKey={key}
      subjectLabel={label}
      current={current || {}}
      inheritedLabel={inheritedLabel}
      splits={splits}
      gates={gates}
      index={splitIndex}
      onSaved={onAvailabilityChange}
      align={align}
    />
  )
  const showOpensIn = splitLayout && editMode && gameId != null && !row.is_bonus_location
  const areaAvailability = area => (row.areas || []).find(a => a.area === area) || null

  // The confirm bar: the selection becomes the encounter and is saved at
  // once with the chosen status, like the Caught / Missed buttons today.
  // The stat screen (nickname, nature, IVs) opens after.
  const handleConfirmEncounter = (nextStatus) => {
    const slot = selectedSlot
    if (attemptEnded || !slot?.species_id) return
    setEncounter({ species_id: slot.species_id, name: slot.name })
    setAbility('')
    setSearchQuery(slot.name)
    setShowSearch(false)
    setClaimedSlot(slot)
    setKeepEditor(false)
    setSelectedSlot(null)
    setActivePanel('encounter')
    saveStatusImmediatelyRef.current = true
    setStatus(nextStatus)
    if (onStatusChange) onStatusChange(row.encounter_key, slot.species_id, nextStatus)
  }

  // Undo a decision made from the tables: the encounter is cleared (and
  // deleted if it saved) and the tables come back with the pick selected.
  const handleUndoDecision = () => {
    const slot = claimedSlot
    handleClear()
    setActivePanel('encounter')
    if (slot) setSelectedSlot(slot)
  }

  // Back to the tables from an unsaved pick: the pick is discarded whole
  // (nickname, nature, shiny, IVs), not carried onto the next species.
  const handleChangeEncounter = () => {
    discardUnsavedStatus()
    resetDraft()
  }

  const handleSeasonChange = (season) => {
    if (onSeasonChangeProp) {
      onSeasonChangeProp(season)
      return
    }
    setLocalSeason(season)
    rememberSeason(runId, season)
  }

  // The ability follows its slot onto the evolved species; it resolves
  // before any state changes so the auto-save fires once, not twice.
  const handleEvolveSelect = async (evo) => {
    const nextAbility = await resolveEvolvedAbility(ability, encounter?.species_id, evo.to_species_id, gameId)
    setEncounter({ species_id: evo.to_species_id, name: evo.name })
    setAbility(nextAbility)
    setSearchQuery(evo.name)
    setShowEvolve(false)
    setEvolutions(null)
  }

  const handleFormSelect = (form) => {
    setEncounter({ species_id: form.species_id, name: form.name })
    setAbility('')
    setSearchQuery(form.name)
  }

  const isGroupMember = (groupKey) => (trainer) => (
    !trainer.is_event && !trainer.is_rematch && (trainer.area_id ?? null) === groupKey
  )

  // One save at a time: the controls stay off while a POST is pending, so
  // two optimistic orders can never race each other or the server. A
  // failed save reloads the list rather than guessing the server's state.
  const commitTrainerOrder = (group, orderedIds) => {
    if (reorderSaving) return
    const currentIds = group.trainers.map(t => t.trainer_id)
    if (sameOrder(currentIds, orderedIds)) return
    setReorderError('')
    setReorderSaving(true)
    setTrainers(prev => reorderWithinGroup(prev, isGroupMember(group.key), orderedIds))
    apiFetch('/api/admin/trainer-order', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ trainer_ids: orderedIds }),
    })
      .then(async res => {
        const data = await res.json().catch(() => ({}))
        if (!res.ok) throw new Error(data.error || `Reorder failed (${res.status})`)
      })
      .catch(err => {
        console.error('Failed to save trainer order:', err)
        setReorderError(err.message || 'Reorder failed')
        setTrainersLoaded(false)
      })
      .finally(() => setReorderSaving(false))
  }

  const reorderControlsFor = (group, index) => {
    const ids = group.trainers.map(t => t.trainer_id)
    const trainerId = ids[index]
    return {
      saving: reorderSaving,
      canMoveUp: index > 0 && !reorderSaving,
      canMoveDown: index < ids.length - 1 && !reorderSaving,
      onMoveUp: () => commitTrainerOrder(group, moveBy(ids, trainerId, -1)),
      onMoveDown: () => commitTrainerOrder(group, moveBy(ids, trainerId, 1)),
      onDragStart: (event, cardElement) => {
        if (reorderSaving) { event.preventDefault(); return }
        event.dataTransfer.effectAllowed = 'move'
        try { event.dataTransfer.setData('text/plain', String(trainerId)) } catch { /* not every engine allows this */ }
        if (cardElement && typeof event.dataTransfer.setDragImage === 'function') {
          const rect = cardElement.getBoundingClientRect()
          event.dataTransfer.setDragImage(cardElement, event.clientX - rect.left, event.clientY - rect.top)
        }
        draggingRef.current = { trainerId, groupKey: group.key }
        setTimeout(() => setDraggingId(trainerId), 0)
      },
      onDragEnd: () => {
        draggingRef.current = null
        setDraggingId(null)
        setDropTarget(null)
      },
    }
  }

  const dropPosition = (event) => {
    const rect = event.currentTarget.getBoundingClientRect()
    return event.clientY < rect.top + rect.height / 2 ? 'before' : 'after'
  }

  const slotDragHandlers = (group, trainer) => {
    const trainerId = trainer.trainer_id
    const activeDrag = () => {
      const drag = draggingRef.current
      return drag && drag.groupKey === group.key && drag.trainerId !== trainerId ? drag : null
    }
    return {
      onDragOver: (event) => {
        if (!activeDrag()) return
        event.preventDefault()
        event.dataTransfer.dropEffect = 'move'
        const position = dropPosition(event)
        setDropTarget(prev => (prev?.trainerId === trainerId && prev.position === position ? prev : { trainerId, position }))
      },
      onDragLeave: (event) => {
        if (event.currentTarget.contains(event.relatedTarget)) return
        setDropTarget(prev => (prev?.trainerId === trainerId ? null : prev))
      },
      onDrop: (event) => {
        const drag = activeDrag()
        if (!drag) return
        event.preventDefault()
        const ids = group.trainers.map(t => t.trainer_id)
        commitTrainerOrder(group, moveRelative(ids, drag.trainerId, trainerId, dropPosition(event)))
        draggingRef.current = null
        setDraggingId(null)
        setDropTarget(null)
      },
    }
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

  // The blank state shows the tables; a chosen species, a stored row, or a
  // species being retyped in the editor shows the editor.
  const isStored = Boolean(pokemonId || savedEncounter?.pokemon_id)
  const panelMode = activePanel === 'encounter' && !encounter?.species_id && !isStored && !keepEditor ? 'tables' : 'editor'
  // Change / Back to tables: only for an undecided, unstored pick, and only
  // when the tables panel has something to go back to.
  const canReturnToTables = !status && !isStored && (hasTables || pool.length > 0)

  const renderSearchInput = (placeholder) => (
    <div ref={searchRef} style={{ position: 'relative' }}>
      <input
        type="text"
        placeholder={placeholder}
        autoComplete="off"
        autoCapitalize="none"
        autoCorrect="off"
        spellCheck={false}
        value={searchQuery}
        // A create in flight is about this species: hold the input until it lands.
        readOnly={isSavingEncounter && !pokemonId}
        onChange={(e) => {
          if (panelMode === 'editor') setKeepEditor(true)
          discardUnsavedStatus()
          setSearchQuery(e.target.value)
          setEncounter(null)
          setEncounterDetails(null)
          setAbility('')
          setClaimedSlot(null)
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
            <MenuItem
              key={species.species_id}
              onClick={() => {
                if (panelMode === 'tables') {
                  handleSelectSlot({ species_id: species.species_id, name: species.name, method: null, slot_kind: 'slot', source: 'search' })
                  setShowSearch(false)
                  return
                }
                handleEncounterSelect(species)
              }}
              style={dupedFamilyIds.has(species.species_id) && species.species_id !== savedEncounter?.species_id ? { opacity: 0.35 } : undefined}
            >
              <Sprite speciesId={species.species_id} size={26} useIcon />
              <span>{species.name}</span>
            </MenuItem>
          ))}
        </div>
      )}
    </div>
  )

  // Where the chosen species came from, until a save (Phase 4 persists it).
  const renderProvenance = () => {
    if (!encounter?.species_id) {
      if (!canReturnToTables || panelMode !== 'editor') return null
      return (
        <div className="encounter-provenance" style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap', marginTop: '8px', fontSize: '0.78em', color: 'var(--text-secondary)' }}>
          <span>No species chosen</span>
          <Button size="sm" onClick={handleChangeEncounter}>Back to tables</Button>
        </div>
      )
    }
    if (pokemonId && !claimedSlot) return null
    const meta = claimedSlot?.method ? methodMeta(encounterMethods, claimedSlot.method) : null
    const bits = meta
      ? [
          meta.label,
          claimedSlot.rate != null ? `${claimedSlot.rate}%` : (claimedSlot.slot_kind === 'static' ? 'Static' : null),
          claimedSlot.area,
          claimedSlot.condition ? conditionLabel(claimedSlot.condition) : null,
          claimedSlot.min_level != null ? `Lv ${claimedSlot.min_level}` : null,
        ].filter(Boolean)
      : [claimedSlot?.source === 'pool' ? 'Encounter list' : 'Searched']
    return (
      <div className="encounter-provenance" style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap', marginTop: '8px', fontSize: '0.78em', color: 'var(--text-secondary)' }}>
        {meta && <MethodIcon group={meta.group} rare={Boolean(meta.is_rare)} size={16} title={meta.label} />}
        <span>{bits.join(' · ')}</span>
        {canReturnToTables && (
          <Button size="sm" onClick={handleChangeEncounter}>Change</Button>
        )}
        {status === 'Captured' && claimedSlot && pokemonId && (
          <Button size="sm" onClick={handleUndoDecision} disabled={isSavingEncounter} title="Clear this encounter and pick again">Undo</Button>
        )}
      </div>
    )
  }

  // Bottom right of the tables: the selected species and the decision.
  const renderConfirmBar = () => {
    const slot = selectedSlot
    const meta = slot?.method ? methodMeta(encounterMethods, slot.method) : null
    const detail = !slot ? null : meta
      ? [
          meta.label,
          slot.rate != null ? `${slot.rate}%` : (slot.slot_kind === 'static' ? 'Static' : null),
          slot.area,
          slot.condition ? conditionLabel(slot.condition) : null,
          slot.min_level != null ? `Lv ${slot.min_level}` : null,
        ].filter(Boolean).join(' · ')
      : (slot.source === 'pool' ? 'Encounter list' : 'Searched')
    const disabled = !slot || attemptEnded
    return (
      <div className="encounter-confirm-dock" style={{ position: 'sticky', display: 'flex', justifyContent: 'flex-end', marginTop: '14px', zIndex: 2, pointerEvents: 'none' }}>
        <div
          className={`encounter-confirm${slot ? ' encounter-confirm--armed' : ''}`}
          role="group"
          aria-label="Confirm encounter"
          style={{
            pointerEvents: 'auto', display: 'flex', alignItems: 'center', flexWrap: 'wrap', justifyContent: 'flex-end', gap: '10px',
            padding: '8px 8px 8px 12px', borderRadius: '14px', background: 'var(--surface)',
            border: `1px solid ${slot ? 'var(--pick)' : 'var(--border-strong)'}`, boxShadow: '0 8px 24px rgba(0,0,0,0.35)',
          }}
        >
          {slot ? (
            <span className="encounter-confirm__pick" style={{ display: 'flex', alignItems: 'center', gap: '8px', minWidth: 0 }}>
              <Sprite speciesId={slot.species_id} size={30} useIcon />
              <span style={{ display: 'grid', minWidth: 0 }}>
                <b style={{ fontSize: '0.92em' }}>{slot.name}</b>
                <small style={{ fontSize: '0.76em', color: 'var(--text-secondary)' }}>{detail}</small>
              </span>
            </span>
          ) : (
            <span className="encounter-confirm__prompt" style={{ fontSize: '0.85em', color: 'var(--text-secondary)' }}>
              {attemptEnded ? 'This attempt has ended' : 'Tap a Pokémon to select it'}
            </span>
          )}
          <Button tone="warning" size="lg" className="encounter-confirm__missed" disabled={disabled} onClick={() => handleConfirmEncounter('Missed')} style={{ minWidth: '104px' }}>
            Missed
          </Button>
          <Button tone="success" size="lg" className="encounter-confirm__caught" disabled={disabled} onClick={() => handleConfirmEncounter('Captured')} style={{ minWidth: '104px' }}>
            Caught
          </Button>
        </div>
      </div>
    )
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
    <div id={`location-${row.encounter_key}`} className="location-row" style={{ marginBottom: '14px' }}>
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
                  <Button key={evo.to_species_id} tone="accent" size="lg" block onClick={() => handleEvolveSelect(evo)} style={{ gap: '10px', minHeight: '56px' }}>
                    <Sprite speciesId={evo.to_species_id} size={48} />
                    {evo.name}
                  </Button>
                ))}
              </div>
            )}
            <Button onClick={() => setShowEvolve(false)} style={{ marginTop: '20px' }}>Cancel</Button>
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
        <div className="location-row__name" style={{ minWidth: 0, flex: '0 1 220px', display: 'flex', flexDirection: 'column', gap: '4px' }}>
          {renderLocationCell()}
          {showOpensIn && renderOpensIn('location', String(row.event_id), row.display_name, row, 'story order')}
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

            <Button className="location-row__encounter-button" align="start" selected={activePanel === 'encounter'} onClick={() => togglePanel('encounter')} style={{ flex: '0 1 240px', width: '240px', minWidth: 0, color: 'var(--text-primary)' }}>
              <span style={{ fontWeight: 'bold', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', display: 'block' }}>
                {summaryName}
              </span>
            </Button>
          </>
        )}

        {showTrainerView && !row.is_bonus_location && (
          <Button className="location-row__trainer-button" disabled={trainerButtonDisabled} selected={activePanel === 'trainers'} onClick={() => togglePanel('trainers')}>
            Trainers {defeatedTrainerCount}/{trainerCount}{(() => {
              const special = trainersLoaded && showSpecialTrainers ? specialTrainers.length : initialSpecialCount
              return special > 0 ? ` +${special}★` : ''
            })()}
          </Button>
        )}

        {showEncounterView && activePanel !== 'encounter' && renderEncounterActions('summary')}

        <div ref={menuRef} className="location-row__menu" style={{ position: 'relative', marginLeft: 'auto' }}>
          <Button onClick={() => setShowMenu(current => !current)} selected={showMenu} aria-label="Location actions" aria-expanded={showMenu} style={{ minWidth: 0, padding: '0 12px' }}>
            ...
          </Button>
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
              <MenuItem tone="info" onClick={handleAddLocation}>Add location</MenuItem>
              {row.is_bonus_location && (
                <MenuItem tone="danger" onClick={handleDeleteLocation}>Delete location</MenuItem>
              )}
              <MenuItem tone="danger" onClick={handleClear}>Clear encounter</MenuItem>
              {status === 'Captured' && pokemonId && (
                <MenuItem tone="warning" onClick={() => { setShowMenu(false); handleMiss() }}>Mark as Missed</MenuItem>
              )}
            </div>
          )}
        </div>
      </div>

      {showEncounterView && activePanel === 'encounter' && panelMode === 'tables' && (
        <div className="location-row__panel location-row__panel--encounter location-row__panel--tables" style={{ ...PANEL_STYLE, marginTop: '10px', padding: '16px' }}>
          <div className="encounter-tables__header" style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: '10px', marginBottom: '12px' }}>
            <div style={{ flex: '1 1 240px', maxWidth: '360px' }}>{renderSearchInput('Search any species')}</div>
            <div style={{ fontSize: '0.75em', color: 'var(--text-secondary)' }}>
              {hasTables ? 'Pick how you met it, then the species.' : 'Pick the species you met.'}
            </div>
          </div>
          <EncounterTables
            view={encounterView}
            locationName={row.display_name}
            fallbackPool={pool}
            dupedFamilyIds={dupedFamilyIds}
            disabled={attemptEnded}
            area={tablesArea}
            onAreaChange={setTablesArea}
            season={tablesSeason}
            onSeasonChange={handleSeasonChange}
            selectedKey={slotKey(selectedSlot)}
            onSelect={handleSelectSlot}
            availabilityOf={availabilityOf}
            newSplitKey={focusSplitKey}
            focus={tablesFocus}
            gates={gates}
            renderTableAdmin={showOpensIn ? (table => {
              const sample = table.rows[0] || table.overlays[0]
              const parent = table.area ? areaAvailability(table.area) : row
              const parentSplit = parent?.opens_in ? splitIndex.get(parent.opens_in) : null
              return renderOpensIn('table', `${row.event_id}|${table.area || ''}|${table.method}|${table.condition || ''}`,
                `${row.display_name} · ${table.meta.label}${table.area ? ` (${table.area})` : ''}`, sample,
                parentSplit ? `${parentSplit.label} or the method's gate` : 'the area and gate', 'right')
            }) : null}
            renderAreaAdmin={showOpensIn ? (area => {
              const current = areaAvailability(area)
              const homeLabel = row.opens_in ? (splitIndex.get(row.opens_in)?.label || 'the location') : 'the location'
              return renderOpensIn('area', `${row.event_id}|${area}`, `${row.display_name} · ${area}`, current, homeLabel)
            }) : null}
          />
          {renderConfirmBar()}
        </div>
      )}

      {showEncounterView && activePanel === 'encounter' && panelMode === 'editor' && (
        <div className="location-row__panel location-row__panel--encounter" style={{ ...PANEL_STYLE, marginTop: '10px', padding: '16px' }}>
          <div className="encounter-editor" style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
            gap: '14px',
            alignItems: 'stretch',
          }}>
            <div className="encounter-editor__column encounter-editor__column--identity" style={{ display: 'grid', gridTemplateRows: 'auto 1fr auto', gap: '14px', minHeight: '320px', padding: '14px', border: 'none', background: 'transparent' }}>
              <div>
                {renderSearchInput('Encounter')}
                {renderProvenance()}
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
                <Button
                  size="sm"
                  shape="rect"
                  icon
                  selected={isShiny}
                  onClick={() => setIsShiny(current => !current)}
                  title="Toggle shiny"
                  aria-label="Shiny"
                  style={{ position: 'absolute', top: '8px', left: '8px', color: isShiny ? '#f4d35e' : undefined }}
                >
                  ★
                </Button>
                {encounterDetails?.has_gender === 'true' && (
                  <Button
                    size="sm"
                    shape="rect"
                    icon
                    onClick={() => {
                      if (encounterDetails?.one_gender === 'true') return
                      setGender(g => g === 'female' ? 'male' : 'female')
                    }}
                    title={encounterDetails?.one_gender === 'true' ? `Always ${gender}` : `Toggle gender`}
                    aria-label={gender === 'female' ? 'Female' : 'Male'}
                    style={{ position: 'absolute', top: '8px', right: '8px', fontSize: '0.9rem', color: gender === 'female' ? '#e84d8a' : '#4d8fe8', cursor: encounterDetails?.one_gender === 'true' ? 'default' : undefined }}
                  >
                    {gender === 'female' ? '♀' : '♂'}
                  </Button>
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
                    <MenuItem onClick={() => { setNature(''); setShowNature(false) }} style={{ color: 'var(--text-secondary)' }}>
                      - Clear -
                    </MenuItem>
                    {NATURES.map(entry => (
                      <MenuItem
                        key={entry.name}
                        selected={nature === entry.name}
                        onClick={() => { setNature(entry.name); setShowNature(false) }}
                        style={{ justifyContent: 'space-between' }}
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
                      </MenuItem>
                    ))}
                  </div>
                )}
              </div>

              <div style={{ border: '1px solid var(--border-strong)', borderRadius: '12px', background: 'var(--surface-mid)', padding: '14px' }}>
                <div style={{ display: 'grid', gridTemplateColumns: STAT_GRID_COLUMNS, gap: '8px', alignItems: 'center', paddingBottom: '8px', marginBottom: '10px', borderBottom: '1px solid var(--border-strong)' }}>
                  <span style={{ fontSize: '0.85em', fontWeight: 'bold', color: 'var(--text-secondary)' }}>BST</span>
                  <span style={{ fontSize: '0.85em', fontWeight: 'bold', color: 'var(--text-secondary)', textAlign: 'right', whiteSpace: 'nowrap' }}>{encounterDetails?.bst ?? '—'}</span>
                  <span />
                  <span title={`Individual values, ${IV_MIN}-${IV_MAX}`} style={{ fontSize: '0.85em', fontWeight: 'bold', color: 'var(--text-secondary)', textAlign: 'center' }}>IV</span>
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
                      <div key={stat.key} style={{ display: 'grid', gridTemplateColumns: STAT_GRID_COLUMNS, gap: '8px', alignItems: 'center' }}>
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
                        <input
                          type="number"
                          inputMode="numeric"
                          min={IV_MIN}
                          max={IV_MAX}
                          step={1}
                          aria-label={`${stat.label} IV`}
                          className="encounter-editor__iv"
                          value={ivs[stat.key] ?? ''}
                          onChange={e => {
                            // Free typing while editing; the blur clamps.
                            const raw = e.target.value
                            setIvs(prev => ({ ...prev, [stat.key]: raw === '' ? null : Number(raw) }))
                          }}
                          onBlur={() => setIvs(prev => {
                            const value = prev[stat.key]
                            if (value == null || Number.isNaN(value)) return { ...prev, [stat.key]: null }
                            return { ...prev, [stat.key]: Math.min(IV_MAX, Math.max(IV_MIN, Math.round(value))) }
                          })}
                          style={IV_INPUT_STYLE}
                        />
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
                autoComplete="off"
                autoCorrect="off"
                spellCheck={false}
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
                        <Button
                          key={option.name}
                          tone={chosen ? 'success' : 'neutral'}
                          shape="rect"
                          block
                          align="start"
                          disabled={!clickable || isSavingEncounter}
                          onClick={() => handleSelectAbility(chosen ? '' : option.name)}
                          title={clickable ? (chosen ? 'Press to unset' : 'Press to record this ability') : undefined}
                          style={{
                            fontWeight: chosen ? 700 : 400,
                            fontStyle: option.hidden ? 'italic' : 'normal',
                            // A read-only list until the Pokemon is caught, not a dead control.
                            opacity: clickable ? 1 : 0.75,
                            cursor: clickable && !isSavingEncounter ? 'pointer' : 'default',
                          }}
                        >
                          {formatAbility(option.name)}{option.hidden ? ' (Hidden)' : ''}{chosen ? ' ✓' : ''}
                        </Button>
                      )
                    })
                  })()}
                </div>
              </div>

              <div className={`encounter-editor__actions${!status ? ' encounter-editor__actions--sticky' : ''}`} style={{ display: 'flex', alignItems: 'flex-end' }}>
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
          {reorderError && (
            <div className="location-row__reorder-error" style={{ fontSize: '0.78em', color: '#e05252', marginBottom: '8px' }}>{reorderError}</div>
          )}
          {!trainersLoaded ? (
            <div style={{ color: 'var(--text-secondary)', fontSize: '0.85em' }}>Loading trainers...</div>
          ) : availableTrainers.length === 0 && specialTrainers.length === 0 ? (
            <div style={{ color: 'var(--text-secondary)', fontSize: '0.85em' }}>No trainers at this location.</div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: hasNamedAreas || specialGroups.length ? '14px' : '8px' }}>
              {[...trainerGroups, ...specialGroups].map(group => (
                <div key={group.key ?? 'location'} className={group.later ? 'trainer-group trainer-group--later' : 'trainer-group'} style={{ display: 'flex', flexDirection: 'column', gap: '8px', ...(group.later ? { '--split-color': group.split.color } : {}) }}>
                  {group.name && (
                    <div className="trainer-group__head" style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '8px',
                      fontSize: '0.72em',
                      letterSpacing: '0.08em',
                      textTransform: 'uppercase',
                      color: group.kind === 'gym' ? 'var(--accent)' : 'var(--text-secondary)',
                    }}>
                      <span>
                        {group.later && <span className="opens-chip__medal" aria-hidden="true">{group.split.label.charAt(0)}</span>}
                        {group.name}
                      </span>
                      <span style={{ flex: 1, height: '1px', background: group.later ? 'color-mix(in srgb, var(--split-color) 50%, transparent)' : 'var(--border-strong)' }} />
                      <span style={{ opacity: 0.7 }}>
                        {group.trainers.filter(t => t.is_defeated).length}/{group.trainers.length}
                      </span>
                    </div>
                  )}
                  {group.trainers.map((trainer, index) => {
                    // Later-split groups are the resolver's order, not a curated one.
                    const reorderable = editMode && !group.special && !group.later
                    const locked = trainerLocked(trainer)
                    const laterSplit = trainerSplitOf(trainer)
                    const slotClass = [
                      'trainer-slot',
                      dropTarget?.trainerId === trainer.trainer_id ? `trainer-slot--drop-${dropTarget.position}` : '',
                      draggingId === trainer.trainer_id ? 'trainer-slot--dragging' : '',
                      highlightTrainerIds.has(Number(trainer.trainer_id)) ? 'trainer-slot--highlight' : '',
                    ].filter(Boolean).join(' ')
                    return (
                      <div
                        key={trainer.trainer_id}
                        className={slotClass}
                        style={laterSplit ? { '--split-color': laterSplit.color } : undefined}
                        {...(reorderable ? slotDragHandlers(group, trainer) : {})}
                      >
                        {showOpensIn && !group.special && (
                          <div style={{ marginBottom: '4px' }}>
                            {renderOpensIn('trainer', trainer.encounter_name, `${trainer.trainer_name || trainer.encounter_name}`, trainer,
                              trainer.area_name ? `${trainer.area_name} or ${homeSplit?.label || 'this row'}` : (homeSplit?.label || 'this row'))}
                          </div>
                        )}
                        <TrainerCard
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
                          reorder={reorderable ? reorderControlsFor(group, index) : null}
                          lockedLabel={locked ? `Opens in ${laterSplit.label}` : null}
                          lockedColor={locked ? laterSplit.color : null}
                        />
                      </div>
                    )
                  })}
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
