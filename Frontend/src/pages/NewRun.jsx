import { useNavigate } from 'react-router-dom'
import { apiFetch } from '../utils/api'
import { useState, useEffect } from 'react'
import SiteHeader from '../components/SiteHeader'

function getGameLogoSrc(gameName) {
  return `/sprites/Game Logos/Pokemon_${String(gameName || '').replace(/\s+/g, '_')}.png`
}

function GameRow({ game, isSelected, onSelect }) {
  const [logoFailed, setLogoFailed] = useState(false)

  useEffect(() => {
    setLogoFailed(false)
  }, [game.game_id, game.name])

  return (
    <button
      type="button"
      className={`new-run-game-row${isSelected ? ' is-selected' : ''}`}
      onClick={() => onSelect(game)}
    >
      <div className="new-run-game-logo-cell">
        {!logoFailed ? (
          <img
            className="new-run-game-logo"
            src={getGameLogoSrc(game.name)}
            alt={`Pokemon ${game.name}`}
            onError={() => setLogoFailed(true)}
          />
        ) : (
          <div className="new-run-game-logo-placeholder">No Logo</div>
        )}
      </div>
      <div className="new-run-game-name">Pokemon {game.name}</div>
      <div className="new-run-game-meta">Gen {game.generation}</div>
    </button>
  )
}

function NewRun() {
  const navigate = useNavigate()
  const [gameid, setGameId] = useState('')
  const [runName, setRunName] = useState('')
  const [games, setGames] = useState([])
  const [selectedGeneration, setSelectedGeneration] = useState('all')

  useEffect(() => {
    apiFetch('/api/games')
      .then(res => res.json())
      .then(data => setGames(data))
  }, [])

  const generations = [...new Set(games.map(game => Number(game.generation)).filter(Number.isFinite))].sort((a, b) => a - b)
  const sortedGames = [...games].sort((a, b) => {
    const versionGroupDiff = Number(a.version_group_id) - Number(b.version_group_id)
    if (versionGroupDiff !== 0) return versionGroupDiff
    const generationDiff = Number(a.generation) - Number(b.generation)
    if (generationDiff !== 0) return generationDiff
    return String(a.name || '').localeCompare(String(b.name || ''))
  })
  const filteredGames = selectedGeneration === 'all'
    ? sortedGames
    : sortedGames.filter(game => Number(game.generation) === Number(selectedGeneration))

  useEffect(() => {
    if (generations.length === 0) return
    if (selectedGeneration !== 'all' && !generations.includes(Number(selectedGeneration))) {
      setSelectedGeneration('all')
    }
  }, [generations.join(','), selectedGeneration])

  function handleCreate() {
    if (!gameid || !runName) {
      alert('Please select a game and enter a run name')
      return
    }

    apiFetch('/api/runs', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ game_id: gameid, run_name: runName })
    })
      .then(res => res.json())
      .then(data => {
        if (data.success) {
          navigate(`/attempt/${data.run_id}/1`)
        }
      })
  }

  return (
    <div className="new-run-page">
      <SiteHeader showHomeButton />

      <h1>New Run</h1>

      <div className="new-run-controls">
        <label className="new-run-field">
          <span>Selected Game</span>
          <select value={gameid} onChange={(e) => setGameId(e.target.value)}>
            <option value="">Select a game...</option>
            {games.map(g => (
              <option key={g.game_id} value={g.game_id}>
                Pokemon {g.name} (Gen {g.generation})
              </option>
            ))}
          </select>
        </label>

        <label className="new-run-field">
          <span>Run Name</span>
          <input
            type="text"
            placeholder="Run name"
            value={runName}
            onChange={(e) => setRunName(e.target.value)}
          />
        </label>

        <div className="new-run-actions new-run-actions-top">
          <button onClick={handleCreate}>Create</button>
        </div>
      </div>

      <div className="new-run-picker">
        <div className="new-run-generation-bar">
          <button
            type="button"
            className={`new-run-generation-pill${selectedGeneration === 'all' ? ' is-selected' : ''}`}
            onClick={() => setSelectedGeneration('all')}
          >
            All
          </button>
          {generations.map(generation => (
            <button
              key={generation}
              type="button"
              className={`new-run-generation-pill${Number(selectedGeneration) === generation ? ' is-selected' : ''}`}
              onClick={() => setSelectedGeneration(generation)}
            >
              Gen {generation}
            </button>
          ))}
        </div>

        <div className="new-run-game-table" role="list">
          {filteredGames.map(game => (
            <GameRow
              key={game.game_id}
              game={game}
              isSelected={String(game.game_id) === String(gameid)}
              onSelect={(selected) => setGameId(String(selected.game_id))}
            />
          ))}
        </div>
      </div>

    </div>
  )
}

export default NewRun