import { useCallback, useState } from 'react'
import { rememberSeason, rememberedSeason } from './encounterTables'

/**
 * One Black/White season for a whole run, shared by every location's
 * encounter tables and remembered per run. The pick is keyed by run, so
 * opening another run reads that run's season rather than carrying one over.
 */
export default function useRunSeason(runId) {
  const [pick, setPick] = useState(() => ({ runId, season: rememberedSeason(runId) }))
  const season = pick.runId === runId ? pick.season : rememberedSeason(runId)
  const changeSeason = useCallback((next) => {
    setPick({ runId, season: next })
    rememberSeason(runId, next)
  }, [runId])
  return [season, changeSeason]
}
