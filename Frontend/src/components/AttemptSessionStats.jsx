import { useEffect, useState } from 'react'
import { getSessionStats } from '../utils/dataLayer'

function StatItem({ label, value, compact = false }) {
  return (
    <div style={{ width: compact ? '100%' : 'auto', minWidth: compact ? 0 : '130px', boxSizing: 'border-box', border: '1px solid #2f3340', borderRadius: '6px', padding: '8px 10px', background: '#1d2028' }}>
      <div style={{ fontSize: '0.72em', color: '#99a2b5', textTransform: 'uppercase', letterSpacing: '0.04em' }}>{label}</div>
      <div style={{ marginTop: '4px', fontSize: '1.05em', color: '#e8ecf5', fontWeight: 'bold' }}>{value}</div>
    </div>
  )
}

function BadgeStatItem({ badgeIds = [], compact = false }) {
  return (
    <div style={{ width: compact ? '100%' : 'auto', minWidth: compact ? 0 : '130px', boxSizing: 'border-box', border: '1px solid #2f3340', borderRadius: '6px', padding: '8px 10px', background: '#1d2028' }}>
      <div style={{ fontSize: '0.72em', color: '#99a2b5', textTransform: 'uppercase', letterSpacing: '0.04em' }}>Badges Earned</div>
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
          <div style={{ width: '100%', textAlign: 'center', fontSize: '1.05em', color: '#e8ecf5', fontWeight: 'bold' }}>0</div>
        )}
      </div>
    </div>
  )
}

function AttemptSessionStats({ runId, attemptId, refreshKey = 0, compact = false }) {
  const [stats, setStats] = useState(null)

  useEffect(() => {
    const controller = new AbortController()
    getSessionStats(runId, attemptId, controller.signal)
      .then(data => setStats(data))
      .catch(err => { if (err.name !== 'AbortError') console.error(err) })
    return () => controller.abort()
  }, [runId, attemptId, refreshKey])

  return (
    <div style={{ width: '100%', boxSizing: 'border-box', margin: '10px 0 16px 0', border: '1px solid #343a47', borderRadius: '8px', padding: '10px', background: '#171920', overflow: 'hidden' }}>
      <div style={{ fontSize: '0.8em', color: '#8d97ab', marginBottom: '8px' }}> Run\] Stats</div>
      {!stats ? (
        <div style={{ fontSize: '0.8em', color: '#7f8798' }}>Loading...</div>
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
