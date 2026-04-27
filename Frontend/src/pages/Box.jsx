import { useState, useEffect } from 'react'
import { apiFetch } from '../utils/api'
import { useParams } from 'react-router-dom'
import AttemptHeader from '../components/AttemptHeader'
import AttemptSidePanel from '../components/AttemptSidePanel'
import PokemonCard from '../components/PokemonCard'
import Sprite from '../components/Sprite'
import {
  getRunDetails,
  getBox,
  getParty,
  addToParty,
  removeFromParty,
  updateEncounterStatus,
} from '../utils/dataLayer'

function Box() {
  const { runId, attemptId } = useParams()
  const [runDetails, setRunDetails] = useState(null)
  const [pokemon, setPokemon] = useState([])
  const [statsRefreshKey, setStatsRefreshKey] = useState(0)

  useEffect(() => {
    const controller = new AbortController()
    getRunDetails(runId, attemptId)
      .then(data => setRunDetails(data))
      .catch(err => { if (err.name !== 'AbortError') console.error(err) })
    return () => controller.abort()
  }, [runId, attemptId])

  useEffect(() => {
    const controller = new AbortController()
    getBox(runId, attemptId)
      .then(data => setPokemon((data || []).filter(p => p.status === 'Captured')))
      .catch(err => { if (err.name !== 'AbortError') console.error(err) })
    return () => controller.abort()
  }, [runId, attemptId])

  const [partyRefreshKey, setPartyRefreshKey] = useState(0)
  const [partyPokemonIds, setPartyPokemonIds] = useState(new Set())

  useEffect(() => {
    const controller = new AbortController()
    getParty(runId, attemptId)
      .then(data => setPartyPokemonIds(new Set((data || []).map(p => p.pokemon_id))))
      .catch(err => { if (err.name !== 'AbortError') console.error(err) })
    return () => controller.abort()
  }, [runId, attemptId, partyRefreshKey])

  const handleAddToParty = (p) => {
    addToParty(runId, attemptId, p.pokemon_id)
      .then(() => setPartyRefreshKey(k => k + 1))
      .catch(err => console.error('Failed to add to party:', err))
  }

  const handleDead = (p) => {
    updateEncounterStatus(runId, attemptId, {
      ...p,
      status: 'Dead',
      bonus_location: p.bonus_location || p.secondary_sort_order || 0,
    })
      .then(() => {
        setPokemon(prev => prev.filter(x => x.pokemon_id !== p.pokemon_id))
        setStatsRefreshKey(k => k + 1)
        removeFromParty(runId, attemptId, p.pokemon_id)
          .then(() => setPartyRefreshKey(k => k + 1))
      })
      .catch(err => console.error('Failed to mark dead:', err))
  }

  const handleRemoveFromParty = (p) => {
    removeFromParty(runId, attemptId, p.pokemon_id)
      .then(() => setPartyRefreshKey(k => k + 1))
      .catch(err => console.error('Failed to remove from party:', err))
  }

  const [evolveTarget, setEvolveTarget] = useState(null)
  const [evolveOptions, setEvolveOptions] = useState(null)
  const [evolvableSpecies, setEvolvableSpecies] = useState(new Set())

  useEffect(() => {
    if (pokemon.length === 0) { setEvolvableSpecies(new Set()); return }
    const uniqueIds = [...new Set(pokemon.map(p => p.species_id))]
    Promise.all(
      uniqueIds.map(id =>
        apiFetch(`/api/evolutions/${id}`)
          .then(res => res.json())
          .then(data => ({ id, canEvolve: data.length > 0 }))
          .catch(() => ({ id, canEvolve: false }))
      )
    ).then(results => {
      setEvolvableSpecies(new Set(results.filter(r => r.canEvolve).map(r => r.id)))
    })
  }, [pokemon])

  const handleEvolve = (p) => {
    setEvolveTarget(p)
    setEvolveOptions(null)
    apiFetch(`/api/evolutions/${p.species_id}`)
      .then(res => res.json())
      .then(data => setEvolveOptions(data))
      .catch(err => console.error('Failed to fetch evolutions:', err))
  }

  const handleConfirmEvolve = (toSpeciesId) => {
    updateEncounterStatus(runId, attemptId, {
      ...evolveTarget,
      species_id: toSpeciesId,
      bonus_location: evolveTarget.bonus_location || evolveTarget.secondary_sort_order || 0,
    })
      .then(() => {
        getBox(runId, attemptId)
          .then(data => setPokemon((data || []).filter(p => p.status === 'Captured')))
        setEvolveTarget(null)
        setEvolveOptions(null)
      })
      .catch(err => console.error('Failed to evolve:', err))
  }

  return (
    <div style={{ paddingTop: '120px', paddingBottom: '40px' }}>
      {evolveTarget !== null && (
        <div style={{
          position: 'fixed', inset: 0,
          backgroundColor: 'rgba(0,0,0,0.7)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          zIndex: 1000
        }}>
          <div style={{
            background: '#1e1f26', border: '1px solid #444', borderRadius: '10px',
            padding: '28px 32px', maxWidth: '420px', width: '90%', textAlign: 'center'
          }}>
            <h2 style={{ marginTop: 0, color: '#f3f4f6' }}>Evolve {evolveTarget.nickname || evolveTarget.species_name}?</h2>
            {evolveOptions === null ? (
              <p style={{ color: '#aaa' }}>Loading...</p>
            ) : evolveOptions.length === 0 ? (
              <p style={{ color: '#aaa' }}>No evolutions available.</p>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', marginTop: '16px' }}>
                {evolveOptions.map(opt => (
                  <button
                    key={opt.to_species_id}
                    onClick={() => handleConfirmEvolve(opt.to_species_id)}
                    style={{
                      display: 'flex', alignItems: 'center', justifyContent: 'center',
                      gap: '10px', padding: '8px 16px', fontSize: '0.9em',
                      cursor: 'pointer', color: '#7ec8e3', borderColor: '#7ec8e3'
                    }}
                  >
                    <Sprite speciesId={opt.to_species_id} size={48} />
                    {opt.name}
                  </button>
                ))}
              </div>
            )}
            <button
              onClick={() => { setEvolveTarget(null); setEvolveOptions(null) }}
              style={{ marginTop: '20px', padding: '6px 16px', cursor: 'pointer', fontSize: '0.85em' }}
            >Cancel</button>
          </div>
        </div>
      )}
      <AttemptHeader runId={runId} attemptId={parseInt(attemptId)} runDetails={runDetails} backToAttempt partyRefreshKey={partyRefreshKey} />

      <div style={{ maxWidth: '1380px', margin: '0 auto', padding: '0 28px', position: 'relative' }}>
        <AttemptSidePanel runId={runId} attemptId={parseInt(attemptId)} statsRefreshKey={statsRefreshKey} />

        <div style={{ padding: '20px', textAlign: 'left' }}>
          <h2 style={{ marginBottom: '16px', fontSize: '1.1em', color: '#aaa' }}>
            Box — Attempt {attemptId} ({pokemon.length} caught)
          </h2>

          {pokemon.length === 0 ? (
            <p style={{ color: '#555' }}>No pokemon recorded yet.</p>
          ) : (
            <div style={{
              display: 'flex', flexWrap: 'wrap', gap: '14px', justifyContent: 'center',
            }}>
              {pokemon.map(p => (
                <PokemonCard key={p.pokemon_id} pokemon={p} inParty={partyPokemonIds.has(p.pokemon_id)} onAddToParty={handleAddToParty} onRemoveFromParty={handleRemoveFromParty} onDead={handleDead} onEvolve={evolvableSpecies.has(p.species_id) ? handleEvolve : undefined} runId={runId} attemptId={parseInt(attemptId)} />
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default Box

