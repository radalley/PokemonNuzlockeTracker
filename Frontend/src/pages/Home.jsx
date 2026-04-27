import { useNavigate } from 'react-router-dom'
import SiteHeader from '../components/SiteHeader'
import { useAuth } from '../contexts/AuthContext'
import PokemonFeed from '../components/PokemonFeed'

function Home() {
  const navigate = useNavigate()
  const { user } = useAuth()

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
            <button className="home-action-button" onClick={() => navigate('/new-run')}>New Game</button>
            <button className="home-action-button" onClick={() => navigate('/load-run')}>Load Game</button>
            <button className="home-action-button" onClick={() => navigate('/guides')}>Guides</button>
          </div>
        </div>
      </main>

      <footer className="home-footer">
        <div >Lockley Nuzlocke Tracker BETAv0.1 — Built by Riley Dalley ·
        <a href="https://github.com/radalley/PokemonNuzlockeTracker">GitHub</a> </div>
        Pokemon and its trademarks are ©1995-2023 Nintendo/Creatures Inc./GAME FREAK inc. TM, ® and © 1995-2023 Nintendo.
      </footer>
    </div>
  )
}

export default Home