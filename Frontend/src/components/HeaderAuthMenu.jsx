import { useEffect, useRef, useState } from 'react'
import { useAuth } from '../contexts/AuthContext'

function HeaderAuthMenu() {
  const { user, openAuthDialog, logout } = useAuth()
  const [menuOpen, setMenuOpen] = useState(false)
  const wrapperRef = useRef(null)

  useEffect(() => {
    if (!menuOpen) return undefined

    function handlePointerDown(event) {
      if (wrapperRef.current && !wrapperRef.current.contains(event.target)) {
        setMenuOpen(false)
      }
    }

    document.addEventListener('mousedown', handlePointerDown)
    return () => document.removeEventListener('mousedown', handlePointerDown)
  }, [menuOpen])

  if (!user) {
    return (
      <div className="site-header__auth">
        <button type="button" className="site-header__auth-button" onClick={() => openAuthDialog('login')}>
          Sign In
        </button>
        <button type="button" className="site-header__auth-button is-primary" onClick={() => openAuthDialog('register')}>
          Create Account
        </button>
      </div>
    )
  }

  const initial = String(user.display_name || user.email || '?').trim().charAt(0).toUpperCase()

  return (
    <div
      ref={wrapperRef}
      className="site-header__auth site-header__auth--menu"
      onMouseEnter={() => setMenuOpen(true)}
      onMouseLeave={() => setMenuOpen(false)}
    >
      <button
        type="button"
        className={`site-header__user-button${menuOpen ? ' is-open' : ''}`}
        onClick={() => setMenuOpen(open => !open)}
        aria-haspopup="menu"
        aria-expanded={menuOpen}
      >
        <span className="site-header__user-avatar" aria-hidden="true">{initial}</span>
        <span className="site-header__user-label">{user.display_name}</span>
      </button>

      {menuOpen && (
        <div className="site-header__auth-menu" role="menu">
          <div className="site-header__auth-menu-meta">
            <div className="site-header__auth-menu-name">{user.display_name}</div>
            <div className="site-header__auth-menu-email">{user.email}</div>
          </div>
          <button type="button" className="site-header__auth-menu-item is-disabled" disabled title="Settings coming soon">
            Settings
          </button>
          <button type="button" className="site-header__auth-menu-item" onClick={logout}>
            Sign Out
          </button>
        </div>
      )}
    </div>
  )
}

export default HeaderAuthMenu
