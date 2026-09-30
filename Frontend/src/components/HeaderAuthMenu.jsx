import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import useHoverCapable from '../utils/useHoverCapable'
import { Button, MenuItem } from './Button'

function HeaderAuthMenu() {
  const { user, openAuthDialog, logout } = useAuth()
  const navigate = useNavigate()
  const [menuOpen, setMenuOpen] = useState(false)
  const wrapperRef = useRef(null)
  const hoverCapable = useHoverCapable()

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
        <Button className="site-header__auth-button" onClick={() => openAuthDialog('login')}>
          Sign In
        </Button>
        <Button tone="accent" appearance="solid" className="site-header__auth-button is-primary" onClick={() => openAuthDialog('register')}>
          Create Account
        </Button>
      </div>
    )
  }

  const initial = String(user.display_name || user.email || '?').trim().charAt(0).toUpperCase()

  return (
    <div
      ref={wrapperRef}
      className="site-header__auth site-header__auth--menu"
      onMouseEnter={hoverCapable ? () => setMenuOpen(true) : undefined}
      onMouseLeave={hoverCapable ? () => setMenuOpen(false) : undefined}
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
          <MenuItem disabled title="Settings coming soon">
            Settings
          </MenuItem>
          {user.account_type === 'admin' && (
            <MenuItem
              onClick={() => {
                setMenuOpen(false)
                navigate('/admin/reports')
              }}
            >
              Reports
            </MenuItem>
          )}
          {user.account_type === 'admin' && (
            <MenuItem
              onClick={() => {
                setMenuOpen(false)
                navigate('/admin/placement')
              }}
            >
              Placement
            </MenuItem>
          )}
          <MenuItem tone="danger" onClick={logout}>
            Sign Out
          </MenuItem>
        </div>
      )}
    </div>
  )
}

export default HeaderAuthMenu
