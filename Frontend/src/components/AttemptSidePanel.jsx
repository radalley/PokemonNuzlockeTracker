import AttemptSessionStats from './AttemptSessionStats'

function AttemptSidePanel({ runId, attemptId, statsRefreshKey = 0, children }) {
  return (
    <div style={{ position: 'fixed', left: 'max(8px, calc((100vw - 1380px) / 2 + 28px - 262px))', top: '120px', width: '250px', zIndex: 900 }}>
      {children}
      <AttemptSessionStats runId={runId} attemptId={attemptId} refreshKey={statsRefreshKey} compact />
    </div>
  )
}

export default AttemptSidePanel