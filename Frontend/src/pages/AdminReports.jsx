import { useEffect, useMemo, useState } from 'react'
import SiteHeader from '../components/SiteHeader'
import { useAuth } from '../contexts/AuthContext'
import { getContactReports, getContactReportStats, updateContactReport } from '../utils/dataLayer'
import { apiFetch } from '../utils/api'

const STATUS_OPTIONS = ['open', 'reviewing', 'resolved', 'closed']
const PRIORITY_OPTIONS = ['low', 'normal', 'high']

const REPORT_LABELS = {
  bug: 'Bug',
  missing_information: 'Missing info',
  incorrect_information: 'Incorrect info',
  general_contact: 'General',
}

const STAT_COLUMNS = [
  { key: 'game_name', label: 'Game', type: 'text' },
  { key: 'generation', label: 'Gen', type: 'number' },
  { key: 'version_group_id', label: 'Version', type: 'number' },
  { key: 'total_reports', label: 'Total', type: 'number' },
  { key: 'general_count', label: 'General', type: 'number' },
  { key: 'bug_count', label: 'Bug', type: 'number' },
  { key: 'missing_count', label: 'Missing', type: 'number' },
  { key: 'incorrect_count', label: 'Incorrect', type: 'number' },
]

function formatReportId(reportId) {
  return `#${String(reportId || 0).padStart(4, '0')}`
}

function reportTypeClass(reportType) {
  return `admin-report-type-pill admin-report-type-pill--${reportType || 'unknown'}`
}

function AdminReports() {
  const { user, loading } = useAuth()
  const [activeView, setActiveView] = useState('reports')
  const [reports, setReports] = useState([])
  const [statusFilter, setStatusFilter] = useState('open')
  const [gameFilter, setGameFilter] = useState('')
  const [versionFilter, setVersionFilter] = useState('')
  const [generationFilter, setGenerationFilter] = useState('')
  const [games, setGames] = useState([])
  const [stats, setStats] = useState([])
  const [statsSort, setStatsSort] = useState({ key: 'total_reports', direction: 'desc' })
  const [activeReportId, setActiveReportId] = useState(null)
  const [savingId, setSavingId] = useState(null)
  const [error, setError] = useState('')

  const activeReport = useMemo(
    () => reports.find(report => report.report_id === activeReportId) || reports[0] || null,
    [reports, activeReportId]
  )

  useEffect(() => {
    if (loading || user?.account_type !== 'admin') return
    let cancelled = false
    setError('')
    getContactReports({ status: statusFilter, gameId: gameFilter, versionGroupId: versionFilter })
      .then(data => {
        if (cancelled) return
        if (!Array.isArray(data)) {
          setReports([])
          setError(data?.error || 'Unable to load reports.')
          return
        }
        setReports(data)
        setActiveReportId(current => current && data.some(report => report.report_id === current) ? current : data[0]?.report_id || null)
      })
      .catch(err => {
        if (!cancelled) setError(err.message || 'Unable to load reports.')
      })
    return () => { cancelled = true }
  }, [loading, user, statusFilter, gameFilter, versionFilter])

  useEffect(() => {
    if (loading || user?.account_type !== 'admin') return
    let cancelled = false
    apiFetch('/api/games')
      .then(response => response.json())
      .then(data => {
        if (!cancelled) setGames(Array.isArray(data) ? data : [])
      })
      .catch(() => {
        if (!cancelled) setGames([])
      })
    return () => { cancelled = true }
  }, [loading, user])

  useEffect(() => {
    if (loading || user?.account_type !== 'admin' || activeView !== 'statistics') return
    let cancelled = false
    setError('')
    getContactReportStats(generationFilter)
      .then(data => {
        if (!cancelled) setStats(Array.isArray(data) ? data : [])
      })
      .catch(err => {
        if (!cancelled) setError(err.message || 'Unable to load statistics.')
      })
    return () => { cancelled = true }
  }, [loading, user, activeView, generationFilter])

  const generations = useMemo(
    () => Array.from(new Set(games.map(game => Number(game.generation)).filter(Number.isFinite))).sort((a, b) => a - b),
    [games]
  )
  const versionOptions = useMemo(() => {
    const byVersion = new Map()
    games.forEach(game => {
      const versionGroupId = Number(game.version_group_id)
      if (!Number.isFinite(versionGroupId)) return
      const existing = byVersion.get(versionGroupId)
      byVersion.set(versionGroupId, {
        version_group_id: versionGroupId,
        generation: Number(game.generation),
        label: existing ? `${existing.label} / ${game.name}` : game.name,
      })
    })
    return Array.from(byVersion.values()).sort((a, b) => {
      const generationDiff = Number(a.generation) - Number(b.generation)
      if (generationDiff !== 0) return generationDiff
      return Number(a.version_group_id) - Number(b.version_group_id)
    })
  }, [games])
  const sortedStats = useMemo(() => {
    const column = STAT_COLUMNS.find(entry => entry.key === statsSort.key) || STAT_COLUMNS[3]
    const direction = statsSort.direction === 'asc' ? 1 : -1
    return [...stats].sort((left, right) => {
      if (column.type === 'text') {
        return String(left[column.key] || '').localeCompare(String(right[column.key] || '')) * direction
      }
      const leftValue = Number(left[column.key] || 0)
      const rightValue = Number(right[column.key] || 0)
      const diff = leftValue - rightValue
      if (diff !== 0) return diff * direction
      return String(left.game_name || '').localeCompare(String(right.game_name || ''))
    })
  }, [stats, statsSort])

  const handleStatsSort = (key) => {
    setStatsSort(current => ({
      key,
      direction: current.key === key && current.direction === 'desc' ? 'asc' : 'desc',
    }))
  }

  const patchReport = async (reportId, patch) => {
    setSavingId(reportId)
    setError('')
    try {
      const result = await updateContactReport(reportId, patch)
      if (!result?.success) throw new Error(result?.error || 'Unable to update report.')
      setReports(prev => prev.map(report => report.report_id === reportId ? { ...report, ...patch } : report))
    } catch (err) {
      setError(err.message || 'Unable to update report.')
    } finally {
      setSavingId(null)
    }
  }

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
            <div className="admin-reports-view-tabs">
              <button
                type="button"
                className={`admin-reports-view-tab${activeView === 'reports' ? ' is-active' : ''}`}
                onClick={() => setActiveView('reports')}
              >
                Reports
              </button>
              <button
                type="button"
                className={`admin-reports-view-tab${activeView === 'statistics' ? ' is-active' : ''}`}
                onClick={() => setActiveView('statistics')}
              >
                Statistics
              </button>
            </div>
            <p>{activeView === 'reports' ? `${reports.length} report${reports.length === 1 ? '' : 's'} in view` : `${stats.length} game${stats.length === 1 ? '' : 's'} in view`}</p>
          </div>
          {activeView === 'reports' ? (
            <div className="admin-report-filters">
              <select value={statusFilter} onChange={event => setStatusFilter(event.target.value)}>
                {STATUS_OPTIONS.map(status => (
                  <option key={status} value={status}>{status}</option>
                ))}
              </select>
              <select value={generationFilter} onChange={event => { setGenerationFilter(event.target.value); setGameFilter(''); setVersionFilter('') }}>
                <option value="">All generations</option>
                {generations.map(generation => (
                  <option key={generation} value={generation}>Gen {generation}</option>
                ))}
              </select>
              <select value={versionFilter} onChange={event => { setVersionFilter(event.target.value); setGameFilter('') }}>
                <option value="">All versions</option>
                {versionOptions
                  .filter(version => !generationFilter || Number(version.generation) === Number(generationFilter))
                  .map(version => (
                    <option key={version.version_group_id} value={version.version_group_id}>{version.label}</option>
                  ))}
              </select>
              <select value={gameFilter} onChange={event => { setGameFilter(event.target.value); setVersionFilter('') }}>
                <option value="">All games</option>
                {games
                  .filter(game => !generationFilter || Number(game.generation) === Number(generationFilter))
                  .map(game => (
                    <option key={game.game_id} value={game.game_id}>Pokemon {game.name}</option>
                  ))}
              </select>
            </div>
          ) : (
            <select value={generationFilter} onChange={event => setGenerationFilter(event.target.value)}>
              <option value="">All generations</option>
              {generations.map(generation => (
                <option key={generation} value={generation}>Gen {generation}</option>
              ))}
            </select>
          )}
        </div>

        {error && <div className="contact-panel__status contact-panel__status--error">{error}</div>}

        {activeView === 'reports' ? (
          <div className="admin-reports-layout">
          <div className="admin-reports-list">
            {reports.map(report => (
              <button
                key={report.report_id}
                type="button"
                className={`admin-report-list-item${activeReport?.report_id === report.report_id ? ' is-active' : ''}`}
                onClick={() => setActiveReportId(report.report_id)}
              >
                <div className="admin-report-list-item__top">
                  <span className={reportTypeClass(report.report_type)}>{REPORT_LABELS[report.report_type] || report.report_type}</span>
                  <span className="admin-report-id">{formatReportId(report.report_id)}</span>
                </div>
                <strong>{report.title || report.details.slice(0, 80)}</strong>
                <small>{report.game_name || 'No game'} · {report.created_at}</small>
              </button>
            ))}
            {reports.length === 0 && <div className="admin-reports-empty">No reports here.</div>}
          </div>

          {activeReport && (
            <section className="admin-report-detail">
              <div className="admin-report-detail__header">
                <div>
                  <div className="admin-report-detail__identity">
                    <span className={reportTypeClass(activeReport.report_type)}>{REPORT_LABELS[activeReport.report_type] || activeReport.report_type}</span>
                    <span className="admin-report-id">{formatReportId(activeReport.report_id)}</span>
                  </div>
                  <h2>{activeReport.title || 'Untitled report'}</h2>
                </div>
                <div className="admin-report-detail__controls">
                  <select
                    value={activeReport.status}
                    disabled={savingId === activeReport.report_id}
                    onChange={event => patchReport(activeReport.report_id, { status: event.target.value })}
                  >
                    {STATUS_OPTIONS.map(status => <option key={status} value={status}>{status}</option>)}
                  </select>
                  <select
                    value={activeReport.priority}
                    disabled={savingId === activeReport.report_id}
                    onChange={event => patchReport(activeReport.report_id, { priority: event.target.value })}
                  >
                    {PRIORITY_OPTIONS.map(priority => <option key={priority} value={priority}>{priority}</option>)}
                  </select>
                </div>
              </div>

              <div className="admin-report-detail__section">
                <h3>Report</h3>
                <p>{activeReport.details}</p>
                {activeReport.reproduction_steps && (
                  <>
                    <h3>Recreate</h3>
                    <p>{activeReport.reproduction_steps}</p>
                  </>
                )}
              </div>

              <div className="admin-report-context">
                <span>topic: {activeReport.topic || 'none'}</span>
                <span>user_id: {activeReport.user_id || 'anonymous'}</span>
                <span>game_id: {activeReport.game_id || 'none'}</span>
                <span>version_group_id: {activeReport.version_group_id || 'none'}</span>
                <span>run_id: {activeReport.run_id || 'none'}</span>
                <span>attempt: {activeReport.attempt_number || 'none'}</span>
              </div>

              <label className="admin-report-notes">
                <span>Admin notes</span>
                <textarea
                  value={activeReport.admin_notes || ''}
                  onChange={event => setReports(prev => prev.map(report => report.report_id === activeReport.report_id ? { ...report, admin_notes: event.target.value } : report))}
                  onBlur={event => patchReport(activeReport.report_id, { admin_notes: event.target.value })}
                />
              </label>

              {activeReport.page_url && (
                <a className="admin-report-page-link" href={activeReport.page_url} target="_blank" rel="noreferrer">
                  Open reported page
                </a>
              )}
            </section>
          )}
          </div>
        ) : (
          <div className="admin-report-stats">
            <table className="admin-report-stats-table">
              <thead>
                <tr>
                  {STAT_COLUMNS.map(column => (
                    <th key={column.key}>
                      <button
                        type="button"
                        className={`admin-report-stats-sort${statsSort.key === column.key ? ' is-active' : ''}`}
                        onClick={() => handleStatsSort(column.key)}
                      >
                        <span>{column.label}</span>
                        <span aria-hidden="true">{statsSort.key === column.key ? (statsSort.direction === 'desc' ? '↓' : '↑') : '↕'}</span>
                      </button>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {sortedStats.map(row => (
                  <tr key={`${row.game_id || 'none'}:${row.version_group_id || 'none'}`}>
                    <td>{row.game_name}</td>
                    <td>{row.generation || 'none'}</td>
                    <td>{row.version_group_id || 'none'}</td>
                    <td>{row.total_reports || 0}</td>
                    <td>{row.general_count || 0}</td>
                    <td>{row.bug_count || 0}</td>
                    <td>{row.missing_count || 0}</td>
                    <td>{row.incorrect_count || 0}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            {stats.length === 0 && <div className="admin-reports-empty">No statistics available.</div>}
          </div>
        )}
      </div>
    </div>
  )
}

export default AdminReports
