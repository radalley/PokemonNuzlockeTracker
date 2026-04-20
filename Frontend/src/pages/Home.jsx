import { useEffect } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import SiteHeader from '../components/SiteHeader'
import { useAuth } from '../contexts/AuthContext'

function Home() {
  const navigate = useNavigate()
  const location = useLocation()
  const { user, openAuthDialog } = useAuth()

  useEffect(() => {
    if (location.state?.from && !user) {
      openAuthDialog('login')
    }
  }, [location.state, openAuthDialog, user])

  function handleProtectedNavigation(path) {
    if (!user) {
      openAuthDialog('login')
      return
    }
    navigate(path)
  }

  return (
    <div className="home-page">
      <SiteHeader logoClickable={false} />

      <main className="home-main">
        <img className="home-logo" src="/sprites/Lockley_Logo.gif" alt="Lockley" />
        <h2>A Multi-game Pokémon Nuzlocke Tracker</h2>
        <p className="home-auth-note">
          {user ? `Signed in as ${user.display_name}` : 'Sign in to sync your runs across laptop and PC.'}
        </p>
        <div className="home-actions">
          <button className="home-action-button" onClick={() => handleProtectedNavigation('/new-run')}>New Game</button>
          <button className="home-action-button" onClick={() => handleProtectedNavigation('/load-run')}>Load Game</button>
          <button className="home-action-button" onClick={() => navigate('/guides')}>Guides</button>
        </div>
      </main>

      
        
      <footer className="home-footer">
        <div>Dalley Nuzlocke Tracker v0.1 — Built by Riley Dalley ·
        <a href="https://github.com/radalley/PokemonNuzlockeTracker">GitHub</a> </div>
        Pokemon and its trademarks are ©1995-2023 Nintendo/Creatures Inc./GAME FREAK inc. TM, ® and © 1995-2023 Nintendo.
      </footer>
    </div>
  )
}

export default Home