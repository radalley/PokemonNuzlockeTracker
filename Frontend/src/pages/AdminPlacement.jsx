import { useCallback, useEffect, useMemo, useState } from 'react'
import SiteHeader from '../components/SiteHeader'
import { useAuth } from '../contexts/AuthContext'
import { apiFetch } from '../utils/api'

const PAGE_SIZE = 100

const SOURCE_LABELS = {
  candidate_note: 'extractor',
  map_reference: 'map',
  serebii: 'serebii',
}

function formatClass(trainerClass) {
  return (trainerClass || '')
    .replace('TRAINER_CLASS_', '')
    .replace(/_/g, ' ')
    .toLowerCase()
    .replace(/\b\w/g, c => c.toUpperCase())
}

// A trainer is auto-acceptable when every suggestion agrees on one location
// that is actually in this game's script.
function unambiguousSuggestion(trainer) {
  const inScript = (trainer.suggestions || []).filter(s => s.in_script)
  if (!inScript.length) return null
  const locations = new Set(inScript.map(s => s.canonical_location_id))
  if (locations.size !== 1) return null
  return inScript.find(s => s.area_name) || inScript[0]
}

function AdminPlacement() {
  const { user, loading } = useAuth()
  const [summary, setSummary] = useState([])
  const [games, setGames] = useState([])
  const [versionGroupId, setVersionGroupId] = useState(null)
  const [trainers, setTrainers] = useState([])
  const [hasMore, setHasMore] = useState(false)
  const [onlySuggested, setOnlySuggested] = useState(true)
  const [busyKeys, setBusyKeys] = useState(() => new Set())
  const [bulkBusy, setBulkBusy] = useState(false)
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')

  const isAdmin = !loading && user?.account_type === 'admin'

  const loadSummary = useCallback(() => {
    apiFetch('/api/admin/placement/summary')
      .then(res => res.json())
      .then(data => setSummary(Array.isArray(data) ? data : []))
      .catch(() => setSummary([]))
  }, [])

  useEffect(() => {
    if (!isAdmin) return
    loadSummary()
    apiFetch('/api/games')
      .then(res => res.json())
      .then(data => setGames(Array.isArray(data) ? data : []))
      .catch(() => setGames([]))
  }, [isAdmin, loadSummary])

  const versionLabels = useMemo(() => {
    const byVersion = new Map()
    games.forEach(game => {
      const vg = Number(game.version_group_id)
      if (!Number.isFinite(vg)) return
      const existing = byVersion.get(vg)
      byVersion.set(vg, existing ? `${existing} / ${game.name}` : game.name)
    })
    return byVersion
  }, [games])

  const loadTrainers = useCallback((vg, offset = 0, append = false) => {
    if (vg == null) return
    apiFetch(`/api/admin/placement/unplaced?version_group_id=${vg}&limit=${PAGE_SIZE}&offset=${offset}&only_suggested=${onlySuggested ? 1 : 0}`)
      .then(res => res.json())
      .then(data => {
        if (!Array.isArray(data)) {
          setError(data?.error || 'Unable to load trainers.')
          return
        }
        setTrainers(prev => append ? [...prev, ...data] : data)
        setHasMore(data.length === PAGE_SIZE)
      })
      .catch(err => setError(err.message || 'Unable to load trainers.'))
  }, [onlySuggested])

  useEffect(() => {
    if (!isAdmin || versionGroupId == null) return
    setTrainers([])
    setMessage('')
    setError('')
    loadTrainers(versionGroupId, 0, false)
  }, [isAdmin, versionGroupId, loadTrainers])

  const applyPlacements = useCallback(async (placements) => {
    const res = await apiFetch('/api/admin/placement', {
      method: 'POST',
      body: JSON.stringify({ version_group_id: versionGroupId, placements }),
    })
    const data = await res.json()
    if (!res.ok || !data?.success) throw new Error(data?.error || 'Placement failed.')
    return data.applied
  }, [versionGroupId])

  const placeOne = useCallback(async (trainer, suggestion) => {
    setError('')
    setBusyKeys(prev => new Set(prev).add(trainer.encounter_name))
    try {
      await applyPlacements([{
        trainer_key: trainer.encounter_name,
        canonical_location_id: suggestion.canonical_location_id,
        area_name: suggestion.area_name || undefined,
      }])
      setTrainers(prev => prev.filter(t => t.encounter_name !== trainer.encounter_name))
      setMessage(`Placed ${trainer.trainer_name || trainer.encounter_name} at ${suggestion.location_name}.`)
      loadSummary()
    } catch (err) {
      setError(err.message)
    } finally {
      setBusyKeys(prev => {
        const next = new Set(prev)
        next.delete(trainer.encounter_name)
        return next
      })
    }
  }, [applyPlacements, loadSummary])

  const autoAcceptable = useMemo(
    () => trainers
      .map(trainer => ({ trainer, suggestion: unambiguousSuggestion(trainer) }))
      .filter(entry => entry.suggestion),
    [trainers]
  )

  const acceptAllUnambiguous = useCallback(async () => {
    if (!autoAcceptable.length) return
    setError('')
    setBulkBusy(true)
    try {
      const applied = await applyPlacements(autoAcceptable.map(({ trainer, suggestion }) => ({
        trainer_key: trainer.encounter_name,
        canonical_location_id: suggestion.canonical_location_id,
        area_name: suggestion.area_name || undefined,
      })))
      const placedKeys = new Set(applied.map(entry => entry.trainer_key))
      setTrainers(prev => prev.filter(t => !placedKeys.has(t.encounter_name)))
      setMessage(`Placed ${applied.length} trainers.`)
      loadSummary()
    } catch (err) {
      setError(err.message)
    } finally {
      setBulkBusy(false)
    }
  }, [autoAcceptable, applyPlacements, loadSummary])

  if (loading) {
    return <div className="admin-reports-page"><SiteHeader showHomeButton /><p>Loading...</p></div>
  }
  if (user?.account_type !== 'admin') {
    return (
      <div className="admin-reports-page">
        <SiteHeader showHomeButton />
        <div className="admin-reports-empty">Admin access required.</div>
      </div>
    )
  }

  return (
    <div className="admin-reports-page">
      <SiteHeader showHomeButton />
      <div className="admin-reports-shell">
        <div className="admin-reports-toolbar">
          <div>
            <h2 style={{ margin: 0 }}>Trainer placement</h2>
            <p>Assign unplaced trainers to their locations. Decisions persist across data reloads.</p>
          </div>
        </div>

        <div style={{ width: '100%', overflowX: 'auto' }}>
        <table style={{ width: '100%', minWidth: '760px', borderCollapse: 'collapse', fontSize: '0.9em' }}>
          <thead>
            <tr style={{ textAlign: 'left', color: 'var(--text-secondary)' }}>
              <th style={{ padding: '6px' }}>Version</th>
              <th style={{ padding: '6px', textAlign: 'right' }}>Trainers</th>
              <th style={{ padding: '6px', textAlign: 'right' }}>Placed</th>
              <th style={{ padding: '6px', textAlign: 'right' }}>Gaps</th>
              <th style={{ padding: '6px', textAlign: 'right' }}>Boss-linked</th>
              <th style={{ padding: '6px', textAlign: 'right' }}>Excluded</th>
              <th style={{ padding: '6px', textAlign: 'right' }}>With suggestions</th>
              <th style={{ padding: '6px', textAlign: 'right' }}>Curated</th>
            </tr>
          </thead>
          <tbody>
            {summary.map(row => {
              const vg = Number(row.version_group_id)
              const selected = vg === versionGroupId
              return (
                <tr
                  key={vg}
                  onClick={() => setVersionGroupId(vg)}
                  style={{
                    cursor: 'pointer',
                    background: selected ? 'var(--accent-bg)' : 'transparent',
                    borderTop: '1px solid var(--border-strong)',
                  }}
                >
                  <td style={{ padding: '6px' }}>{versionLabels.get(vg) || `Version group ${vg}`}</td>
                  <td style={{ padding: '6px', textAlign: 'right' }}>{row.total_trainers}</td>
                  <td style={{ padding: '6px', textAlign: 'right' }}>{row.placed}</td>
                  <td style={{ padding: '6px', textAlign: 'right', color: Number(row.actionable_gaps ?? row.unplaced) > 0 ? '#e0a052' : '#5ba85b' }}>{row.actionable_gaps ?? row.unplaced}</td>
                  <td style={{ padding: '6px', textAlign: 'right' }}>{row.boss_linked ?? '-'}</td>
                  <td style={{ padding: '6px', textAlign: 'right' }}>{row.excluded ?? '-'}</td>
                  <td style={{ padding: '6px', textAlign: 'right' }}>{row.unplaced_with_suggestions}</td>
                  <td style={{ padding: '6px', textAlign: 'right' }}>{row.curated}</td>
                </tr>
              )
            })}
          </tbody>
        </table>
        </div>

        {versionGroupId != null && (
          <div style={{ marginTop: '18px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flexWrap: 'wrap', marginBottom: '10px' }}>
              <label style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.85em' }}>
                <input
                  type="checkbox"
                  checked={onlySuggested}
                  onChange={event => setOnlySuggested(event.target.checked)}
                />
                Only trainers with suggestions
              </label>
              <button
                type="button"
                disabled={bulkBusy || autoAcceptable.length === 0}
                onClick={acceptAllUnambiguous}
                style={{ padding: '6px 12px' }}
              >
                {bulkBusy ? 'Placing...' : `Accept ${autoAcceptable.length} unambiguous`}
              </button>
              {message && <span style={{ color: '#52c97a', fontSize: '0.85em' }}>{message}</span>}
              {error && <span style={{ color: '#e05252', fontSize: '0.85em' }}>{error}</span>}
            </div>

            {trainers.length === 0 ? (
              <div className="admin-reports-empty">No unplaced trainers in view.</div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                {trainers.map(trainer => (
                  <div
                    key={trainer.encounter_name}
                    style={{
                      border: '1px solid var(--border-strong)',
                      borderRadius: '10px',
                      padding: '10px 12px',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '12px',
                      flexWrap: 'wrap',
                      opacity: busyKeys.has(trainer.encounter_name) ? 0.5 : 1,
                    }}
                  >
                    <div style={{ minWidth: '220px' }}>
                      <div style={{ fontWeight: 600 }}>{trainer.trainer_name || trainer.encounter_name}</div>
                      <div style={{ fontSize: '0.78em', color: 'var(--text-secondary)' }}>
                        {formatClass(trainer.trainer_class)}
                        {trainer.is_rematch ? ' · rematch' : ''}
                        {' · '}{trainer.encounter_name}
                      </div>
                    </div>
                    <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
                      {(trainer.suggestions || []).length === 0 && (
                        <span style={{ fontSize: '0.8em', color: 'var(--text-secondary)' }}>No suggestions.</span>
                      )}
                      {(trainer.suggestions || []).map((suggestion, index) => (
                        <button
                          key={`${suggestion.canonical_location_id}-${suggestion.source}-${index}`}
                          type="button"
                          disabled={busyKeys.has(trainer.encounter_name)}
                          onClick={() => placeOne(trainer, suggestion)}
                          title={[
                            suggestion.detail,
                            suggestion.in_script ? null : 'Not in this game\'s route list; will not display until the script covers it.',
                          ].filter(Boolean).join(' — ')}
                          style={{
                            padding: '4px 10px',
                            borderRadius: '999px',
                            border: '1px solid var(--border-strong)',
                            background: suggestion.in_script ? 'var(--accent-bg)' : 'transparent',
                            opacity: suggestion.in_script ? 1 : 0.55,
                            fontSize: '0.8em',
                            cursor: 'pointer',
                          }}
                        >
                          {suggestion.location_name}
                          {suggestion.area_name ? ` · ${suggestion.area_name}` : ''}
                          <span style={{ opacity: 0.65 }}> ({SOURCE_LABELS[suggestion.source] || suggestion.source})</span>
                        </button>
                      ))}
                    </div>
                  </div>
                ))}
                {hasMore && (
                  <button
                    type="button"
                    onClick={() => loadTrainers(versionGroupId, trainers.length, true)}
                    style={{ padding: '8px' }}
                  >
                    Load more
                  </button>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

export default AdminPlacement
