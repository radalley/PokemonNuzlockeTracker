import { useState, useEffect } from 'react'
import { apiFetch } from '../utils/api'
import { useParams } from 'react-router-dom'
import AttemptHeader from '../components/AttemptHeader'
import AttemptSidePanel from '../components/AttemptSidePanel'
import PokemonCard from '../components/PokemonCard'

function Graveyard() {
  const { runId, attemptId } = useParams()
  const [runDetails, setRunDetails] = useState(null)
  const [pokemon, setPokemon] = useState([])
  const [statsRefreshKey, setStatsRefreshKey] = useState(0)

  useEffect(() => {
    const controller = new AbortController()
    apiFetch(`/api/runs/${runId}/${attemptId}`, { signal: controller.signal })
      .then(res => res.json())
      .then(data => setRunDetails(data))
      .catch(err => { if (err.name !== 'AbortError') console.error(err) })
    return () => controller.abort()
  }, [runId, attemptId])

  useEffect(() => {
    const controller = new AbortController()
    apiFetch(`/api/box/${runId}/${attemptId}`, { signal: controller.signal })
      .then(res => res.json())
      .then(data => setPokemon(data.filter(p => p.status === 'Dead')))
      .catch(err => { if (err.name !== 'AbortError') console.error(err) })
    return () => controller.abort()
  }, [runId, attemptId])

  const handleRevive = (pokemonToRevive) => {
    apiFetch('/api/pokebank/save', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        run_id: parseInt(runId),
        attempt_number: parseInt(attemptId),
        location_id: pokemonToRevive.location_id,
        species_id: pokemonToRevive.species_id,
        nickname: pokemonToRevive.nickname || null,
        nature: pokemonToRevive.nature || null,
        status: 'Captured',
        shiny: pokemonToRevive.shiny || null,
        pokemon_id: pokemonToRevive.pokemon_id,
      })
    })
      .then(() => {
        setPokemon(prev => prev.filter(entry => entry.pokemon_id !== pokemonToRevive.pokemon_id))
        setStatsRefreshKey(key => key + 1)
      })
      .catch(err => console.error('Failed to revive pokemon:', err))
  }

  return (
    <div style={{ paddingTop: '120px', paddingBottom: '40px' }}>
      <AttemptHeader runId={parseInt(runId)} attemptId={parseInt(attemptId)} runDetails={runDetails} backToAttempt />

      <div style={{ maxWidth: '1380px', margin: '0 auto', padding: '0 28px', position: 'relative' }}>
        <AttemptSidePanel runId={parseInt(runId)} attemptId={parseInt(attemptId)} statsRefreshKey={statsRefreshKey} />

        <div style={{ padding: '20px', textAlign: 'left' }}>
          <h2 style={{ marginBottom: '16px', fontSize: '1.1em', color: '#aaa' }}>
            Graveyard — Attempt {attemptId} ({pokemon.length} fallen)
          </h2>

          {pokemon.length === 0 ? (
            <p style={{ color: '#555' }}>No fallen pokemon — nice work.</p>
          ) : (
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '14px', justifyContent: 'center' }}>
              {pokemon.map(p => (
                <PokemonCard
                  key={p.pokemon_id}
                  pokemon={p}
                  onRevive={handleRevive}
                  runId={parseInt(runId)}
                  attemptId={parseInt(attemptId)}
                />
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default Graveyard
