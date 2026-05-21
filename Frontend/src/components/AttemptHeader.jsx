import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import Sprite from './Sprite'
import HeaderAuthMenu from './HeaderAuthMenu'
import { getAttempts, getParty, createAttempt, removeFromParty } from '../utils/dataLayer'

function PartySlot({ member, slot, onRemove }) {
  const [hovered, setHovered] = useState(false)
  if (!member) {
    return (
      <div style={{
        width: '64px', height: '64px', border: '1px solid var(--border-strong)', borderRadius: '10px',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        fontSize: '0.6em', color: 'var(--text-secondary)', boxShadow: '0 2px 6px rgba(0,0,0,0.4)'
      }}>{slot}</div>
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
        width: '64px', height: '64px', borderRadius: '10px', cursor: 'pointer',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        backgroundColor: hovered ? 'rgba(229,85,85,0.15)' : 'var(--border)',
        border: hovered ? '2px solid #e55' : '2px solid transparent',
        transition: 'border-color 0.15s, background-color 0.15s',
        boxSizing: 'border-box', boxShadow: '0 2px 6px rgba(0,0,0,0.4)',
      }}
    >
      <Sprite speciesId={member.species_id} size={52} shiny={isShiny} />
    </div>
  )
}

function AttemptHeader({ runId, attemptId, runDetails, backToAttempt = false, partyRefreshKey = 0, onPartyChange = null, statsOpen = true, onToggleStats = null, debugOpen = true, onToggleDebug = null }) {
  const navigate = useNavigate()
  const [attempts, setAttempts] = useState([])
  const [showAttemptMenu, setShowAttemptMenu] = useState(false)
  const attemptMenuRef = useRef(null)
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
    const handleClickOutside = (e) => {
      if (attemptMenuRef.current && !attemptMenuRef.current.contains(e.target))
        setShowAttemptMenu(false)
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
        setShowAttemptMenu(false)
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
  return (
    <header style={{
      display: 'flex', justifyContent: 'space-between', alignItems: 'center',
      padding: '10px', borderBottom: '1px solid var(--border-strong)',
      position: 'fixed', top: 0, left: 0, right: 0, zIndex: 1000, backgroundColor: 'var(--surface-deep)'
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flex: 1 }}>
        <div style={{ width: '138px', height: '50px', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
          {gameLogoSrc && !logoLoadFailed ? (
            <img
              src={gameLogoSrc}
              alt={`${runDetails?.game_name || 'Pokemon'} logo`}
              onError={() => setLogoLoadFailed(true)}
              style={{ maxWidth: '100%', maxHeight: '100%', objectFit: 'contain' }}
            />
          ) : (
            <div style={{ fontSize: '0.72em', color: 'var(--text-secondary)', textAlign: 'center' }}>Game Art</div>
          )}
        </div>
        <div>
          {/* <div style={{ fontWeight: 'bold' }}>{runDetails?.game_name || 'Game Name'}</div> */}
          <div style={{ color: 'var(--text-primary)' }}>{runDetails?.name || 'Run Name'}</div>
        </div>

        <div ref={attemptMenuRef} style={{ position: 'relative' }}>
          <button onClick={() => setShowAttemptMenu(m => !m)} style={btnStyle}>
            Attempt {attemptId} ▾
          </button>
          {showAttemptMenu && (
            <div style={{
              position: 'absolute', top: '100%', left: 0, zIndex: 2000,
              background: 'var(--surface)', border: '1px solid var(--border-strong)', borderRadius: '4px', minWidth: '150px'
            }}>
              {attempts.map(a => (
                <div
                  key={a.attempt_number}
                  onClick={() => { setShowAttemptMenu(false); window.location.href = `/attempt/${runId}/${a.attempt_number}` }}
                  style={{
                    padding: '7px 12px', cursor: 'pointer', borderBottom: '1px solid var(--border)',
                    fontWeight: a.attempt_number === parseInt(attemptId) ? 'bold' : 'normal',
                    color: a.attempt_number === parseInt(attemptId) ? 'var(--text-primary)' : 'var(--text-secondary)'
                  }}
                >
                  Attempt {a.attempt_number}
                </div>
              ))}
              <div
                onClick={handleNewAttempt}
                style={{ padding: '7px 12px', cursor: 'pointer', color: '#6cf', borderTop: '1px solid var(--border-strong)' }}
              >
                + New Attempt
              </div>
            </div>
          )}
        </div>

        <button onClick={() => navigate('/')} style={btnStyle}>Main Menu</button>
        {!statsOpen && onToggleStats && (
          <button onClick={onToggleStats} style={btnStyle}>Stats</button>
        )}
      </div>

      <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
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

      <div style={{ display: 'flex', gap: '10px', alignItems: 'center', flex: 1, justifyContent: 'flex-end' }}>
        {backToAttempt && (
          <button onClick={() => navigate(`/attempt/${runId}/${attemptId}`)} style={btnStyle}>
            ← Attempt
          </button>
        )}
        {onToggleDebug && (
          <button onClick={onToggleDebug} style={btnStyle}>{debugOpen ? 'Debug −' : 'Debug'}</button>
        )}
        <button onClick={() => navigate(`/box/${runId}/${attemptId}`)} style={btnStyle}>Box</button>
        <button onClick={() => navigate(`/graveyard/${runId}/${attemptId}`)} style={btnStyle}>Graveyard</button>
        <HeaderAuthMenu />
      </div>
    </header>
  )
}

export default AttemptHeader
