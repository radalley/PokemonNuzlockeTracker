import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import SiteHeader from '../components/SiteHeader'
import Sprite from '../components/Sprite'
import { useAuth } from '../contexts/AuthContext'
import { getRuns, deleteRun } from '../utils/dataLayer'

function getGameLogoSrc(gameName) {
  return `/sprites/Game Logos/Pokemon_${String(gameName || '').replace(/\s+/g, '_')}.png`
}

function formatTimestamp(value) {
  if (!value) return ''
  return String(value).slice(0, 10)
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
            </div>
            <div className="load-run-summary__title-row">
              <span className="load-run-summary__run-name">{run.run_name}</span>
              <span className="load-run-summary__attempts">{totalAttempts} Attempt{totalAttempts === 1 ? '' : 's'}</span>
            </div>
            <div className="load-run-summary__status-row">
              <span className="load-run-summary__range">{statusTimeLabel}</span>
            </div>
          </div>
        </div>
      </td>

      <td className="load-run-cell load-run-cell--latest-attempt">
        <div className="load-run-latest-attempt">
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

          <BadgeStrip badgeIds={run.latest_attempt_badges} />
        </div>
      </td>

      <td className="load-run-cell load-run-cell--actions">
        <div className="load-run-actions-row">
          <button type="button" className="page-action-button page-action-button--success" onClick={onLoad} disabled={!run.latest_attempt}>Load</button>
          <button type="button" className="page-action-button page-action-button--danger" onClick={onDelete}>Delete</button>
        </div>
      </td>
    </tr>
  )
}

function LoadRun() {
  const navigate = useNavigate()
  const { user } = useAuth()
  const [runs, setRuns] = useState([])
  const [confirmDelete, setConfirmDelete] = useState(null)
  const [genFilter, setGenFilter] = useState(null)

  const handleDeleteRun = async (run_id) => {
    const data = await deleteRun(run_id)
    if (data?.success) {
      setRuns(prev => prev.filter(r => String(r.run_id) !== String(run_id)))
    }
    setConfirmDelete(null)
  }

  useEffect(() => {
    getRuns(!!user)
      .then(data => setRuns(data || []))
      .catch(() => setRuns([]))
  }, [user])

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
              <button type="button" className="page-action-button" onClick={() => setConfirmDelete(null)}>Cancel</button>
              <button
                type="button"
                className="page-action-button page-action-button--danger"
                onClick={() => handleDeleteRun(confirmDelete)}
              >
                Yes, Delete Permanently
              </button>
            </div>
          </div>
        </div>
      )}
      <h1>Load Run</h1>
      {(() => {
        const generations = [...new Set(runs.map(r => r.generation).filter(g => g != null))].sort((a, b) => a - b)
        const visibleRuns = genFilter === null ? runs : runs.filter(r => r.generation === genFilter)
        return (
          <>
            {generations.length > 1 && (
              <div className="load-run-filters">
                <button
                  type="button"
                  className={`load-run-filter-btn${genFilter === null ? ' is-active' : ''}`}
                  onClick={() => setGenFilter(null)}
                >
                  All
                </button>
                {generations.map(gen => (
                  <button
                    key={gen}
                    type="button"
                    className={`load-run-filter-btn${genFilter === gen ? ' is-active' : ''}`}
                    onClick={() => setGenFilter(gen)}
                  >
                    Gen {gen}
                  </button>
                ))}
              </div>
            )}
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
                  {visibleRuns.map(r => (
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
          </>
        )
      })()}
    </div>
  )
}

export default LoadRun
