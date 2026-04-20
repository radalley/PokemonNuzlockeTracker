import { useNavigate } from 'react-router-dom'
import HeaderAuthMenu from './HeaderAuthMenu'

function SiteHeader({ showHomeButton = false, logoClickable = true }) {
  const navigate = useNavigate()

  return (
    <header className="site-header">
      <div className="site-header__left">
        {logoClickable ? (
          <button type="button" className="site-header__logo-button" onClick={() => navigate('/')}>
            <img className="site-header__logo" src="/sprites/Lockley_Logo.gif" alt="Lockley" />
          </button>
        ) : (
          <div className="site-header__logo-static">
            <img className="site-header__logo" src="/sprites/Lockley_Logo.gif" alt="Lockley" />
          </div>
        )}
        {showHomeButton && (
          <button type="button" className="site-header__nav-button" onClick={() => navigate('/')}>
            Home
          </button>
        )}
      </div>

      <HeaderAuthMenu />
    </header>
  )
}

export default SiteHeader