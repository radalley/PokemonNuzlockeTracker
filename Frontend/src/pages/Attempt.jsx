
import { useState, useEffect, useMemo, useCallback } from 'react'
import { useParams } from 'react-router-dom'
import LocationRow from '../components/LocationRow'
import BossRow from '../components/BossRow'
import RivalRow from '../components/RivalRow'
import AttemptHeader from '../components/AttemptHeader'
import AttemptSidePanel from '../components/AttemptSidePanel'

const FILTER_OPTIONS = [
  { key: 'master', label: 'Master' },
  { key: 'encounters', label: 'Encounters' },
  { key: 'trainers', label: 'Trainers' },
]

const DOC_SOURCES = [
  {
    name: 'Serebii',
    url: 'https://www.serebii.net/',
    description: 'Pokemon game data, encounter tables, move lists, item data, and walkthrough coverage.',
  },
  {
    name: 'Bulbapedia',
    url: 'https://bulbapedia.bulbagarden.net/',
    description: 'Pokemon wiki documentation for games, mechanics, locations, trainers, and species.',
  },
  {
    name: 'PokemonDB',
    url: 'https://pokemondb.net/',
    description: 'Structured Pokemon reference data with quick lookups for moves, abilities, and locations.',
  },
]

function Attempt() {
  const { runId, attemptId } = useParams()
  const [script, setScript] = useState([])
  const [pools, setPools] = useState({})
  const [runDetails, setRunDetails] = useState(null)
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

  const handlePartyChange = useCallback(() => setPartyRefreshKey(k => k + 1), [])

  useEffect(() => {
    const controller = new AbortController()
    fetch(`/api/runs/${runId}/attempts/${attemptId}/party`, { signal: controller.signal })
      .then(res => res.json())
      .then(data => setPartyPokemonIds(new Set(data.map(p => p.pokemon_id))))
      .catch(err => { if (err.name !== 'AbortError') console.error(err) })
    return () => controller.abort()
  }, [runId, attemptId, partyRefreshKey])

  useEffect(() => {
    const controller = new AbortController()
    setAttemptLoadError('')
    setAttemptLoaded(false)
    fetch(`/api/attempt-page/${runId}/${attemptId}`, { signal: controller.signal })
      .then(res => res.json())
      .then(data => {
        setRunDetails(data.run)
        setCurrentStarter(data.run?.starter || '')
        setScript(data.script)
        setPools(data.pools || {})
        setSavedEncounters(data.encounters || {})
        setAttemptLoaded(true)
      })
      .catch(err => {
        if (err.name === 'AbortError') return
        console.error(err)
        setAttemptLoadError('Failed to load attempt page data.')
        setAttemptLoaded(true)
      })
    return () => controller.abort()
  }, [runId, attemptId, refreshKey])

  const handleStarterChange = (newStarter) => {
    if (newStarter !== currentStarter) {
      fetch(`/api/update-starter`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ run_id: runId, attempt_id: attemptId, starter: newStarter })
      })
      .then(res => res.json())
      .then(() => {
        setCurrentStarter(newStarter)
        setRefreshKey(k => k + 1)
      })
      .catch(err => console.error('Failed to update starter:', err))
    }
  }

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
    fetch(`/api/evolution-families?ids=${capturedSpeciesIds.join(',')}`, { signal: controller.signal })
      .then(res => res.json())
      .then(data => setDupedFamilyIds(new Set(data)))
      .catch(err => { if (err.name !== 'AbortError') console.error(err) })
    return () => controller.abort()
  }, [capturedSpeciesIds.join(',')])

  const handleStatusChange = useCallback((locationId, speciesId, newStatus) => {
    setSavedEncounters(prev => ({
      ...prev,
      [locationId]: { ...(prev[locationId] || {}), species_id: speciesId, status: newStatus }
    }))
  }, [])

  const handleEncounterChange = useCallback(() => {
    fetch(`/api/pokebank/${runId}/${attemptId}`)
      .then(res => res.json())
      .then(data => {
        const byLocation = {}
        data.forEach(p => { byLocation[p.encounter_key] = p })
        setSavedEncounters(byLocation)
        setStatsRefreshKey(k => k + 1)
      })
  }, [runId, attemptId])

  const handleVictoryRecorded = useCallback(() => {
    setStatsRefreshKey(k => k + 1)
    setRefreshKey(k => k + 1)
  }, [])

  const handleStructureChange = useCallback(() => {
    setRefreshKey(k => k + 1)
    setStatsRefreshKey(k => k + 1)
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

  const visibleScript = useMemo(() => {
    if (activeFilter === 'master') return script
    if (activeFilter === 'encounters') {
      return script.filter(row => row.event_type === 'Location')
    }
    return script.filter(row => row.event_type !== 'Location' || row.trainer_count > 0)
  }, [activeFilter, script])

  if (!attemptLoaded) return <p>Loading...</p>
  if (!runDetails) return <p>{attemptLoadError || 'Attempt not found.'}</p>

  function renderScriptRow(row) {
    if (row.event_type === 'Location') return <LocationRow key={`${row.event_id}:${row.secondary_sort_order}:${row.display_name}`} row={row} pool={pools[row.event_id] || []} savedEncounter={savedEncounters[row.encounter_key] ?? null} runId={parseInt(runId)} attemptNumber={parseInt(attemptId)} gameId={runDetails?.game_id || null} dupedFamilyIds={dupedFamilyIds} onEncounterChange={handleEncounterChange} onStatusChange={handleStatusChange} onPartyChange={handlePartyChange} onStructureChange={handleStructureChange} partyPokemonIds={partyPokemonIds} onVictoryRecorded={handleVictoryRecorded} viewMode={locationViewMode} />
    if (row.event_type === 'Rival') return <RivalRow key={row.sort_order} row={row} gameId={runDetails?.game_id || null} runId={parseInt(runId)} attemptId={parseInt(attemptId)} onVictoryRecorded={handleVictoryRecorded} />
    return <BossRow key={row.sort_order} row={row} gameId={runDetails?.game_id || null} runId={parseInt(runId)} attemptId={parseInt(attemptId)} onVictoryRecorded={handleVictoryRecorded} />
  }

  return (
    <div style={{ paddingTop: '120px', paddingBottom: '40px' }}>
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
              background: '#1b1c23',
              border: '1px solid #343a47',
              borderRadius: '14px',
              padding: '20px',
              boxShadow: '0 18px 48px rgba(0, 0, 0, 0.35)',
            }}
          >
            <div style={{ fontSize: '1rem', fontWeight: 'bold', color: '#eef2f7', marginBottom: '4px' }}>
              Game Documentation
            </div>
            <div style={{ fontSize: '0.82rem', color: '#9aa3b5', marginBottom: '16px' }}>
              Choose a source for {runDetails?.game_name || 'this game'}.
            </div>
            <div
              style={{
                marginBottom: '16px',
                padding: '8px 10px',
                borderRadius: '8px',
                border: '1px dashed #3f4654',
                background: '#141922',
                fontSize: '0.76rem',
                color: '#9aa3b5',
                fontFamily: 'Consolas, monospace',
              }}
            >
              debug game_id={runDetails?.game_id ?? 'n/a'} version_group_id={runDetails?.version_group_id ?? 'n/a'}
            </div>
            <div style={{ display: 'grid', gap: '10px' }}>
              {DOC_SOURCES.map(source => (
                <button
                  key={source.name}
                  type="button"
                  onClick={() => handleOpenDocsSource(source.url)}
                  style={{
                    textAlign: 'left',
                    padding: '12px 14px',
                    borderRadius: '10px',
                    border: '1px solid #343a47',
                    background: '#11151d',
                    color: '#eef2f7',
                    cursor: 'pointer',
                  }}
                >
                  <div style={{ fontWeight: 'bold', color: '#7ec8e3', marginBottom: '4px' }}>{source.name}</div>
                  <div style={{ fontSize: '0.8rem', color: '#c5cedd', lineHeight: 1.4 }}>{source.description}</div>
                </button>
              ))}
            </div>
            <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '16px' }}>
              <button
                type="button"
                onClick={() => setShowDocsMenu(false)}
                style={{
                  padding: '7px 12px',
                  borderRadius: '8px',
                  border: '1px solid #343a47',
                  background: '#171920',
                  color: '#d6dbe6',
                  cursor: 'pointer',
                }}
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      <AttemptHeader runId={parseInt(runId)} attemptId={parseInt(attemptId)} runDetails={runDetails} partyRefreshKey={partyRefreshKey} />

      <div style={{ maxWidth: '1380px', margin: '0 auto', padding: '0 28px', position: 'relative' }}>
        <AttemptSidePanel runId={parseInt(runId)} attemptId={parseInt(attemptId)} statsRefreshKey={statsRefreshKey}>
          <div style={{ width: '100%', boxSizing: 'border-box', margin: '10px 0 8px 0', border: '1px solid #343a47', borderRadius: '8px', padding: '10px', background: '#171920' }}>
            <div style={{ fontSize: '0.8em', color: '#8d97ab', marginBottom: '8px' }}>Starter</div>
            <div style={{ display: 'flex', flexDirection: 'row', gap: '6px' }}>
              <button 
                onClick={() => handleStarterChange('Fire')}
                style={{ 
                  flex: 1,
                  padding: '5px 8px', 
                  backgroundColor: currentStarter === 'Fire' ? '#ff6b6b' : '',
                  border: '1px solid #ccc',
                  borderRadius: '4px',
                  cursor: 'pointer'
                }}
              >
                Fire
              </button>
              <button 
                onClick={() => handleStarterChange('Grass')}
                style={{ 
                  flex: 1,
                  padding: '5px 8px', 
                  backgroundColor: currentStarter === 'Grass' ? '#51cf66' : '',
                  border: '1px solid #ccc',
                  borderRadius: '4px',
                  cursor: 'pointer'
                }}
              >
                Grass
              </button>
              <button 
                onClick={() => handleStarterChange('Water')}
                style={{ 
                  flex: 1,
                  padding: '5px 8px', 
                  backgroundColor: currentStarter === 'Water' ? '#74c0fc' : '',
                  border: '1px solid #ccc',
                  borderRadius: '4px',
                  cursor: 'pointer'
                }}
              >
                Water
              </button>
            </div>
          </div>
        </AttemptSidePanel>

        <div style={{ textAlign: 'left' }}>
          <div style={{ marginBottom: '18px', padding: '12px', border: '1px solid #343a47', borderRadius: '12px', background: '#171920', display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
            <div style={{ fontSize: '0.82em', color: '#8d97ab', marginRight: '8px' }}>Filter View</div>
            {FILTER_OPTIONS.map(option => {
              const isActive = activeFilter === option.key
              return (
                <button
                  key={option.key}
                  type="button"
                  onClick={() => setActiveFilter(option.key)}
                  style={{
                    padding: '8px 14px',
                    borderRadius: '999px',
                    border: `1px solid ${isActive ? '#7ec8e3' : '#343a47'}`,
                    background: isActive ? '#1d2430' : '#11151d',
                    color: isActive ? '#eef7fb' : '#c5cedd',
                    cursor: 'pointer',
                    font: 'inherit',
                  }}
                >
                  {option.label}
                </button>
              )
            })}
          </div>

          {visibleScript.map(row => renderScriptRow(row))}
        </div>
      </div>

      <footer style={{ position: 'fixed', bottom: 0, left: 0, right: 0, height: '40px', borderTop: '1px solid #ccc', backgroundColor: '#16171d', zIndex: 1000, display: 'flex', justifyContent: 'center', alignItems: 'center', gap: '10px' }}>
        <button type="button" onClick={() => setShowDocsMenu(true)}>Game Documentation</button>
        <button>Contact/About Me</button>
      </footer>
    </div>
  )
}

export default Attempt