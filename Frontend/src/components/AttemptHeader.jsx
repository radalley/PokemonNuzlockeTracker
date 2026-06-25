import { useState, useEffect, useRef } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import Sprite from './Sprite'
import HeaderAuthMenu from './HeaderAuthMenu'
import { getAttempts, getParty, createAttempt, removeFromParty } from '../utils/dataLayer'

function PartySlot({ member, slot, onRemove }) {
  const [hovered, setHovered] = useState(false)
  const slotSize = 'clamp(44px, 4.8vw, 64px)'

  if (!member) {
    return (
      <div style={{
        width: slotSize,
        aspectRatio: '1 / 1',
        border: '1px solid var(--border-strong)',
        borderRadius: '10px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        fontSize: '0.6em',
        color: 'var(--text-secondary)',
        boxShadow: '0 2px 6px rgba(0,0,0,0.4)',
        boxSizing: 'border-box',
      }}>
        {slot}
      </div>
    )
  }

  const isShiny = member.shiny === 'True' || member.shiny === true

  return (
    <div
      onClick={() => onRemove(member.pokemon_id)}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      title="Drop from party"
      style={{
        width: slotSize,
        aspectRatio: '1 / 1',
        borderRadius: '10px',
        cursor: 'pointer',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        backgroundColor: hovered ? 'rgba(229,85,85,0.15)' : 'var(--border)',
        border: hovered ? '2px solid #e55' : '2px solid transparent',
        transition: 'border-color 0.15s, background-color 0.15s',
        boxSizing: 'border-box',
        boxShadow: '0 2px 6px rgba(0,0,0,0.4)',
      }}
    >
      <Sprite speciesId={member.species_id} size={52} shiny={isShiny} style={{ width: '82%', height: '82%' }} />
    </div>
  )
}

function AttemptHeader({ runId, attemptId, runDetails, backToAttempt = false, partyRefreshKey = 0, onPartyChange = null, statsOpen = true, onToggleStats = null, debugOpen = true, onToggleDebug = null }) {
  const navigate = useNavigate()
  const location = useLocation()
  const [attempts, setAttempts] = useState([])
  const [showRunMenu, setShowRunMenu] = useState(false)
  const [showAttemptFlyout, setShowAttemptFlyout] = useState(false)
  const runMenuRef = useRef(null)
  const [party, setParty] = useState([])
  const [logoLoadFailed, setLogoLoadFailed] = useState(false)

  const gameLogoSrc = runDetails?.game_name
    ? `/sprites/Game Logos/Pokemon_${runDetails.game_name.replace(/\s+/g, '_')}.png`
    : null

  useEffect(() => {
    const controller = new AbortController()
    getAttempts(runId)
      .then(data => setAttempts(data || []))
      .catch(err => { if (err.name !== 'AbortError') console.error(err) })
    return () => controller.abort()
  }, [runId])

  useEffect(() => {
    const controller = new AbortController()
    getParty(runId, attemptId)
      .then(data => setParty(data || []))
      .catch(err => { if (err.name !== 'AbortError') console.error(err) })
    return () => controller.abort()
  }, [runId, attemptId, partyRefreshKey])

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (runMenuRef.current && !runMenuRef.current.contains(event.target)) {
        setShowRunMenu(false)
        setShowAttemptFlyout(false)
      }
    }

    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  useEffect(() => {
    setLogoLoadFailed(false)
  }, [gameLogoSrc])

  const handleNewAttempt = () => {
    createAttempt(runId)
      .then(data => {
        setShowRunMenu(false)
        setShowAttemptFlyout(false)
        window.location.href = `/attempt/${runId}/${data.attempt_number}`
      })
  }

  const handleRemoveFromParty = (pokemonId) => {
    removeFromParty(runId, attemptId, pokemonId)
      .then(() => {
        setParty(prev => prev.filter(p => p.pokemon_id !== pokemonId))
        if (onPartyChange) onPartyChange()
      })
      .catch(err => console.error('Failed to remove from party:', err))
  }

  const btnStyle = { padding: '6px 14px', fontSize: '0.8em', cursor: 'pointer', borderRadius: '999px', border: '1px solid var(--border-strong)', background: 'var(--surface-mid)', color: 'var(--text-secondary)', font: 'inherit' }
  const menuItemStyle = { display: 'block', width: '100%', padding: '8px 12px', border: 0, borderBottom: '1px solid var(--border)', background: 'transparent', color: 'var(--text-secondary)', cursor: 'pointer', font: 'inherit', fontSize: '0.8em', textAlign: 'left', boxSizing: 'border-box' }
  const isAttemptPage = location.pathname.startsWith('/attempt/')
  const isBoxPage = location.pathname.startsWith('/box/')
  const isGraveyardPage = location.pathname.startsWith('/graveyard/')

  return (
    <header style={{
      display: 'flex',
      justifyContent: 'space-between',
      alignItems: 'center',
      padding: '10px',
      borderBottom: '1px solid var(--border-strong)',
      position: 'fixed',
      top: 0,
      left: 0,
      right: 0,
      zIndex: 1000,
      backgroundColor: 'var(--surface-deep)',
      gap: '12px',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flex: 1, minWidth: 0 }}>
        <div
          ref={runMenuRef}
          style={{ position: 'relative', minWidth: 0 }}
        >
          <button
            type="button"
            onClick={() => setShowRunMenu(open => !open)}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '10px',
              minWidth: 0,
              maxWidth: 'min(360px, 34vw)',
              padding: '4px 8px',
              border: '1px solid transparent',
              borderRadius: '12px',
              background: showRunMenu ? 'var(--surface-mid)' : 'transparent',
              color: 'var(--text-primary)',
              cursor: 'pointer',
              font: 'inherit',
              textAlign: 'left',
            }}
          >
            <span style={{ width: 'clamp(92px, 12vw, 138px)', height: '50px', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
              {gameLogoSrc && !logoLoadFailed ? (
                <img
                  src={gameLogoSrc}
                  alt={`${runDetails?.game_name || 'Pokemon'} logo`}
                  onError={() => setLogoLoadFailed(true)}
                  style={{ maxWidth: '100%', maxHeight: '100%', objectFit: 'contain' }}
                />
              ) : (
                <span style={{ fontSize: '0.72em', color: 'var(--text-secondary)', textAlign: 'center' }}>Game Art</span>
              )}
            </span>
            <span style={{ minWidth: 0 }}>
              <span style={{ display: 'block', color: 'var(--text-primary)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: 'min(220px, 20vw)' }}>
                {runDetails?.name || 'Run Name'}
              </span>
              <span style={{ display: 'block', marginTop: '3px', color: 'var(--text-secondary)', fontSize: '0.72em' }}>Attempt {attemptId}</span>
            </span>
          </button>

          {showRunMenu && (
            <div style={{
              position: 'absolute',
              top: 'calc(100% + 6px)',
              left: 0,
              zIndex: 2000,
              background: 'var(--surface)',
              border: '1px solid var(--border-strong)',
              borderRadius: '10px',
              minWidth: '170px',
              overflow: 'visible',
              boxShadow: '0 12px 28px rgba(0,0,0,0.32)',
            }}>
              <button type="button" onClick={() => { setShowRunMenu(false); navigate('/') }} style={{ ...menuItemStyle, color: 'var(--text-primary)' }}>Main Menu</button>
              {onToggleStats && (
                <button type="button" onClick={() => { setShowRunMenu(false); onToggleStats() }} style={menuItemStyle}>{statsOpen ? 'Hide Stats' : 'Stats'}</button>
              )}
              {!debugOpen && onToggleDebug && (
                <button type="button" onClick={() => { setShowRunMenu(false); onToggleDebug() }} style={menuItemStyle}>Debug</button>
              )}
              {attempts.length > 0 && (
                <div
                  onMouseEnter={() => setShowAttemptFlyout(true)}
                  style={{ position: 'relative' }}
                >
                  <button
                    type="button"
                    onClick={() => setShowAttemptFlyout(open => !open)}
                    style={{ ...menuItemStyle, display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '16px' }}
                  >
                    <span>Change Attempt</span>
                    <span style={{ color: 'var(--text-secondary)' }}>›</span>
                  </button>
                  {showAttemptFlyout && (
                    <div style={{
                      position: 'absolute',
                      top: 0,
                      left: 'calc(100% + 6px)',
                      zIndex: 2001,
                      minWidth: '150px',
                      background: 'var(--surface)',
                      border: '1px solid var(--border-strong)',
                      borderRadius: '10px',
                      overflow: 'hidden',
                      boxShadow: '0 12px 28px rgba(0,0,0,0.32)',
                    }}>
                      {attempts.map(attempt => (
                        <button
                          type="button"
                          key={attempt.attempt_number}
                          onClick={() => { setShowRunMenu(false); setShowAttemptFlyout(false); window.location.href = `/attempt/${runId}/${attempt.attempt_number}` }}
                          style={{
                            ...menuItemStyle,
                            fontWeight: attempt.attempt_number === parseInt(attemptId) ? 'bold' : 'normal',
                            color: attempt.attempt_number === parseInt(attemptId) ? 'var(--text-primary)' : 'var(--text-secondary)',
                          }}
                        >
                          Attempt {attempt.attempt_number}
                        </button>
                      ))}
                      <button type="button" onClick={handleNewAttempt} style={{ ...menuItemStyle, color: '#6cf', borderTop: '1px solid var(--border-strong)' }}>
                        + New Attempt
                      </button>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      <div style={{ display: 'flex', gap: '10px', alignItems: 'center', justifyContent: 'center', flexShrink: 1, minWidth: 0 }}>
        {Array.from({ length: 6 }, (_, i) => {
          const slot = i + 1
          const member = party.find(p => p.party_slot === slot)
          return (
            <PartySlot
              key={slot}
              member={member}
              slot={slot}
              onRemove={handleRemoveFromParty}
            />
          )
        })}
      </div>

      <div style={{ display: 'flex', gap: '10px', alignItems: 'center', flex: 1, justifyContent: 'flex-end', minWidth: 0 }}>
        {backToAttempt && !isAttemptPage && (
          <button onClick={() => navigate(`/attempt/${runId}/${attemptId}`)} style={btnStyle}>
            Attempt
          </button>
        )}
        {!isBoxPage && <button onClick={() => navigate(`/box/${runId}/${attemptId}`)} style={btnStyle}>Box</button>}
        {!isGraveyardPage && <button onClick={() => navigate(`/graveyard/${runId}/${attemptId}`)} style={btnStyle}>Graveyard</button>}
        <HeaderAuthMenu />
      </div>
    </header>
  )
}

export default AttemptHeader
