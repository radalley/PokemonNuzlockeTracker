import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import Sprite from './Sprite'
import HeaderAuthMenu from './HeaderAuthMenu'

function PartySlot({ member, slot, onRemove }) {
  const [hovered, setHovered] = useState(false)
  if (!member) {
    return (
      <div style={{
        width: '64px', height: '64px', border: '1px solid #444', borderRadius: '4px',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        fontSize: '0.6em', color: '#444'
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
        width: '64px', height: '64px', borderRadius: '4px', cursor: 'pointer',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        backgroundColor: hovered ? 'rgba(229,85,85,0.15)' : '#2e2f3a',
        border: hovered ? '2px solid #e55' : '2px solid transparent',
        transition: 'border-color 0.15s, background-color 0.15s',
        boxSizing: 'border-box',
      }}
    >
      <Sprite speciesId={member.species_id} size={52} shiny={isShiny} />
    </div>
  )
}

function AttemptHeader({ runId, attemptId, runDetails, backToAttempt = false, partyRefreshKey = 0 }) {
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
    fetch(`/api/runs/${runId}/attempts`, { signal: controller.signal })
      .then(res => res.json())
      .then(data => setAttempts(data))
      .catch(err => { if (err.name !== 'AbortError') console.error(err) })
    return () => controller.abort()
  }, [runId])

  useEffect(() => {
    const controller = new AbortController()
    fetch(`/api/runs/${runId}/attempts/${attemptId}/party`, { signal: controller.signal })
      .then(res => res.json())
      .then(data => setParty(data))
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
    fetch(`/api/runs/${runId}/attempts`, { method: 'POST' })
      .then(res => res.json())
      .then(data => {
        setShowAttemptMenu(false)
        window.location.href = `/attempt/${runId}/${data.attempt_number}`
      })
  }

  const handleRemoveFromParty = (pokemonId) => {
    fetch(`/api/runs/${runId}/attempts/${attemptId}/party/${pokemonId}`, { method: 'DELETE' })
      .then(() => setParty(prev => prev.filter(p => p.pokemon_id !== pokemonId)))
      .catch(err => console.error('Failed to remove from party:', err))
  }

  const btnStyle = { padding: '4px 8px', fontSize: '0.8em', cursor: 'pointer' }
  return (
    <header style={{
      display: 'flex', justifyContent: 'space-between', alignItems: 'center',
      padding: '10px', borderBottom: '1px solid #ccc',
      position: 'fixed', top: 0, left: 0, right: 0, zIndex: 1000, backgroundColor: '#16171d'
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
        <div style={{ width: '138px', height: '50px', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
          {gameLogoSrc && !logoLoadFailed ? (
            <img
              src={gameLogoSrc}
              alt={`${runDetails?.game_name || 'Pokemon'} logo`}
              onError={() => setLogoLoadFailed(true)}
              style={{ maxWidth: '100%', maxHeight: '100%', objectFit: 'contain' }}
            />
          ) : (
            <div style={{ fontSize: '0.72em', color: '#667085', textAlign: 'center' }}>Game Art</div>
          )}
        </div>
        <div>
          {/* <div style={{ fontWeight: 'bold' }}>{runDetails?.game_name || 'Game Name'}</div> */}
          <div>{runDetails?.name || 'Run Name'}</div>
        </div>

        <div ref={attemptMenuRef} style={{ position: 'relative' }}>
          <button onClick={() => setShowAttemptMenu(m => !m)} style={btnStyle}>
            Attempt {attemptId} ▾
          </button>
          {showAttemptMenu && (
            <div style={{
              position: 'absolute', top: '100%', left: 0, zIndex: 2000,
              background: '#1e1f26', border: '1px solid #555', borderRadius: '4px', minWidth: '150px'
            }}>
              {attempts.map(a => (
                <div
                  key={a.attempt_number}
                  onClick={() => { setShowAttemptMenu(false); window.location.href = `/attempt/${runId}/${a.attempt_number}` }}
                  style={{
                    padding: '7px 12px', cursor: 'pointer', borderBottom: '1px solid #333',
                    fontWeight: a.attempt_number === parseInt(attemptId) ? 'bold' : 'normal',
                    color: a.attempt_number === parseInt(attemptId) ? '#fff' : '#aaa'
                  }}
                >
                  Attempt {a.attempt_number}
                </div>
              ))}
              <div
                onClick={handleNewAttempt}
                style={{ padding: '7px 12px', cursor: 'pointer', color: '#6cf', borderTop: '1px solid #555' }}
              >
                + New Attempt
              </div>
            </div>
          )}
        </div>

        <button onClick={() => navigate('/')} style={btnStyle}>Main Menu</button>
      </div>

      <div style={{ display: 'flex', gap: '10px' }}>
        {Array.from({ length: 6 }, (_, i) => {
          const slot = i + 1
          const member = party.find(p => p.party_slot === slot)
          return (
            <div key={slot} style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '3px' }}>
              <PartySlot
                member={member}
                slot={slot}
                onRemove={handleRemoveFromParty}
              />
              {member && (
                <div style={{ fontSize: '0.6em', color: '#ccc', maxWidth: '64px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', textAlign: 'center' }}>
                  {member.nickname || member.species_name}
                </div>
              )}
            </div>
          )
        })}
      </div>

      <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
        {backToAttempt && (
          <button onClick={() => navigate(`/attempt/${runId}/${attemptId}`)} style={btnStyle}>
            ← Attempt
          </button>
        )}
        <button onClick={() => navigate(`/box/${runId}/${attemptId}`)} style={btnStyle}>Box</button>
        <button onClick={() => navigate(`/graveyard/${runId}/${attemptId}`)} style={btnStyle}>Graveyard</button>
        <HeaderAuthMenu />
      </div>
    </header>
  )
}

export default AttemptHeader
