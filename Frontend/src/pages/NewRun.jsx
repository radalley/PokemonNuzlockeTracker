import { useNavigate } from 'react-router-dom'
import { apiFetch } from '../utils/api'
import { useState, useEffect } from 'react'
import SiteHeader from '../components/SiteHeader'
import { useAuth } from '../contexts/AuthContext'
import { createRun } from '../utils/dataLayer'

function getGameLogoSrc(gameName) {
  return `/sprites/Game Logos/Pokemon_${String(gameName || '').replace(/\s+/g, '_')}.png`
}

function GameRow({ game, isSelected, onSelect }) {
  // A hack without its own logo art falls back to its base game's logo
  // before giving up.
  const logoCandidates = [getGameLogoSrc(game.name)]
  if (game.base_game_name) logoCandidates.push(getGameLogoSrc(game.base_game_name))
  const [logoIndex, setLogoIndex] = useState(0)

  useEffect(() => {
    setLogoIndex(0)
  }, [game.game_id, game.name])

  return (
    <button
      type="button"
      className={`new-run-game-row${isSelected ? ' is-selected' : ''}`}
      onClick={() => onSelect(game)}
    >
      <div className="new-run-game-logo-cell">
        {logoIndex < logoCandidates.length ? (
          <img
            className="new-run-game-logo"
            src={logoCandidates[logoIndex]}
            alt={game.is_rom_hack ? game.name : `Pokemon ${game.name}`}
            onError={() => setLogoIndex(index => index + 1)}
          />
        ) : (
          <div className="new-run-game-logo-placeholder">No Logo</div>
        )}
      </div>
      <div className="new-run-game-name">{game.is_rom_hack ? game.name : `Pokemon ${game.name}`}</div>
      <div className="new-run-game-meta">
        {game.is_rom_hack && game.base_game_name ? (
          <span style={{
            display: 'inline-block',
            padding: '2px 8px',
            borderRadius: '999px',
            border: '1px solid var(--accent-border)',
            color: 'var(--accent)',
            fontSize: '0.8em',
            marginRight: '8px',
          }}>
            Hack of {game.base_game_name}
          </span>
        ) : null}
        Gen {game.generation}
      </div>
    </button>
  )
}

function NewRun() {
  const navigate = useNavigate()
  const { user } = useAuth()
  const [gameid, setGameId] = useState('')
  const [runName, setRunName] = useState('')
  const [games, setGames] = useState([])
  const [selectedGame, setSelectedGame] = useState(null)
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
  const vanillaGames = filteredGames.filter(game => !game.is_rom_hack)
  const hackGames = filteredGames.filter(game => game.is_rom_hack)

  useEffect(() => {
    if (generations.length === 0) return
    if (selectedGeneration !== 'all' && !generations.includes(Number(selectedGeneration))) {
      setSelectedGeneration('all')
    }
  }, [generations.join(','), selectedGeneration])

  async function handleCreate() {
    if (!gameid || !runName) {
      alert('Please select a game and enter a run name')
      return
    }

    const gameMeta = selectedGame || games.find(g => String(g.game_id) === String(gameid)) || null
    const data = await createRun(!!user, gameid, runName, gameMeta)
    if (data?.success) {
      navigate(`/attempt/${data.run_id}/1`)
    }
  }

  return (
    <div className="new-run-page">
      <SiteHeader showHomeButton />

      <h1>New Run</h1>

      <div className="new-run-controls">
        <label className="new-run-field">
          <span>Selected Game</span>
          <select
            value={gameid}
            onChange={(e) => {
              const id = e.target.value
              setGameId(id)
              setSelectedGame(games.find(g => String(g.game_id) === id) || null)
            }}
          >
            <option value="">Select a game...</option>
            {games.filter(g => !g.is_rom_hack).map(g => (
              <option key={g.game_id} value={g.game_id}>
                Pokemon {g.name} (Gen {g.generation})
              </option>
            ))}
            {games.some(g => g.is_rom_hack) && (
              <optgroup label="ROM Hacks">
                {games.filter(g => g.is_rom_hack).map(g => (
                  <option key={g.game_id} value={g.game_id}>
                    {g.name}{g.base_game_name ? ` (Hack of ${g.base_game_name})` : ''}
                  </option>
                ))}
              </optgroup>
            )}
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
          <button type="button" className="page-action-button page-action-button--success" onClick={handleCreate}>Create</button>
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
          {vanillaGames.map(game => (
            <GameRow
              key={game.game_id}
              game={game}
              isSelected={String(game.game_id) === String(gameid)}
              onSelect={(selected) => {
                setGameId(String(selected.game_id))
                setSelectedGame(selected)
              }}
            />
          ))}
        </div>

        {hackGames.length > 0 && (
          <>
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: '10px',
              margin: '18px 0 10px',
              color: 'var(--text-secondary)',
              fontSize: '0.8em',
              letterSpacing: '0.08em',
              textTransform: 'uppercase',
            }}>
              <span>ROM Hacks</span>
              <span style={{ flex: 1, height: '1px', background: 'var(--border-strong)' }} />
            </div>
            <div className="new-run-game-table" role="list">
              {hackGames.map(game => (
                <GameRow
                  key={game.game_id}
                  game={game}
                  isSelected={String(game.game_id) === String(gameid)}
                  onSelect={(selected) => {
                    setGameId(String(selected.game_id))
                    setSelectedGame(selected)
                  }}
                />
              ))}
            </div>
          </>
        )}
      </div>

    </div>
  )
}

export default NewRun
