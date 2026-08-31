import { useState, useEffect, useRef } from 'react'
import { createPortal } from 'react-dom'
import { useLocation, useNavigate } from 'react-router-dom'
import Sprite from './Sprite'
import HeaderAuthMenu from './HeaderAuthMenu'
import { getAttempts, getParty, createAttempt, removeFromParty, endAttempt } from '../utils/dataLayer'
import useHoverCapable from '../utils/useHoverCapable'

function PartySlot({ member, slot, onRemove, hoverCapable }) {
  const [hovered, setHovered] = useState(false)
  const [armed, setArmed] = useState(false)
  const slotSize = 'clamp(44px, 4.8vw, 64px)'

  // The only warning that a click drops the Pokemon from the party is the
  // red hover tint, which touch devices never show. Ask for a second tap
  // there instead, and disarm on a timer so a stray tap cannot linger.
  useEffect(() => {
    if (!armed) return undefined
    const timer = setTimeout(() => setArmed(false), 3000)
    return () => clearTimeout(timer)
  }, [armed])

  if (!member) {
    return (
      <div className="attempt-header__party-slot" style={{
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
      className="attempt-header__party-slot"
      onClick={() => {
        if (hoverCapable) { onRemove(member.pokemon_id); return }
        if (!armed) { setArmed(true); return }
        setArmed(false)
        onRemove(member.pokemon_id)
      }}
      onMouseEnter={hoverCapable ? () => setHovered(true) : undefined}
      onMouseLeave={hoverCapable ? () => setHovered(false) : undefined}
      title={armed ? 'Tap again to drop from party' : 'Drop from party'}
      style={{
        position: 'relative',
        width: slotSize,
        aspectRatio: '1 / 1',
        borderRadius: '10px',
        cursor: 'pointer',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        backgroundColor: hovered || armed ? 'rgba(229,85,85,0.15)' : 'var(--border)',
        border: hovered || armed ? '2px solid #e55' : '2px solid transparent',
        transition: 'border-color 0.15s, background-color 0.15s',
        boxSizing: 'border-box',
        boxShadow: '0 2px 6px rgba(0,0,0,0.4)',
      }}
    >
      <Sprite speciesId={member.species_id} size={52} shiny={isShiny} style={{ width: '82%', height: '82%' }} />
      {armed && (
        <span
          aria-hidden="true"
          style={{
            position: 'absolute',
            inset: 0,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            borderRadius: '8px',
            background: 'rgba(229,85,85,0.55)',
            color: '#fff',
            fontSize: '0.62em',
            fontWeight: 'bold',
            lineHeight: 1.1,
          }}
        >
          Drop?
        </span>
      )}
    </div>
  )
}

function AttemptHeader({ runId, attemptId, runDetails, backToAttempt = false, partyRefreshKey = 0, onPartyChange = null, statsOpen = true, onToggleStats = null, debugOpen = true, onToggleDebug = null, attemptOutcome = null }) {
  const navigate = useNavigate()
  const location = useLocation()
  const hoverCapable = useHoverCapable()
  const [attempts, setAttempts] = useState([])
  const [showRunMenu, setShowRunMenu] = useState(false)
  const [showAttemptFlyout, setShowAttemptFlyout] = useState(false)
  const runMenuRef = useRef(null)
  const [party, setParty] = useState([])
  const [logoLoadFailed, setLogoLoadFailed] = useState(false)
  const [showDeadDialog, setShowDeadDialog] = useState(false)
  const [deathNote, setDeathNote] = useState('')
  const [endingAttempt, setEndingAttempt] = useState(false)
  const [endError, setEndError] = useState('')
  // Pages that don't load attempt info (Box, Graveyard) still know the
  // outcome from the attempts list this header fetches anyway.
  const attemptIsDead = attemptOutcome
    ? attemptOutcome.outcome === 'dead'
    : attempts.some(a => Number(a.attempt_number) === Number(attemptId) && a.outcome === 'dead')

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

  const handleDeclareDead = () => {
    if (endingAttempt) return
    setEndingAttempt(true)
    setEndError('')
    endAttempt(runId, attemptId, { note: deathNote })
      .then(() => {
        setShowDeadDialog(false)
        window.location.href = `/attempt/${runId}/${attemptId}/summary`
      })
      .catch(err => setEndError(err.message || 'Failed to end attempt'))
      .finally(() => setEndingAttempt(false))
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
    <header className="attempt-header" style={{
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
      <div className="attempt-header__primary" style={{ display: 'flex', alignItems: 'center', gap: '10px', flex: 1, minWidth: 0 }}>
        <div
          ref={runMenuRef}
          className="attempt-header__run-control"
          style={{ position: 'relative', minWidth: 0 }}
        >
          <button
            className="attempt-header__run-button"
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
            <span className="attempt-header__game-logo" style={{ width: 'clamp(92px, 12vw, 138px)', height: '50px', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
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
            <span className="attempt-header__run-copy" style={{ minWidth: 0 }}>
              <span className="attempt-header__run-name" style={{ display: 'block', color: 'var(--text-primary)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: 'min(220px, 20vw)' }}>
                {runDetails?.name || 'Run Name'}
              </span>
              <span style={{ display: 'block', marginTop: '3px', color: attemptIsDead ? '#e05252' : 'var(--text-secondary)', fontSize: '0.72em' }}>
                Attempt {attemptId}{attemptIsDead ? ' ☠' : ''}
              </span>
            </span>
          </button>

          {showRunMenu && (
            <div className="attempt-header__run-menu" style={{
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
              {isAttemptPage && attemptOutcome && !attemptIsDead && (
                <button
                  type="button"
                  onClick={() => { setShowRunMenu(false); setDeathNote(''); setEndError(''); setShowDeadDialog(true) }}
                  style={{ ...menuItemStyle, color: '#e05252' }}
                >
                  Declare Attempt Dead
                </button>
              )}
              {attemptIsDead && (
                <button
                  type="button"
                  onClick={() => { setShowRunMenu(false); navigate(`/attempt/${runId}/${attemptId}/summary`) }}
                  style={{ ...menuItemStyle, color: '#f2b46b' }}
                >
                  Attempt Summary
                </button>
              )}
              {attempts.length > 0 && (
                <div
                  onMouseEnter={hoverCapable ? () => setShowAttemptFlyout(true) : undefined}
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
                    <div className="attempt-header__attempt-flyout" style={{
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
                          Attempt {attempt.attempt_number}{attempt.outcome === 'dead' ? ' ☠' : ''}
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

      <div className="attempt-header__party" style={{ display: 'flex', gap: '10px', alignItems: 'center', justifyContent: 'center', flexShrink: 1, minWidth: 0 }}>
        {Array.from({ length: 6 }, (_, i) => {
          const slot = i + 1
          const member = party.find(p => p.party_slot === slot)
          return (
            <PartySlot
              key={slot}
              member={member}
              slot={slot}
              onRemove={handleRemoveFromParty}
              hoverCapable={hoverCapable}
            />
          )
        })}
      </div>

      <div className="attempt-header__nav" style={{ display: 'flex', gap: '10px', alignItems: 'center', flex: 1, justifyContent: 'flex-end', minWidth: 0 }}>
        {attemptIsDead && (
          <button
            onClick={() => navigate(`/attempt/${runId}/${attemptId}/summary`)}
            className="attempt-header__nav-button"
            style={{ ...btnStyle, borderColor: '#f2b46b', color: '#f2b46b' }}
            title="This attempt has ended — view its summary"
          >
            ☠ Summary
          </button>
        )}
        {backToAttempt && !isAttemptPage && (
          <button className="attempt-header__nav-button" onClick={() => navigate(`/attempt/${runId}/${attemptId}`)} style={btnStyle}>
            Attempt
          </button>
        )}
        {!isBoxPage && <button className="attempt-header__nav-button" onClick={() => navigate(`/box/${runId}/${attemptId}`)} style={btnStyle}>Box</button>}
        {!isGraveyardPage && <button className="attempt-header__nav-button" onClick={() => navigate(`/graveyard/${runId}/${attemptId}`)} style={btnStyle}>Graveyard</button>}
        <HeaderAuthMenu />
      </div>

      {showDeadDialog && createPortal(
        // Rendered through a portal because this header is position:fixed
        // with a z-index, which traps any descendant's z-index inside its
        // stacking context — the page footer (same z-index, later in the
        // document) would otherwise paint over the Cancel / Declare Dead
        // buttons. The backdrop scrolls so the dialog stays reachable when
        // the on-screen keyboard shrinks the viewport.
        <div
          onClick={() => !endingAttempt && setShowDeadDialog(false)}
          style={{ position: 'fixed', inset: 0, backgroundColor: 'rgba(0,0,0,0.7)', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '16px', overflowY: 'auto', overscrollBehavior: 'contain', zIndex: 3000 }}
        >
          <div
            onClick={e => e.stopPropagation()}
            style={{ width: 'min(420px, calc(100vw - 32px))', maxHeight: 'calc(100svh - 32px)', overflowY: 'auto', background: 'var(--surface)', border: '1px solid var(--border-strong)', borderRadius: '12px', padding: '18px' }}
          >
            <div style={{ fontWeight: 'bold', color: '#e05252', fontSize: '1.05em', marginBottom: '6px' }}>
              Declare Attempt {attemptId} dead?
            </div>
            <div style={{ fontSize: '0.82em', color: 'var(--text-secondary)', marginBottom: '12px' }}>
              This ends the attempt and opens its summary. You can reopen it later if it was a mistake.
            </div>
            <textarea
              value={deathNote}
              onChange={e => setDeathNote(e.target.value)}
              placeholder="How did it end? (optional — e.g. crit on the last mon vs wild Excadrill)"
              rows={3}
              maxLength={500}
              style={{ width: '100%', boxSizing: 'border-box', resize: 'vertical', fontSize: '0.82em', padding: '8px', borderRadius: '8px', border: '1px solid var(--border-strong)', background: 'var(--surface-deep)', color: 'var(--text-primary)', font: 'inherit' }}
            />
            {endError && <div style={{ fontSize: '0.78em', color: '#e05252', marginTop: '6px' }}>{endError}</div>}
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px', marginTop: '12px' }}>
              <button type="button" onClick={() => setShowDeadDialog(false)} disabled={endingAttempt} style={btnStyle}>Cancel</button>
              <button
                type="button"
                onClick={handleDeclareDead}
                disabled={endingAttempt}
                style={{ ...btnStyle, borderColor: '#e05252', color: '#e05252', background: 'rgba(224,82,82,0.1)', cursor: endingAttempt ? 'wait' : 'pointer' }}
              >
                {endingAttempt ? 'Ending...' : 'Declare Dead'}
              </button>
            </div>
          </div>
        </div>,
        document.body
      )}
    </header>
  )
}

export default AttemptHeader
