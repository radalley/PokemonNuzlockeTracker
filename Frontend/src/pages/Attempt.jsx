
import { useState, useEffect, useMemo, useCallback, useRef } from 'react'
import { apiFetch } from '../utils/api'
import { useParams } from 'react-router-dom'
import LocationRow from '../components/LocationRow'
import BossRow from '../components/BossRow'
import RivalRow from '../components/RivalRow'
import AttemptHeader from '../components/AttemptHeader'
import AttemptSidePanel from '../components/AttemptSidePanel'
import SplitTimeline from '../components/SplitTimeline'
import SplitSection from '../components/SplitSection'
import SplitRail from '../components/SplitRail'
import GameFlagsPanel from '../components/GameFlagsPanel'
import ContactButton from '../components/ContactButton'
import { Button } from '../components/Button'
import { getAttemptPageData, getBattleRecords, getParty, getPokebank, getSplitCatalogue, markRunOpened, updateStarter as saveStarter } from '../utils/dataLayer'
import { useAuth } from '../contexts/AuthContext'
import { useEditMode } from '../contexts/EditModeContext'
import useDockedPanels from '../utils/useDockedPanels'
import useRunSeason from '../utils/useRunSeason'
import { applyStatusChange } from '../utils/savedEncounters'
import { starterBranchForSpecies, starterCaptureSpecies } from '../utils/starterBranch'
import { buildSplitFeed, isSplitLayout } from '../utils/splitFeed'
import '../components/SplitSections.css'

const EMPTY_POOL = []
const EMPTY_TABLES = []
const EMPTY_METHODS = []
const EMPTY_SPLITS = []
const EMPTY_GATES = []

const FILTER_OPTIONS = [
  { key: 'master', label: 'Master' },
  { key: 'encounters', label: 'Encounters' },
  { key: 'trainers', label: 'Trainers' },
]

const DOC_SOURCES = [
  {
    name: 'Serebii',
    refKey: 's_ref',
    buildUrl: (ref) => `https://serebii.net/${ref}/`,
    fallbackUrl: 'https://serebii.net/',
    description: 'Pokemon game data, encounter tables, move lists, item data, and walkthrough coverage.',
  },
  {
    name: 'Bulbapedia',
    refKey: 'b_ref',
    buildUrl: (ref) => `https://bulbapedia.bulbagarden.net/wiki/${ref}`,
    fallbackUrl: 'https://bulbapedia.bulbagarden.net/',
    description: 'Pokemon wiki documentation for games, mechanics, locations, trainers, and species.',
  },
  {
    name: 'PokemonDB',
    refKey: 'pdb_ref',
    buildUrl: (ref) => `https://pokemondb.net/${ref}`,
    fallbackUrl: 'https://pokemondb.net/',
    description: 'Structured Pokemon reference data with quick lookups for moves, abilities, and locations.',
  },
]

// The filter is applied inside each section the same way it is applied
// to the flat feed.
function rowPassesFilter(row, filter) {
  if (filter === 'master') return true
  if (filter === 'encounters') return row.event_type === 'Location'
  return row.event_type !== 'Location' || row.trainer_count > 0 || row.special_trainer_count > 0
}

function Attempt() {
  const { runId, attemptId } = useParams()
  const { user } = useAuth()
  const isAdmin = user?.account_type === 'admin'
  const { editMode } = useEditMode()
  const [script, setScript] = useState([])
  const [pools, setPools] = useState({})
  const [poolTables, setPoolTables] = useState({})
  const [encounterMethods, setEncounterMethods] = useState(EMPTY_METHODS)
  // Split layout (Blaze Black): the payload's sections and gates. Other
  // games leave these empty and keep the flat feed.
  const [splits, setSplits] = useState(EMPTY_SPLITS)
  const [splitGates, setSplitGates] = useState(EMPTY_GATES)
  const [splitItems, setSplitItems] = useState([])
  const [battleRecords, setBattleRecords] = useState([])
  const [itemsRevision, setItemsRevision] = useState(0)
  // One Black/White season for the whole run, shared by every location's
  // encounter tables and remembered per run.
  const [season, handleSeasonChange] = useRunSeason(runId)
  const [runDetails, setRunDetails] = useState(null)
  const [attemptInfo, setAttemptInfo] = useState(null)
  const [attemptLoaded, setAttemptLoaded] = useState(false)
  const [attemptLoadError, setAttemptLoadError] = useState('')
  const [currentStarter, setCurrentStarter] = useState('')
  const [savedEncounters, setSavedEncounters] = useState({})
  const [refreshKey, setRefreshKey] = useState(0)
  const [statsRefreshKey, setStatsRefreshKey] = useState(0)
  const [partyRefreshKey, setPartyRefreshKey] = useState(0)
  const [partyPokemonIds, setPartyPokemonIds] = useState(new Set())
  const [activeFilter, setActiveFilter] = useState('master')
  const [showDocsMenu, setShowDocsMenu] = useState(false)
  const [allSpecies, setAllSpecies] = useState([])
  // Open in the outer desktop gutter; narrow screens use a corner-tab drawer.
  const dockedPanels = useDockedPanels()
  const [statsOverride, setStatsOpen] = useState(null)
  const statsOpen = statsOverride ?? dockedPanels
  const [flagsOpen, setFlagsOpen] = useState(false)
  // Sections the player opened or closed by hand; the rest follow their
  // state (beaten splits collapse, the current and future ones stay open).
  const [expandedOverrides, setExpandedOverrides] = useState({})
  // A jump from a split's returns list to an earlier area's row. The nonce
  // makes a repeat jump to the same row re-open its panel.
  const [jump, setJump] = useState(null)
  const jumpNonceRef = useRef(0)

  useEffect(() => {
    apiFetch('/api/species/search?q=')
      .then(res => res.json())
      .then(data => setAllSpecies(data))
      .catch(err => console.error('Failed to preload species:', err))
  }, [])

  const handlePartyChange = useCallback(() => setPartyRefreshKey(k => k + 1), [])

  useEffect(() => {
    const controller = new AbortController()
    getParty(runId, attemptId)
      .then(data => setPartyPokemonIds(new Set((data || []).map(p => p.pokemon_id))))
      .catch(err => { if (err.name !== 'AbortError') console.error(err) })
    return () => controller.abort()
  }, [runId, attemptId, partyRefreshKey])

  // Refetches for an already-displayed attempt (victories, starter changes,
  // structure edits) reconcile in the background: unmounting into the
  // loading screen would collapse the page and reset the scroll position.
  const loadedIdentityRef = useRef(null)
  const loadSeqRef = useRef(0)
  const encountersVersionRef = useRef(0)

  useEffect(() => {
    const identity = `${runId}:${attemptId}`
    const seq = ++loadSeqRef.current
    const encountersVersion = encountersVersionRef.current
    const isBackgroundRefresh = loadedIdentityRef.current === identity
    if (!isBackgroundRefresh) {
      setAttemptLoadError('')
      setAttemptLoaded(false)
    }
    getAttemptPageData(runId, attemptId)
      .then(data => {
        if (seq !== loadSeqRef.current) return
        if (!data?.run && isBackgroundRefresh) {
          // The run vanished mid-session (e.g. deleted in another tab):
          // keep the current view rather than collapsing it under the user.
          console.error('Background refresh returned no run data; keeping current view.')
          return
        }
        setRunDetails(data?.run || null)
        setAttemptInfo(data?.attempt || null)
        setCurrentStarter(data?.run?.starter || '')
        setScript(data?.script || [])
        setPools(data?.pools || {})
        setPoolTables(data?.pool_tables || {})
        setEncounterMethods(data?.encounter_methods?.length ? data.encounter_methods : EMPTY_METHODS)
        setSplits(isSplitLayout(data) ? data.splits : EMPTY_SPLITS)
        setSplitGates(data?.split_gates?.length ? data.split_gates : EMPTY_GATES)
        // A stale snapshot must not clobber encounter edits (saves, deletes,
        // status changes) made while this request was in flight.
        if (encountersVersion === encountersVersionRef.current) {
          setSavedEncounters(data?.encounters || {})
        }
        setAttemptLoaded(true)
        if (data?.run) {
          loadedIdentityRef.current = identity
          markRunOpened(runId, attemptId).catch(err => console.error('Failed to record opened run:', err))
        }
      })
      .catch(err => {
        if (seq !== loadSeqRef.current) return
        console.error(err)
        if (!isBackgroundRefresh) {
          setAttemptLoadError('Failed to load attempt page data.')
          setAttemptLoaded(true)
        }
      })
  }, [runId, attemptId, refreshKey])

  const splitLayout = splits.length > 0
  const gameId = runDetails?.game_id || null

  // Split layout: each split's item library and the parties that beat it.
  useEffect(() => {
    if (!splitLayout || !gameId) return undefined
    let active = true
    Promise.all([getSplitCatalogue(gameId, currentStarter), getBattleRecords(runId, attemptId)])
      .then(([catalogue, records]) => {
        if (!active) return
        setSplitItems(catalogue?.items || [])
        setBattleRecords(records || [])
      })
      .catch(err => console.error('Failed to load split items:', err))
    return () => { active = false }
  }, [splitLayout, gameId, currentStarter, runId, attemptId, statsRefreshKey, itemsRevision])

  const handleStarterChange = (newStarter) => {
    if (newStarter !== currentStarter) {
      saveStarter(runId, attemptId, newStarter)
        .then(() => {
          setCurrentStarter(newStarter)
          setRefreshKey(k => k + 1)
        })
        .catch(err => console.error('Failed to update starter:', err))
    }
  }

  // Logging (or changing) the Starter capture sets the session-stats
  // branch. Only a change seen this session counts: attempts default to
  // 'Fire', so a value on load may be a deliberate picker override.
  const starterCapture = attemptLoaded ? starterCaptureSpecies(savedEncounters) : undefined
  const seenStarterCaptureRef = useRef({ identity: null, species: undefined })
  useEffect(() => {
    if (starterCapture === undefined) return
    // The loaded attempt, not the URL: right after navigating, the old
    // attempt's encounters render once under the new params.
    const identity = loadedIdentityRef.current
    const seen = seenStarterCaptureRef.current
    seenStarterCaptureRef.current = { identity, species: starterCapture }
    if (!identity || seen.identity !== identity || seen.species === starterCapture || !starterCapture) return
    if (Number(runDetails?.version_group_id) === 2) return
    const branch = starterBranchForSpecies(starterCapture)
    if (branch) handleStarterChange(branch)
  }, [starterCapture, runId, attemptId]) // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (Number(runDetails?.version_group_id) !== 2) return
    if (['Blue', 'Red', 'Yellow'].includes(currentStarter)) return

    saveStarter(runId, attemptId, 'Yellow')
      .then(() => {
        setCurrentStarter('Yellow')
        setRefreshKey(k => k + 1)
      })
      .catch(err => console.error('Failed to update Yellow rival Eevee branch:', err))
  }, [runDetails?.version_group_id, currentStarter, runId, attemptId])

  const capturedSpeciesIds = useMemo(
    () => Object.values(savedEncounters)
      .filter(e => e.status === 'Captured' || e.status === 'Dead')
      .map(e => e.species_id)
      .filter(Boolean),
    [savedEncounters]
  )

  const [dupedFamilyIds, setDupedFamilyIds] = useState(new Set())

  useEffect(() => {
    if (capturedSpeciesIds.length === 0) {
      setDupedFamilyIds(new Set())
      return
    }
    const controller = new AbortController()
    apiFetch(`/api/evolution-families?ids=${capturedSpeciesIds.join(',')}`, { signal: controller.signal })
      .then(res => res.json())
      .then(data => setDupedFamilyIds(new Set(data)))
      .catch(err => { if (err.name !== 'AbortError') console.error(err) })
    return () => controller.abort()
  }, [capturedSpeciesIds.join(',')])

  const handleStatusChange = useCallback((locationId, speciesId, newStatus) => {
    encountersVersionRef.current += 1
    setSavedEncounters(prev => applyStatusChange(prev, locationId, speciesId, newStatus))
  }, [])

  const handleEncounterChange = useCallback(() => {
    const version = ++encountersVersionRef.current
    getPokebank(runId, attemptId)
      .then(data => {
        if (version !== encountersVersionRef.current) return
        const byLocation = {}
        ;(data || []).forEach(p => { byLocation[p.encounter_key] = p })
        setSavedEncounters(byLocation)
        setStatsRefreshKey(k => k + 1)
      })
  }, [runId, attemptId])

  const handleVictoryRecorded = useCallback(() => {
    setStatsRefreshKey(k => k + 1)
    setRefreshKey(k => k + 1)
    setPartyRefreshKey(k => k + 1)
  }, [])

  const handleStructureChange = useCallback(() => {
    setRefreshKey(k => k + 1)
    setStatsRefreshKey(k => k + 1)
  }, [])

  // An availability edit (Opens in, Game flags) re-resolves the whole page.
  const handleAvailabilityChange = useCallback(() => {
    setRefreshKey(k => k + 1)
  }, [])

  const handleOpenDocsSource = (url) => {
    window.open(url, '_blank', 'noopener,noreferrer')
    setShowDocsMenu(false)
  }

  const locationViewMode = activeFilter === 'encounters'
    ? 'encounters'
    : activeFilter === 'trainers'
      ? 'trainers'
      : 'master'
  const contactContext = {
    runId,
    attemptId,
    gameId: runDetails?.game_id || null,
    versionGroupId: runDetails?.version_group_id || null,
    runName: runDetails?.name || null,
    gameName: runDetails?.game_name || null,
  }

  const visibleScript = useMemo(() => script.filter(row => rowPassesFilter(row, activeFilter)), [activeFilter, script])

  const feed = useMemo(
    () => (splitLayout ? buildSplitFeed(script, splits, savedEncounters) : null),
    [splitLayout, script, splits, savedEncounters]
  )
  const splitIndex = feed?.index
  const currentOrdinal = feed?.currentOrdinal ?? Number.POSITIVE_INFINITY

  const isExpanded = section => expandedOverrides[section.key] ?? section.state !== 'done'
  const toggleSection = section => setExpandedOverrides(prev => ({ ...prev, [section.key]: !isExpanded(section) }))

  const scrollToId = useCallback((id) => {
    requestAnimationFrame(() => {
      const target = document.getElementById(id)
      if (!target) return
      const reduce = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
      target.scrollIntoView({ block: 'start', behavior: reduce ? 'auto' : 'smooth' })
    })
  }, [])

  // From a split's "New encounters / New trainers" list to the area's row
  // in its home split: expand that split, scroll there, open the panel on
  // what is new, and offer the way back.
  const handleJump = (entry, panel, fromSection) => {
    const homeKey = entry.row.home_split
    if (homeKey) setExpandedOverrides(prev => ({ ...prev, [homeKey]: true }))
    jumpNonceRef.current += 1
    setJump({
      nonce: jumpNonceRef.current,
      encounterKey: entry.encounterKey,
      panel,
      splitKey: fromSection.key,
      fromKey: fromSection.key,
      fromLabel: fromSection.split.label,
      methods: (entry.methods || []).map(m => m.method),
      areas: entry.areas || [],
      trainerIds: entry.trainerIds || [],
    })
    scrollToId(`location-${entry.encounterKey}`)
  }
  const handleJumpBack = () => {
    if (!jump) return
    const key = jump.fromKey
    setJump(null)
    scrollToId(`section-${key}`)
  }
  const handleRailJump = (key) => {
    setExpandedOverrides(prev => ({ ...prev, [key]: true }))
    scrollToId(`section-${key}`)
  }

  if (!attemptLoaded) return <p>Loading...</p>
  if (!runDetails) return <p>{attemptLoadError || 'Attempt not found.'}</p>

  function renderScriptRow(row) {
    const generation = runDetails?.generation ?? null
    const attemptEnded = attemptInfo?.outcome === 'dead'
    if (row.event_type === 'Location') return <LocationRow key={`${row.event_id}:${row.secondary_sort_order}`} row={row} pool={pools[row.event_id] ?? EMPTY_POOL} poolTables={poolTables[row.event_id] ?? EMPTY_TABLES} encounterMethods={encounterMethods} season={season} onSeasonChange={handleSeasonChange} allSpecies={allSpecies} savedEncounter={savedEncounters[row.encounter_key] ?? null} runId={runId} attemptNumber={parseInt(attemptId)} gameId={runDetails?.game_id || null} generation={generation} dupedFamilyIds={dupedFamilyIds} onEncounterChange={handleEncounterChange} onStatusChange={handleStatusChange} onPartyChange={handlePartyChange} onStructureChange={handleStructureChange} partyPokemonIds={partyPokemonIds} onVictoryRecorded={handleVictoryRecorded} viewMode={locationViewMode} attemptEnded={attemptEnded}
      splitLayout={splitLayout} splitIndex={splitIndex} currentOrdinal={currentOrdinal} splits={splits} gates={splitGates}
      openRequest={jump && jump.encounterKey === row.encounter_key ? jump : null} onAvailabilityChange={handleAvailabilityChange} />
    if (row.event_type === 'Rival') return <RivalRow key={row.sort_order} row={row} gameId={runDetails?.game_id || null} generation={generation} runId={runId} attemptId={parseInt(attemptId)} onVictoryRecorded={handleVictoryRecorded} attemptEnded={attemptEnded} />
    return <BossRow key={row.sort_order} row={row} gameId={runDetails?.game_id || null} generation={generation} runId={runId} attemptId={parseInt(attemptId)} onVictoryRecorded={handleVictoryRecorded} attemptEnded={attemptEnded} />
  }

  const visibleSections = feed ? feed.sections.filter(section => !section.hidden) : []
  const currentSection = feed?.current || null

  return (
    <div className="attempt-page" style={{ paddingTop: '120px', paddingBottom: '56px' }}>
      {showDocsMenu && (
        <div
          onClick={() => setShowDocsMenu(false)}
          style={{
            position: 'fixed',
            inset: 0,
            backgroundColor: 'rgba(0, 0, 0, 0.68)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 2000,
          }}
        >
          <div
            onClick={event => event.stopPropagation()}
            style={{
              width: 'min(560px, calc(100vw - 32px))',
              background: 'var(--surface)',
              border: '1px solid var(--border-strong)',
              borderRadius: '14px',
              padding: '20px',
              boxShadow: '0 18px 48px rgba(0, 0, 0, 0.35)',
            }}
          >
            <div style={{ fontSize: '1rem', fontWeight: 'bold', color: 'var(--text-primary)', marginBottom: '4px' }}>
              Game Documentation
            </div>
            <div style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', marginBottom: '16px' }}>
              Choose a source for {runDetails?.game_name || 'this game'}.
            </div>
            <div style={{ display: 'grid', gap: '10px' }}>
              {DOC_SOURCES.map(source => (
                <Button
                  key={source.name}
                  shape="rect"
                  block
                  align="start"
                  className="btn--stack"
                  onClick={() => { const ref = runDetails?.[source.refKey]; handleOpenDocsSource(ref ? source.buildUrl(ref) : source.fallbackUrl) }}
                >
                  <span style={{ fontWeight: 'bold', color: 'var(--info)' }}>{source.name}</span>
                  <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', lineHeight: 1.4 }}>{source.description}</span>
                </Button>
              ))}
            </div>
            <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '16px' }}>
              <Button onClick={() => setShowDocsMenu(false)}>Close</Button>
            </div>
          </div>
        </div>
      )}

      <AttemptHeader runId={runId} attemptId={parseInt(attemptId)} runDetails={runDetails} partyRefreshKey={partyRefreshKey} onPartyChange={handlePartyChange} statsOpen={statsOpen} onToggleStats={() => setStatsOpen(!statsOpen)} debugOpen={isAdmin && flagsOpen} onToggleDebug={isAdmin ? () => setFlagsOpen(v => !v) : null} attemptOutcome={attemptInfo} />

      {isAdmin && flagsOpen && (
        <GameFlagsPanel
          gameId={gameId}
          gameName={runDetails?.game_name || ''}
          splits={splits}
          gates={splitGates}
          index={splitIndex || new Map()}
          encounterMethods={encounterMethods}
          onClose={() => setFlagsOpen(false)}
          onSaved={handleAvailabilityChange}
        />
      )}

      <div className="attempt-page__content attempt-page__content--splits" style={{ maxWidth: '1380px', margin: '0 auto', padding: '0 28px', position: 'relative' }}>
        {!dockedPanels && <button type="button" className="attempt-panel-flag attempt-panel-flag--stats" aria-expanded={statsOpen} onClick={() => setStatsOpen(!statsOpen)}>Stats {statsOpen ? '×' : '›'}</button>}
        {!dockedPanels && statsOpen && <button type="button" className="attempt-panel-backdrop" aria-label="Close stats panel" onClick={() => setStatsOpen(false)} />}
        <AttemptSidePanel runId={runId} attemptId={parseInt(attemptId)} statsRefreshKey={statsRefreshKey} statsOpen={statsOpen} onToggleStats={() => setStatsOpen(!statsOpen)} starter={currentStarter} onStarterChange={handleStarterChange} showStarterControls versionGroupId={runDetails?.version_group_id} />

        <div className={`attempt-page__body${splitLayout ? ' split-feed' : ''}`} style={{ textAlign: 'left', ...(currentSection ? { '--split-color': currentSection.color } : {}) }}>
          {attemptInfo?.outcome === 'dead' && (
            <div style={{ marginBottom: '18px', padding: '10px 14px', border: '1px solid #5a2d2d', borderRadius: '12px', background: 'rgba(224,82,82,0.08)', display: 'flex', alignItems: 'center', gap: '12px', flexWrap: 'wrap' }}>
              <span style={{ fontSize: '0.88em', color: '#e05252', fontWeight: 'bold' }}>☠ This attempt has ended</span>
              {attemptInfo.ended_at && (
                <span style={{ fontSize: '0.78em', color: 'var(--text-secondary)' }}>{new Date(attemptInfo.ended_at).toLocaleDateString()}</span>
              )}
              <span style={{ fontSize: '0.78em', color: 'var(--text-secondary)' }}>You are reviewing it.</span>
              <Button
                tone="warning"
                size="sm"
                onClick={() => { window.location.href = `/attempt/${runId}/${attemptId}/summary` }}
                style={{ marginLeft: 'auto' }}
              >
                View Summary
              </Button>
            </div>
          )}

          {splitLayout && (
            <div className="split-strip" role="status" aria-live="polite">
              <span className="split-strip__kicker">{currentSection ? `Now · ${currentSection.split.kind === 'gym' ? `Split ${currentSection.ordinal + 1}` : currentSection.split.label}` : 'Run complete'}</span>
              {currentSection && <span className="split-strip__name">{currentSection.split.label}</span>}
              {currentSection && (
                <span>{[currentSection.split.type_focus, currentSection.split.level_cap != null ? `Level cap ${currentSection.split.level_cap}` : null].filter(Boolean).join(' · ')}</span>
              )}
              {jump && (
                <button type="button" className="split-strip__back" onClick={handleJumpBack}>
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="M12 19V5" /><path d="M5 12l7-7 7 7" /></svg>
                  Back to {jump.fromLabel}
                </button>
              )}
            </div>
          )}

          <div className="attempt-filter" style={{ marginBottom: '18px', padding: '12px', border: '1px solid var(--border-strong)', borderRadius: '12px', background: 'var(--surface)', display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap', boxShadow: '0 2px 6px rgba(0,0,0,0.4)' }}>
            <div className="attempt-filter__label" style={{ fontSize: '0.82em', color: 'var(--text-secondary)', marginRight: '8px' }}>Filter View</div>
            {FILTER_OPTIONS.map(option => {
              const isActive = activeFilter === option.key
              return (
                <Button
                  key={option.key}
                  className="attempt-filter__button"
                  selected={isActive}
                  onClick={() => setActiveFilter(option.key)}
                >
                  {option.label}
                </Button>
              )
            })}
          </div>

          {splitLayout
            ? visibleSections.map(section => (
              <SplitSection
                key={section.key}
                section={{ ...section, rows: section.rows.filter(row => rowPassesFilter(row, activeFilter)) }}
                total={feed.sections.filter(s => s.split.kind === 'gym').length}
                gameId={gameId}
                items={splitItems.filter(item => item.split_key === section.key)}
                record={battleRecords.find(r => r.split_key === section.key || (section.split.final_trainer_id != null && Number(r.trainer_id) === Number(section.split.final_trainer_id))) || null}
                encounterMethods={encounterMethods}
                editMode={editMode}
                gymSplits={splits.filter(s => s.kind === 'gym')}
                expanded={isExpanded(section)}
                onToggle={() => toggleSection(section)}
                onJump={(entry, panel) => handleJump(entry, panel, section)}
                renderRow={renderScriptRow}
                onItemsChanged={() => setItemsRevision(r => r + 1)}
              />
            ))
            : visibleScript.map(row => renderScriptRow(row))}
        </div>
        {splitLayout
          ? <SplitRail sections={feed.sections} onJump={handleRailJump} />
          : <SplitTimeline key={`${runId}:${attemptId}`} runId={runId} attemptId={attemptId}
              gameId={runDetails?.game_id} generation={runDetails?.generation} starter={currentStarter}
              script={script} refreshKey={statsRefreshKey} editMode={editMode} />}
      </div>

      <footer className="attempt-footer">
        <Button size="sm" className="attempt-footer__button" onClick={() => setShowDocsMenu(true)}>Game Documentation</Button>
        <ContactButton context={contactContext} size="sm" className="attempt-footer__button" />
      </footer>
    </div>
  )
}

export default Attempt
