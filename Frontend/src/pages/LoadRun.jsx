import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import SiteHeader from '../components/SiteHeader'
import Sprite from '../components/Sprite'
import { apiFetch } from '../utils/api'

function getGameLogoSrc(gameName) {
  return `/sprites/Game Logos/Pokemon_${String(gameName || '').replace(/\s+/g, '_')}.png`
}

function formatTimestamp(value) {
  if (!value) return ''
  const normalized = String(value).replace(' ', 'T')
  const date = new Date(normalized)
  if (Number.isNaN(date.getTime())) return String(value)

  return date.toLocaleDateString([], {
    year: 'numeric',
    month: 'short',
    day: 'numeric'
  })
}

function isRunWon(value) {
  const normalized = String(value ?? '').trim().toLowerCase()
  return normalized === '1' || normalized === 'true' || normalized === 'yes' || normalized === 'won'
}

function BadgeStrip({ badgeIds = [] }) {
  const earnedBadgeIds = Array.from(
    new Set(
      (badgeIds || [])
        .map(Number)
        .filter(badgeId => Number.isInteger(badgeId) && badgeId > 0)
    )
  ).sort((left, right) => left - right)

  if (earnedBadgeIds.length === 0) {
    return <div className="load-run-badge-empty">No badges earned</div>
  }

  return (
    <div className="load-run-badge-strip" aria-label="Latest attempt badges earned">
      {earnedBadgeIds.map(badgeId => (
        <div key={badgeId} className="load-run-badge-slot is-earned" title={`Badge ${badgeId}`}>
          <img
            className="load-run-badge-slot__image"
            src={`/sprites/Badges/${badgeId}.png`}
            alt={`Badge ${badgeId}`}
          />
        </div>
      ))}
    </div>
  )
}

function StatPill({ label, value }) {
  return (
    <div className="load-run-attempt-stat">
      <span className="load-run-attempt-stat__label">{label}</span>
      <span className="load-run-attempt-stat__value">{value}</span>
    </div>
  )
}

function LoadRunRow({ run, onLoad, onDelete }) {
  const [logoFailed, setLogoFailed] = useState(false)
  const won = isRunWon(run.victory_item)
  const totalAttempts = Number(run.total_attempts || 0)
  const createdLabel = formatTimestamp(run.created_at)
  const beatenLabel = formatTimestamp(run.beaten_at)
  const statusTimeLabel = won && beatenLabel
    ? `${createdLabel} - ${beatenLabel}`
    : createdLabel
  const latestAttemptStats = run.latest_attempt_stats || null

  useEffect(() => {
    setLogoFailed(false)
  }, [run.run_id, run.game_name])

  return (
    <tr className="load-run-row">
      <td className="load-run-cell load-run-cell--summary">
        <div className="load-run-summary">
          <div className="load-run-summary__media">
            <div className="load-run-summary__logo-cell">
              {!logoFailed ? (
                <img
                  className="load-run-summary__logo"
                  src={getGameLogoSrc(run.game_name)}
                  alt={`Pokemon ${run.game_name}`}
                  onError={() => setLogoFailed(true)}
                />
              ) : (
                <div className="load-run-summary__logo-fallback">No Logo</div>
              )}
            </div>
          </div>

          <div className="load-run-summary__meta">
            <div className="load-run-summary__top-row">
              <span className={`load-run-summary__badge${won ? ' is-won' : ''}`}>
                {won ? 'Won' : 'In Progress'}
              </span>
              <span className="load-run-summary__separator">-</span>
              <span className="load-run-summary__attempts">{totalAttempts} Attempt{totalAttempts === 1 ? '' : 's'}</span>
            </div>
            <div className="load-run-summary__title-row">
              <span className="load-run-summary__run-name">{run.run_name}</span>
            </div>
            <div className="load-run-summary__status-row">
              <span className="load-run-summary__range">{statusTimeLabel}</span>
            </div>
          </div>
        </div>
      </td>

      <td className="load-run-cell load-run-cell--latest-attempt">
        <div className="load-run-latest-attempt">
          <BadgeStrip badgeIds={run.latest_attempt_badges} />

          <div className="load-run-party" aria-label={`Latest party for ${run.run_name}`}>
            {run.latest_party?.length ? (
              run.latest_party.map(member => (
                <div key={member.pokemon_id} className="load-run-party__member" title={member.nickname || member.species_name}>
                  <Sprite speciesId={member.species_id} size={42} shiny={member.shiny === 'True' || member.shiny === true} />
                </div>
              ))
            ) : (
              <div className="load-run-party__empty">No party</div>
            )}
          </div>

          <div className="load-run-attempt-stats">
            <StatPill label="Caught" value={latestAttemptStats?.pokemon_caught ?? 0} />
            <StatPill label="Dead" value={latestAttemptStats?.pokemon_dead ?? 0} />
            <StatPill label="Trainers" value={latestAttemptStats?.trainers_defeated ?? 0} />
          </div>
        </div>
      </td>

      <td className="load-run-cell load-run-cell--actions">
        <div className="load-run-actions-row">
          <button type="button" onClick={onLoad} disabled={!run.latest_attempt}>Load</button>
          <button type="button" className="load-run-delete-button" onClick={onDelete}>Delete</button>
        </div>
      </td>
    </tr>
  )
}

function LoadRun() {
  const navigate = useNavigate()
  const [runs, setRuns] = useState([])
  const [confirmDelete, setConfirmDelete] = useState(null)

  const handleDeleteRun = (run_id) => {
    apiFetch(`/api/delete-run`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ run_id: run_id})
      })
      .then(res => res.json())
      .then(data => {
        if (data.success) {
          setRuns(prev => prev.filter(r => r.run_id !== run_id))
        }
      })
      .catch(err => console.error('Failed to delete run:', err))
    setConfirmDelete(null)
    }
  

  useEffect(() => {
    apiFetch('/api/runs')
      .then(res => res.json())
      .then(data => setRuns(data))
  }, [])

  return (
    <div className="load-run-page">
      <SiteHeader showHomeButton />

      {confirmDelete !== null && (
        <div style={{
          position: 'fixed', inset: 0,
          backgroundColor: 'rgba(0,0,0,0.6)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          zIndex: 1000
        }}>
          <div style={{
            backgroundColor: '', color: '#ffffff',
            borderColor: '#ffffff', borderWidth: '2px', borderStyle: 'solid',
            padding: '32px', borderRadius: '8px',
            maxWidth: '400px', width: '90%', textAlign: 'center'
          }}>
            <h2 style={{ marginTop: 0 }}>Delete Run?</h2>
            <p>
              This will permanently delete this run and <strong>all associated attempts</strong>.
              This action <strong>cannot be undone</strong>.
            </p>
            <p style={{ color: '#c0392b', fontWeight: 'bold' }}>
              All data will be lost.
            </p>
            <div style={{ display: 'flex', justifyContent: 'center', gap: '12px', marginTop: '24px' }}>
              <button onClick={() => setConfirmDelete(null)}>Cancel</button>
              <button
                onClick={() => handleDeleteRun(confirmDelete)}
                style={{ backgroundColor: '#c0392b', color: '#fff', border: 'none', padding: '6px 14px', cursor: 'pointer' }}>
                Yes, Delete Permanently
              </button>
            </div>
          </div>
        </div>
      )}
      <h1>Load Run</h1>
      <div className="load-run-table-wrap">
        <table className="load-run-table">
          <thead>
            <tr>
              <th>Run</th>
              <th>Latest Attempt</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {runs.map(r => (
              <LoadRunRow
                key={r.run_id}
                run={r}
                onLoad={() => navigate(`/attempt/${r.run_id}/${r.latest_attempt}`)}
                onDelete={() => setConfirmDelete(r.run_id)}
              />
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

export default LoadRun