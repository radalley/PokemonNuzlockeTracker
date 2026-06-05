import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import SiteHeader from '../components/SiteHeader'
import { useAuth } from '../contexts/AuthContext'
import PokemonFeed from '../components/PokemonFeed'
import { getRuns } from '../utils/dataLayer'
import { apiFetch } from '../utils/api'

function Home() {
  const navigate = useNavigate()
  const { user, loading: authLoading } = useAuth()
  const [hasRuns, setHasRuns] = useState(false)
  const [runsLoading, setRunsLoading] = useState(true)
  const [backendReady, setBackendReady] = useState(false)

  useEffect(() => {
    let cancelled = false
    apiFetch('/api/games')
      .then(() => { if (!cancelled) setBackendReady(true) })
      .catch(() => { if (!cancelled) setBackendReady(true) })
    return () => { cancelled = true }
  }, [])

  useEffect(() => {
    let cancelled = false

    async function loadRunAvailability() {
      if (authLoading) return

      setRunsLoading(true)
      try {
        const runs = await getRuns(Boolean(user))
        if (!cancelled) {
          setHasRuns(Array.isArray(runs) && runs.length > 0)
        }
      } catch {
        if (!cancelled) {
          setHasRuns(false)
        }
      } finally {
        if (!cancelled) {
          setRunsLoading(false)
        }
      }
    }

    loadRunAvailability()
    return () => {
      cancelled = true
    }
  }, [authLoading, user])

  const loadDisabled = runsLoading || !hasRuns
  const actionsDisabled = !backendReady

  return (
    <div className="home-page">
      <SiteHeader logoClickable={false} />

      <div className="home-feed-layer" aria-hidden="true">
        <PokemonFeed speed={28} columns={8} className="pokemon-feed--background" />
      </div>

      <main className="home-main">
        <div className="home-main-panel">
          <img className="home-logo" src="/sprites/Lockley_Logo.gif" alt="Lockley" />
          <h2>A Multi-Game Pokémon Nuzlocke Tracker</h2>
          <p className="home-auth-note">
            {user ? `Signed in as ${user.display_name}` : 'Sign in to sync your runs across laptop and PC.'}
          </p>
          <div className="home-actions">
            {!backendReady && (
              <p style={{ fontSize: '0.82em', color: 'var(--text-secondary)', margin: '0 0 8px', textAlign: 'center' }}>
                Connecting to server — this can take up to a minute after inactivity…
              </p>
            )}
            <button
              className={`home-action-button${actionsDisabled ? ' is-disabled' : ''}`}
              onClick={() => !actionsDisabled && navigate('/new-run')}
              disabled={actionsDisabled}
              aria-disabled={actionsDisabled}
              title={actionsDisabled ? 'Waiting for server…' : 'Start a new run'}
            >
              {actionsDisabled ? 'Loading…' : 'New Game'}
            </button>
            <button
              className={`home-action-button${actionsDisabled || loadDisabled ? ' is-disabled' : ''}`}
              onClick={() => !actionsDisabled && !loadDisabled && navigate('/load-run')}
              disabled={actionsDisabled || loadDisabled}
              aria-disabled={actionsDisabled || loadDisabled}
              title={actionsDisabled ? 'Waiting for server…' : loadDisabled ? 'No runs available yet' : 'Load an existing run'}
            >
              Load Game
            </button>
            <button className="home-action-button" onClick={() => navigate('/guides')}>Guides</button>
          </div>
        </div>
      </main>

      <footer className="home-footer">
        <div >Lockley Nuzlocke Tracker BETA — Built by Riley Dalley · 
        <a href="https://github.com/radalley/PokemonNuzlockeTracker"> GitHub</a> </div>
        Pokemon and its trademarks are ©1995-2023 Nintendo/Creatures Inc./GAME FREAK inc. TM, ® and © 1995-2023 Nintendo.
      </footer>
    </div>
  )
}

export default Home
