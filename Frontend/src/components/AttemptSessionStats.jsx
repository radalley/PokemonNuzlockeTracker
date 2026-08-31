import { useEffect, useState } from 'react'
import { getSessionStats } from '../utils/dataLayer'

function StatItem({ label, value, compact = false }) {
  return (
    <div className="attempt-session-stats__item" style={{ width: compact ? '100%' : 'auto', minWidth: compact ? 0 : '130px', boxSizing: 'border-box', border: '1px solid var(--border-strong)', borderRadius: '6px', padding: '8px 10px', background: 'var(--surface-mid)' }}>
      <div style={{ fontSize: '0.72em', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>{label}</div>
      <div style={{ marginTop: '4px', fontSize: '1.05em', color: 'var(--text-primary)', fontWeight: 'bold' }}>{value}</div>
    </div>
  )
}

function BadgeStatItem({ badgeIds = [], compact = false }) {
  return (
    <div className="attempt-session-stats__item attempt-session-stats__item--badges" style={{ width: compact ? '100%' : 'auto', minWidth: compact ? 0 : '130px', boxSizing: 'border-box', border: '1px solid var(--border-strong)', borderRadius: '6px', padding: '8px 10px', background: 'var(--surface-mid)' }}>
      <div style={{ fontSize: '0.72em', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>Badges Earned</div>
      <div style={{ marginTop: '6px', minHeight: '28px', display: 'flex', flexWrap: 'wrap', gap: '6px', alignItems: 'center', justifyContent: 'center' }}>
        {badgeIds.length > 0 ? (
          badgeIds.map(badgeId => (
            <img
              key={badgeId}
              src={`/sprites/Badges/${badgeId}.png`}
              alt={`Badge ${badgeId}`}
              title={`Badge ${badgeId}`}
              style={{ width: '24px', height: '24px', imageRendering: 'pixelated' }}
            />
          ))
        ) : (
          <div style={{ width: '100%', textAlign: 'center', fontSize: '1.05em', color: 'var(--text-primary)', fontWeight: 'bold' }}>0</div>
        )}
      </div>
    </div>
  )
}

function StarterButton({ label, color, selected, onClick, compact = false }) {
  return (
    <button
      type="button"
      className="attempt-session-stats__starter"
      onClick={onClick}
      style={{
        flex: compact ? '1 1 calc(50% - 6px)' : 1,
        minWidth: 0,
        padding: compact ? '5px 6px' : '5px 8px',
        backgroundColor: selected ? color : 'var(--surface-deep)',
        border: '1px solid var(--border-strong)',
        borderRadius: '6px',
        cursor: 'pointer',
        color: selected ? '#111' : 'var(--text-secondary)',
        font: 'inherit',
        fontSize: compact ? '0.74em' : '0.85em',
        lineHeight: 1.2,
        overflow: 'hidden',
        textOverflow: 'ellipsis',
        whiteSpace: 'nowrap',
        boxSizing: 'border-box',
      }}
    >
      {label}
    </button>
  )
}

const STARTER_OPTIONS = [
  { label: 'Fire', value: 'Fire', color: '#ff6b6b' },
  { label: 'Grass', value: 'Grass', color: '#51cf66' },
  { label: 'Water', value: 'Water', color: '#74c0fc' },
]

const YELLOW_EEVEE_OPTIONS = [
  { label: 'Vaporeon', value: 'Blue', color: '#74c0fc' },
  { label: 'Flareon', value: 'Red', color: '#ff6b6b' },
  { label: 'Jolteon', value: 'Yellow', color: '#ffd43b' },
]

function AttemptSessionStats({ runId, attemptId, refreshKey = 0, compact = false, starter = '', onStarterChange = null, showStarterControls = false, isOpen = true, onToggle = null, versionGroupId = null }) {
  const [stats, setStats] = useState(null)

  useEffect(() => {
    const controller = new AbortController()
    getSessionStats(runId, attemptId, controller.signal)
      .then(data => setStats(data))
      .catch(err => { if (err.name !== 'AbortError') console.error(err) })
    return () => controller.abort()
  }, [runId, attemptId, refreshKey])

  if (!isOpen) return null

  const miniBtn = { padding: '2px 8px', fontSize: '0.75em', cursor: 'pointer', borderRadius: '999px', border: '1px solid var(--border-strong)', background: 'var(--surface-mid)', color: 'var(--text-secondary)', font: 'inherit', lineHeight: '1.4' }
  const isYellow = Number(versionGroupId) === 2
  const starterOptions = isYellow ? YELLOW_EEVEE_OPTIONS : STARTER_OPTIONS

  return (
    <div className="attempt-session-stats" style={{ width: '100%', boxSizing: 'border-box', margin: '10px 0 16px 0', border: '1px solid var(--border-strong)', borderRadius: '8px', padding: '10px', background: 'var(--surface)', overflow: 'hidden', boxShadow: '0 2px 6px rgba(0,0,0,0.4)' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
        <div style={{ fontSize: '0.8em', color: 'var(--text-secondary)' }}>Run Stats</div>
        {onToggle && <button className="attempt-session-stats__toggle" onClick={onToggle} title="Minimize" style={miniBtn}>−</button>}
      </div>

      {showStarterControls && onStarterChange && (
        <div style={{ marginBottom: '10px', border: '1px solid var(--border-strong)', borderRadius: '6px', padding: '8px 10px', background: 'var(--surface-mid)' }}>
          <div style={{ fontSize: '0.72em', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.04em', marginBottom: '6px' }}>{isYellow ? 'Rival Eevee' : 'Starter'}</div>
          <div style={{ display: 'flex', gap: '6px', flexWrap: isYellow ? 'wrap' : 'nowrap', minWidth: 0 }}>
            {starterOptions.map(option => (
              <StarterButton
                key={option.value}
                label={option.label}
                color={option.color}
                selected={starter === option.value}
                onClick={() => onStarterChange(option.value)}
                compact={isYellow}
              />
            ))}
          </div>
        </div>
      )}

      {!stats ? (
        <div style={{ fontSize: '0.8em', color: 'var(--text-secondary)' }}>Loading...</div>
      ) : (
        <div className="attempt-session-stats__grid" style={{ display: 'flex', minWidth: 0, flexDirection: compact ? 'column' : 'row', flexWrap: compact ? 'nowrap' : 'wrap', gap: '8px' }}>
          <BadgeStatItem badgeIds={stats.badge_ids || []} compact={compact} />
          <StatItem label="Trainers Defeated" value={stats.trainers_defeated ?? 0} compact={compact} />
          <StatItem label="Pokemon Caught" value={stats.pokemon_caught ?? 0} compact={compact} />
          <StatItem label="Pokemon Dead" value={stats.pokemon_dead ?? 0} compact={compact} />
          <StatItem label="Pokemon Missed" value={stats.pokemon_missed ?? 0} compact={compact} />
        </div>
      )}
    </div>
  )
}

export default AttemptSessionStats

