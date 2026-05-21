import { useEffect, useState } from 'react'
import { getSessionStats } from '../utils/dataLayer'

function StatItem({ label, value, compact = false }) {
  return (
    <div style={{ width: compact ? '100%' : 'auto', minWidth: compact ? 0 : '130px', boxSizing: 'border-box', border: '1px solid var(--border-strong)', borderRadius: '6px', padding: '8px 10px', background: 'var(--surface-mid)' }}>
      <div style={{ fontSize: '0.72em', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>{label}</div>
      <div style={{ marginTop: '4px', fontSize: '1.05em', color: 'var(--text-primary)', fontWeight: 'bold' }}>{value}</div>
    </div>
  )
}

function BadgeStatItem({ badgeIds = [], compact = false }) {
  return (
    <div style={{ width: compact ? '100%' : 'auto', minWidth: compact ? 0 : '130px', boxSizing: 'border-box', border: '1px solid var(--border-strong)', borderRadius: '6px', padding: '8px 10px', background: 'var(--surface-mid)' }}>
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

function StarterButton({ label, color, selected, onClick }) {
  return (
    <button
      type="button"
      onClick={onClick}
      style={{
        flex: 1,
        padding: '5px 8px',
        backgroundColor: selected ? color : 'var(--surface-deep)',
        border: '1px solid var(--border-strong)',
        borderRadius: '6px',
        cursor: 'pointer',
        color: selected ? '#111' : 'var(--text-secondary)',
        font: 'inherit',
        fontSize: '0.85em',
      }}
    >
      {label}
    </button>
  )
}

function AttemptSessionStats({ runId, attemptId, refreshKey = 0, compact = false, starter = '', onStarterChange = null, isOpen = true, onToggle = null }) {
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

  return (
    <div style={{ width: '100%', boxSizing: 'border-box', margin: '10px 0 16px 0', border: '1px solid var(--border-strong)', borderRadius: '8px', padding: '10px', background: 'var(--surface)', overflow: 'hidden', boxShadow: '0 2px 6px rgba(0,0,0,0.4)' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
        <div style={{ fontSize: '0.8em', color: 'var(--text-secondary)' }}>Run Stats</div>
        {onToggle && <button onClick={onToggle} title="Minimize" style={miniBtn}>−</button>}
      </div>

      {onStarterChange && (
        <div style={{ marginBottom: '10px', border: '1px solid var(--border-strong)', borderRadius: '6px', padding: '8px 10px', background: 'var(--surface-mid)' }}>
          <div style={{ fontSize: '0.72em', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.04em', marginBottom: '6px' }}>Starter</div>
          <div style={{ display: 'flex', gap: '6px' }}>
            <StarterButton label="Fire" color="#ff6b6b" selected={starter === 'Fire'} onClick={() => onStarterChange('Fire')} />
            <StarterButton label="Grass" color="#51cf66" selected={starter === 'Grass'} onClick={() => onStarterChange('Grass')} />
            <StarterButton label="Water" color="#74c0fc" selected={starter === 'Water'} onClick={() => onStarterChange('Water')} />
          </div>
        </div>
      )}

      {!stats ? (
        <div style={{ fontSize: '0.8em', color: 'var(--text-secondary)' }}>Loading...</div>
      ) : (
        <div style={{ display: 'flex', minWidth: 0, flexDirection: compact ? 'column' : 'row', flexWrap: compact ? 'nowrap' : 'wrap', gap: '8px' }}>
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

