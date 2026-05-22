import AttemptSessionStats from './AttemptSessionStats'

function AttemptSidePanel({ runId, attemptId, statsRefreshKey = 0, statsOpen = true, onToggleStats = null, starter = '', onStarterChange = null }) {
  return (
    <div style={{ position: 'fixed', left: 'max(8px, calc((100vw - 1380px) / 2 + 28px - 262px))', top: '120px', width: '250px', zIndex: 900 }}>
      <AttemptSessionStats
        runId={runId}
        attemptId={attemptId}
        refreshKey={statsRefreshKey}
        compact
        starter={starter}
        onStarterChange={onStarterChange}
        isOpen={statsOpen}
        onToggle={onToggleStats}
      />
    </div>
  )
}

export default AttemptSidePanel