import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import Sprite from '../components/Sprite'
import { getTrainerSpriteSrc } from '../components/trainerSprite'
import { getAttemptSummary, createAttempt, reopenAttempt } from '../utils/dataLayer'

const CARD = {
  border: '1px solid var(--border-strong)',
  borderRadius: '12px',
  background: 'var(--surface)',
  padding: '14px',
  boxShadow: '0 2px 6px rgba(0,0,0,0.4)',
}

const ACTION = {
  padding: '9px 16px',
  borderRadius: '999px',
  border: '1px solid var(--border-strong)',
  background: 'var(--surface-mid)',
  color: 'var(--text-primary)',
  cursor: 'pointer',
  font: 'inherit',
  fontSize: '0.88em',
}

function formatClass(trainerClass) {
  return trainerClass
    ? trainerClass.replace('TRAINER_CLASS_', '').replace(/_/g, ' ').toLowerCase().replace(/\b\w/g, c => c.toUpperCase())
    : ''
}

function MonRow({ mon, badge = null }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '4px 6px', borderRadius: '8px' }}>
      <Sprite speciesId={mon.species_id} size={40} />
      <div style={{ minWidth: 0 }}>
        <div style={{ fontSize: '0.85em', color: 'var(--text-primary)', fontWeight: mon.nickname ? 'bold' : 'normal' }}>
          {mon.nickname || mon.species_name || `#${mon.species_id}`}
          {mon.nickname && mon.species_name && (
            <span style={{ fontWeight: 'normal', color: 'var(--text-secondary)' }}> ({mon.species_name})</span>
          )}
        </div>
        <div style={{ fontSize: '0.72em', color: 'var(--text-secondary)' }}>
          {[mon.location_name, mon.level_met ? `Lv ${mon.level_met} met` : null].filter(Boolean).join(' · ') || ' '}
        </div>
      </div>
      {badge && (
        <span style={{ marginLeft: 'auto', fontSize: '0.68em', color: '#7ec8e3', border: '1px solid #7ec8e3', borderRadius: '999px', padding: '2px 8px', flexShrink: 0 }}>
          {badge}
        </span>
      )}
    </div>
  )
}

function AttemptSummary() {
  const { runId, attemptId } = useParams()
  const navigate = useNavigate()
  const [summary, setSummary] = useState(null)
  const [loaded, setLoaded] = useState(false)
  const [loadError, setLoadError] = useState('')
  const [actionError, setActionError] = useState('')

  useEffect(() => {
    let cancelled = false
    setSummary(null)
    setLoaded(false)
    setLoadError('')
    getAttemptSummary(runId, attemptId)
      .then(data => { if (!cancelled) { setSummary(data); setLoaded(true) } })
      .catch(err => {
        console.error('Failed to load attempt summary:', err)
        if (!cancelled) { setLoadError(err.message || 'Failed to load summary'); setLoaded(true) }
      })
    return () => { cancelled = true }
  }, [runId, attemptId])

  if (!loaded) return <p style={{ padding: '40px', textAlign: 'center' }}>Loading...</p>
  if (!summary) {
    return (
      <p style={{ padding: '40px', textAlign: 'center' }}>
        {loadError ? `Could not load the summary (${loadError}). Try again in a moment.` : 'Attempt not found.'}
      </p>
    )
  }

  const { run, attempt, killer, badges, deaths, survivors, counts } = summary
  const ended = Boolean(attempt?.outcome)
  const endedDate = attempt?.ended_at ? new Date(attempt.ended_at).toLocaleDateString() : null
  const killerSprite = killer
    ? getTrainerSpriteSrc(killer.trainer_pic, killer.trainer_class, killer.trainer_name, run?.game_id, null, run?.generation)
    : null
  const party = survivors.filter(m => m.party_slot != null)
  const boxed = survivors.filter(m => m.party_slot == null)

  const handleNewAttempt = () => {
    setActionError('')
    createAttempt(runId)
      .then(data => { window.location.href = `/attempt/${runId}/${data.attempt_number}` })
      .catch(err => setActionError(err.message || 'Failed to create attempt'))
  }

  const handleReopen = () => {
    setActionError('')
    reopenAttempt(runId, attemptId)
      .then(() => { window.location.href = `/attempt/${runId}/${attemptId}` })
      .catch(err => setActionError(err.message || 'Failed to reopen attempt'))
  }

  return (
    <div style={{ maxWidth: '860px', margin: '0 auto', padding: '36px 20px 60px', textAlign: 'left' }}>
      {/* Hero */}
      <div style={{ textAlign: 'center', marginBottom: '20px' }}>
        <div style={{ fontSize: '0.85em', color: 'var(--text-secondary)' }}>
          {run?.name} · {run?.game_name} · Attempt {attempt?.attempt_number}
        </div>
        <div style={{ fontSize: '1.65em', fontWeight: 'bold', color: ended ? '#e05252' : 'var(--text-primary)', marginTop: '4px' }}>
          {ended ? 'The run has fallen' : 'Attempt in progress'}
        </div>
        {endedDate && (
          <div style={{ fontSize: '0.8em', color: 'var(--text-secondary)', marginTop: '2px' }}>{endedDate}</div>
        )}
      </div>

      {/* Killer */}
      {killer && (
        <div style={{ ...CARD, display: 'flex', alignItems: 'center', gap: '14px', marginBottom: '14px', borderColor: '#5a2d2d' }}>
          {killerSprite && (
            <img
              src={killerSprite}
              alt={killer.trainer_name || 'Trainer'}
              style={{ width: '64px', height: '64px', objectFit: 'contain', imageRendering: 'pixelated' }}
              onError={(e) => { e.currentTarget.style.display = 'none' }}
            />
          )}
          <div>
            <div style={{ fontSize: '0.72em', color: '#e05252', letterSpacing: '0.08em', textTransform: 'uppercase' }}>Defeated by</div>
            <div style={{ fontWeight: 'bold', color: 'var(--text-primary)', fontSize: '1.05em' }}>
              {[formatClass(killer.trainer_class), killer.trainer_name].filter(Boolean).join(' ')}
            </div>
            {killer.location_name && (
              <div style={{ fontSize: '0.8em', color: 'var(--text-secondary)' }}>{killer.location_name}</div>
            )}
          </div>
        </div>
      )}
      {attempt?.death_note && (
        <div style={{ ...CARD, marginBottom: '14px', fontSize: '0.88em', color: 'var(--text-secondary)', fontStyle: 'italic' }}>
          “{attempt.death_note}”
        </div>
      )}

      {/* Counts + badges */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))', gap: '10px', marginBottom: '14px' }}>
        {[
          { label: 'Badges', value: badges.length },
          { label: 'Trainers Defeated', value: counts?.trainers_defeated ?? 0 },
          { label: 'Caught', value: counts?.captured ?? 0 },
          { label: 'Fallen', value: counts?.dead ?? 0 },
          { label: 'Missed', value: counts?.missed ?? 0 },
        ].map(stat => (
          <div key={stat.label} style={{ ...CARD, textAlign: 'center', padding: '10px' }}>
            <div style={{ fontSize: '1.35em', fontWeight: 'bold', color: 'var(--text-primary)' }}>{stat.value}</div>
            <div style={{ fontSize: '0.72em', color: 'var(--text-secondary)' }}>{stat.label}</div>
          </div>
        ))}
      </div>
      {badges.length > 0 && (
        <div style={{ ...CARD, display: 'flex', gap: '10px', flexWrap: 'wrap', alignItems: 'center', marginBottom: '14px' }}>
          {badges.map(b => (
            <img
              key={b.badge_id}
              src={`/sprites/Badges/${b.badge_id}.png`}
              alt={b.badge_name || `Badge ${b.badge_id}`}
              title={b.badge_name || undefined}
              width={30}
              height={30}
              style={{ imageRendering: 'pixelated' }}
              onError={(e) => { e.currentTarget.style.display = 'none' }}
            />
          ))}
        </div>
      )}

      {/* Fallen + survivors */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '14px', marginBottom: '22px' }}>
        <div style={CARD}>
          <div style={{ fontWeight: 'bold', color: '#e05252', marginBottom: '8px', fontSize: '0.9em' }}>The Fallen ({deaths.length})</div>
          {deaths.length
            ? deaths.map(mon => <MonRow key={mon.pokemon_id ?? `${mon.species_id}-${mon.nickname}`} mon={mon} />)
            : <div style={{ fontSize: '0.82em', color: 'var(--text-secondary)' }}>No casualties recorded.</div>}
        </div>
        <div style={CARD}>
          <div style={{ fontWeight: 'bold', color: '#5ba85b', marginBottom: '8px', fontSize: '0.9em' }}>Survivors ({survivors.length})</div>
          {party.map(mon => <MonRow key={mon.pokemon_id ?? `${mon.species_id}-${mon.nickname}`} mon={mon} badge="Party" />)}
          {boxed.map(mon => <MonRow key={mon.pokemon_id ?? `${mon.species_id}-${mon.nickname}`} mon={mon} />)}
          {!survivors.length && <div style={{ fontSize: '0.82em', color: 'var(--text-secondary)' }}>Nobody made it out.</div>}
        </div>
      </div>

      {/* Actions */}
      <div style={{ display: 'flex', gap: '10px', justifyContent: 'center', flexWrap: 'wrap' }}>
        <button type="button" style={ACTION} onClick={() => navigate(`/attempt/${runId}/${attemptId}`)}>
          Review Attempt
        </button>
        <button type="button" style={{ ...ACTION, borderColor: '#5ba85b', color: '#5ba85b', background: 'rgba(91,168,91,0.12)' }} onClick={handleNewAttempt}>
          + New Attempt
        </button>
        {ended && (
          <button type="button" style={ACTION} onClick={handleReopen} title="Undo the death declaration">
            Reopen Attempt
          </button>
        )}
        <button type="button" style={ACTION} onClick={() => navigate('/')}>
          Main Menu
        </button>
      </div>
      {actionError && (
        <div style={{ textAlign: 'center', marginTop: '10px', fontSize: '0.8em', color: '#e05252' }}>{actionError}</div>
      )}
    </div>
  )
}

export default AttemptSummary
