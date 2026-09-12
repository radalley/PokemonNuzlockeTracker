import { useState, useEffect, useMemo } from 'react'
import { apiFetch } from '../utils/api'
import { useParams } from 'react-router-dom'
import AttemptHeader from '../components/AttemptHeader'
import AttemptSidePanel from '../components/AttemptSidePanel'
import BoxTile from '../components/BoxTile'
import PokemonSummary from '../components/PokemonSummary'
import Sprite from '../components/Sprite'
import {
  getRunDetails,
  getBox,
  getParty,
  getSpeciesSummary,
  addToParty,
  removeFromParty,
  updateEncounterStatus,
} from '../utils/dataLayer'

const MODAL_BUTTON_STYLE = {
  minHeight: '34px',
  padding: '6px 14px',
  border: '1px solid var(--border-strong)',
  borderRadius: '999px',
  background: 'var(--surface-deep)',
  color: 'var(--text-secondary)',
  cursor: 'pointer',
  font: 'inherit',
  fontSize: '0.85em',
}

function withStatusPayload(pokemon, patch) {
  return {
    ...pokemon,
    ...patch,
    bonus_location: pokemon.bonus_location || pokemon.secondary_sort_order || 0,
  }
}

/**
 * The PC. Every Pokemon the attempt has caught, alive on top and fallen
 * underneath, laid out as a grid of tiles; selecting one opens its
 * summary (abilities, stats, learnset, battle record, actions) alongside.
 */
function Box() {
  const { runId, attemptId } = useParams()
  const attemptNumber = parseInt(attemptId)
  const [runDetails, setRunDetails] = useState(null)
  const [pokemon, setPokemon] = useState([])
  const [loaded, setLoaded] = useState(false)
  const [selectedId, setSelectedId] = useState(null)
  const [statsRefreshKey, setStatsRefreshKey] = useState(0)
  const [statsOpen, setStatsOpen] = useState(false)
  const [partyRefreshKey, setPartyRefreshKey] = useState(0)
  const [partyPokemonIds, setPartyPokemonIds] = useState(new Set())
  const [evolveTarget, setEvolveTarget] = useState(null)
  const [evolveOptions, setEvolveOptions] = useState(null)
  const [evolvableSpecies, setEvolvableSpecies] = useState(new Set())

  const gameId = runDetails?.game_id || null

  useEffect(() => {
    getRunDetails(runId, attemptId)
      .then(data => setRunDetails(data))
      .catch(err => console.error(err))
  }, [runId, attemptId])

  const loadBox = () => getBox(runId, attemptId)
    .then(data => {
      setPokemon((data || []).filter(p => p.status === 'Captured' || p.status === 'Dead'))
      setLoaded(true)
    })
    .catch(err => console.error(err))

  useEffect(() => { loadBox() }, [runId, attemptId]) // eslint-disable-line react-hooks/exhaustive-deps

  // Guest runs store only what the player typed; fill in the species
  // reference data (typing, stats, ability slots) the API rows already carry.
  useEffect(() => {
    const missing = [...new Set(pokemon.filter(p => p.hp == null && !p._speciesLookedUp).map(p => p.species_id))]
    if (missing.length === 0) return
    let cancelled = false
    Promise.all(missing.map(id => getSpeciesSummary(id, gameId).then(summary => [id, summary]).catch(() => [id, null])))
      .then(entries => {
        if (cancelled) return
        const bySpecies = new Map(entries)
        setPokemon(prev => prev.map(p => {
          if (!bySpecies.has(p.species_id)) return p
          const summary = bySpecies.get(p.species_id)
          if (!summary) return { ...p, _speciesLookedUp: true }
          const { species_id: _id, name: _name, ...reference } = summary
          return { ...reference, ...p, _speciesLookedUp: true }
        }))
      })
    return () => { cancelled = true }
  }, [pokemon, gameId])

  useEffect(() => {
    getParty(runId, attemptId)
      .then(data => setPartyPokemonIds(new Set((data || []).map(p => p.pokemon_id))))
      .catch(err => console.error(err))
  }, [runId, attemptId, partyRefreshKey])

  const living = useMemo(() => pokemon.filter(p => p.status === 'Captured'), [pokemon])
  const fallen = useMemo(() => pokemon.filter(p => p.status === 'Dead'), [pokemon])
  const selected = pokemon.find(p => p.pokemon_id === selectedId) || null

  // A #fallen link (the old Graveyard URL) lands on the fallen section.
  useEffect(() => {
    if (!loaded || window.location.hash !== '#fallen') return
    document.getElementById('fallen')?.scrollIntoView({ block: 'start' })
  }, [loaded])

  // Evolvability is per species, so a stale entry for a species no longer
  // in the box is harmless and nothing needs resetting.
  useEffect(() => {
    if (living.length === 0) return
    let cancelled = false
    const uniqueIds = [...new Set(living.map(p => p.species_id))]
    Promise.all(
      uniqueIds.map(id =>
        apiFetch(`/api/evolutions/${id}`)
          .then(res => res.json())
          .then(data => ({ id, canEvolve: Array.isArray(data) && data.length > 0 }))
          .catch(() => ({ id, canEvolve: false }))
      )
    ).then(results => {
      if (!cancelled) setEvolvableSpecies(new Set(results.filter(r => r.canEvolve).map(r => r.id)))
    })
    return () => { cancelled = true }
  }, [living])

  const patchPokemon = (pokemonId, patch) => {
    setPokemon(prev => prev.map(p => (p.pokemon_id === pokemonId ? { ...p, ...patch } : p)))
  }

  const handleAddToParty = (p) => {
    addToParty(runId, attemptId, p.pokemon_id)
      .then(() => setPartyRefreshKey(k => k + 1))
      .catch(err => console.error('Failed to add to party:', err))
  }

  const handleRemoveFromParty = (p) => {
    removeFromParty(runId, attemptId, p.pokemon_id)
      .then(() => setPartyRefreshKey(k => k + 1))
      .catch(err => console.error('Failed to remove from party:', err))
  }

  const handleDead = (p) => {
    updateEncounterStatus(runId, attemptId, withStatusPayload(p, { status: 'Dead' }))
      .then(() => {
        patchPokemon(p.pokemon_id, { status: 'Dead' })
        setStatsRefreshKey(k => k + 1)
        return removeFromParty(runId, attemptId, p.pokemon_id)
      })
      .then(() => setPartyRefreshKey(k => k + 1))
      .catch(err => console.error('Failed to mark fallen:', err))
  }

  const handleRevive = (p) => {
    updateEncounterStatus(runId, attemptId, withStatusPayload(p, { status: 'Captured' }))
      .then(() => {
        patchPokemon(p.pokemon_id, { status: 'Captured' })
        setStatsRefreshKey(k => k + 1)
      })
      .catch(err => console.error('Failed to revive:', err))
  }

  const handleEvolve = (p) => {
    setEvolveTarget(p)
    setEvolveOptions(null)
    apiFetch(`/api/evolutions/${p.species_id}`)
      .then(res => res.json())
      .then(data => setEvolveOptions(Array.isArray(data) ? data : []))
      .catch(err => { console.error('Failed to fetch evolutions:', err); setEvolveOptions([]) })
  }

  const closeEvolve = () => { setEvolveTarget(null); setEvolveOptions(null) }

  const handleConfirmEvolve = (toSpeciesId) => {
    updateEncounterStatus(runId, attemptId, withStatusPayload(evolveTarget, { species_id: toSpeciesId }))
      .then(() => {
        closeEvolve()
        setPartyRefreshKey(k => k + 1)
        return loadBox()
      })
      .catch(err => console.error('Failed to evolve:', err))
  }

  const renderGrid = (list, emptyText) => (
    list.length === 0 ? (
      <p className="box-section__empty">{emptyText}</p>
    ) : (
      <div className="box-grid">
        {list.map(p => (
          <BoxTile
            key={p.pokemon_id}
            pokemon={p}
            selected={p.pokemon_id === selectedId}
            inParty={partyPokemonIds.has(p.pokemon_id)}
            onSelect={entry => setSelectedId(prev => (prev === entry.pokemon_id ? null : entry.pokemon_id))}
          />
        ))}
      </div>
    )
  )

  return (
    <div className="attempt-page" style={{ paddingTop: '120px', paddingBottom: '40px' }}>
      {evolveTarget !== null && (
        // z-index clears the fixed header; the panel scrolls so a long
        // evolution list stays reachable on a phone.
        <div
          onClick={closeEvolve}
          style={{
            position: 'fixed', inset: 0,
            backgroundColor: 'rgba(0,0,0,0.7)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            padding: '16px', overflowY: 'auto', overscrollBehavior: 'contain',
            zIndex: 3000
          }}
        >
          <div
            onClick={event => event.stopPropagation()}
            style={{
              background: 'var(--surface)', border: '1px solid var(--border-strong)', borderRadius: '10px',
              padding: '28px 32px', maxWidth: '420px', width: '100%',
              maxHeight: 'calc(100svh - 32px)', overflowY: 'auto',
              boxSizing: 'border-box', textAlign: 'center'
            }}
          >
            <h2 style={{ marginTop: 0, color: 'var(--text-primary)' }}>Evolve {evolveTarget.nickname || evolveTarget.species_name}?</h2>
            {evolveOptions === null ? (
              <p style={{ color: 'var(--text-secondary)' }}>Loading...</p>
            ) : evolveOptions.length === 0 ? (
              <p style={{ color: 'var(--text-secondary)' }}>No evolutions available.</p>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', marginTop: '16px' }}>
                {evolveOptions.map(opt => (
                  <button
                    type="button"
                    key={opt.to_species_id}
                    onClick={() => handleConfirmEvolve(opt.to_species_id)}
                    style={{
                      ...MODAL_BUTTON_STYLE,
                      display: 'flex', alignItems: 'center', justifyContent: 'center',
                      gap: '10px', minHeight: '48px',
                      color: 'var(--accent)', borderColor: 'var(--accent-border)', background: 'var(--accent-bg)'
                    }}
                  >
                    <Sprite speciesId={opt.to_species_id} size={48} />
                    {opt.name}
                  </button>
                ))}
              </div>
            )}
            <button type="button" onClick={closeEvolve} style={{ ...MODAL_BUTTON_STYLE, marginTop: '20px' }}>Cancel</button>
          </div>
        </div>
      )}

      <AttemptHeader runId={runId} attemptId={attemptNumber} runDetails={runDetails} backToAttempt partyRefreshKey={partyRefreshKey} statsOpen={statsOpen} onToggleStats={() => setStatsOpen(v => !v)} />

      <div className="attempt-page__content" style={{ maxWidth: '1380px', margin: '0 auto', padding: '0 28px', position: 'relative' }}>
        <AttemptSidePanel runId={runId} attemptId={attemptNumber} statsRefreshKey={statsRefreshKey} statsOpen={statsOpen} onToggleStats={() => setStatsOpen(v => !v)} />

        <div className="attempt-page__body attempt-page__body--inset box-page" style={{ padding: '20px', textAlign: 'left' }}>
          <div className={`box-page__layout${selected ? ' box-page__layout--open' : ''}`}>
            <div className="box-page__sections">
              <section className="box-section" aria-labelledby="box-living-heading">
                <h2 id="box-living-heading" className="box-section__title">
                  Box <span className="box-section__count">{living.length} alive</span>
                </h2>
                {renderGrid(living, loaded ? 'No Pokemon in the box yet.' : 'Loading…')}
              </section>

              <section id="fallen" className="box-section box-section--fallen" aria-labelledby="box-fallen-heading">
                <h2 id="box-fallen-heading" className="box-section__title">
                  Fallen <span className="box-section__count">{fallen.length} lost</span>
                </h2>
                {renderGrid(fallen, loaded ? 'No fallen Pokemon. Keep it that way.' : 'Loading…')}
              </section>
            </div>

            <aside className={`box-page__summary${selected ? ' box-page__summary--open' : ''}`} onClick={() => setSelectedId(null)}>
              <div onClick={event => event.stopPropagation()}>
                {selected ? (
                  <PokemonSummary
                    key={selected.pokemon_id}
                    pokemon={selected}
                    gameId={gameId}
                    runId={runId}
                    attemptId={attemptNumber}
                    inParty={partyPokemonIds.has(selected.pokemon_id)}
                    canEvolve={evolvableSpecies.has(selected.species_id)}
                    onAddToParty={handleAddToParty}
                    onRemoveFromParty={handleRemoveFromParty}
                    onEvolve={handleEvolve}
                    onDead={handleDead}
                    onRevive={handleRevive}
                    onClose={() => setSelectedId(null)}
                  />
                ) : (
                  <div className="box-page__summary-placeholder">
                    Select a Pokemon to see its summary.
                  </div>
                )}
              </div>
            </aside>
          </div>
        </div>
      </div>
    </div>
  )
}

export default Box
