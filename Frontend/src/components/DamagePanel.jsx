import { useEffect, useMemo, useRef, useState } from 'react'
import { apiFetch } from '../utils/api'
import { loadCalcEngine, toCalcPokemon, calcMatchup, opponentMoveRows } from '../utils/battleCalc'

// In-app damage readouts for the battle modal: their known moves against
// your selected mon, and your strongest learnset answers against theirs.
// Math by @smogon/calc, data entirely from our own database.

function DamageRow({ entry, accent }) {
  return (
    <div style={{ display: 'flex', alignItems: 'baseline', gap: '8px', padding: '3px 0', borderBottom: '1px solid var(--border)', fontSize: '0.76em' }}>
      <span style={{ minWidth: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', color: 'var(--text-primary)' }}>
        {entry.name}
        {entry.seen && <span style={{ marginLeft: '5px', fontSize: '0.85em', color: '#5ba85b' }}>seen</span>}
        {entry.learnLevel != null && (
          <span style={{ marginLeft: '5px', fontSize: '0.85em', color: 'var(--text-secondary)' }}>
            {entry.learnLevel === 0 ? '@Evo' : `@L${entry.learnLevel}`}
          </span>
        )}
      </span>
      <span style={{ marginLeft: 'auto', whiteSpace: 'nowrap', fontWeight: 'bold', color: entry.status ? 'var(--text-secondary)' : accent }}>
        {entry.status ? 'status' : `${entry.minPct}–${entry.maxPct}%`}
      </span>
      {!entry.status && entry.koText && (
        <span style={{ whiteSpace: 'nowrap', fontSize: '0.85em', color: 'var(--text-secondary)' }}>{entry.koText}</span>
      )}
    </div>
  )
}

function DamagePanel({ gameId, generation, playerMon, opponentMon, playerLevel }) {
  const [engine, setEngine] = useState(null)
  const [engineFailed, setEngineFailed] = useState(false)
  const [engineAttempt, setEngineAttempt] = useState(0)
  const [learnset, setLearnset] = useState(null)
  const learnsetSeqRef = useRef(0)

  useEffect(() => {
    let active = true
    setEngineFailed(false)
    loadCalcEngine()
      .then(mod => { if (active) setEngine(mod) })
      .catch(() => { if (active) setEngineFailed(true) })
    return () => { active = false }
  }, [engineAttempt])

  useEffect(() => {
    const speciesId = playerMon?.species_id
    if (!speciesId) { setLearnset(null); return }
    const seq = ++learnsetSeqRef.current
    setLearnset(null)
    const query = gameId ? `?game_id=${gameId}` : ''
    apiFetch(`/api/species/${speciesId}/learnset${query}`)
      .then(res => res.ok ? res.json() : null)
      .then(data => {
        if (seq !== learnsetSeqRef.current) return
        setLearnset(Array.isArray(data?.moves) ? data.moves : [])
      })
      .catch(() => { if (seq === learnsetSeqRef.current) setLearnset([]) })
  }, [playerMon?.species_id, gameId])

  const computed = useMemo(() => {
    if (!engine || !playerMon || !opponentMon) return null
    const gen = engine.Generations.get(Math.min(9, Math.max(1, Number(generation) || 5)))
    const mine = toCalcPokemon(engine, gen, playerMon, { level: playerLevel, isPlayer: true })
    const theirs = toCalcPokemon(engine, gen, opponentMon, { level: opponentMon.lvl, isPlayer: false })
    if (!mine || !theirs) return { failed: true }

    const incoming = calcMatchup(engine, gen, theirs, mine, opponentMoveRows(opponentMon))

    // Your side: the learnset up to the battle's level, one row per move
    // (latest learn wins), strongest answers first.
    let outgoing = null
    if (learnset) {
      const level = Number(playerLevel) || 100
      const byName = new Map()
      for (const move of learnset) {
        if (Number(move.learn_level) > level) continue
        byName.set(String(move.move_name || '').toLowerCase(), move)
      }
      outgoing = calcMatchup(engine, gen, mine, theirs, [...byName.values()])
        .filter(entry => !entry.status)
        .sort((a, b) => b.maxPct - a.maxPct)
        .slice(0, 6)
    }
    return { incoming, outgoing }
  }, [engine, playerMon, opponentMon, playerLevel, generation, learnset])

  if (engineFailed) {
    return (
      <div style={{ marginTop: '12px', fontSize: '0.74em', color: 'var(--text-secondary)' }}>
        Damage calc failed to load.{' '}
        <button
          type="button"
          onClick={() => setEngineAttempt(n => n + 1)}
          style={{ font: 'inherit', color: '#7ec8e3', background: 'none', border: 'none', cursor: 'pointer', padding: 0, textDecoration: 'underline' }}
        >
          Retry
        </button>
      </div>
    )
  }
  if (!computed) {
    return <div style={{ marginTop: '12px', fontSize: '0.74em', color: 'var(--text-secondary)' }}>Loading damage calc…</div>
  }
  if (computed.failed) {
    return <div style={{ marginTop: '12px', fontSize: '0.74em', color: 'var(--text-secondary)' }}>Damage calc unavailable for this matchup.</div>
  }

  return (
    <div style={{ marginTop: '14px', borderTop: '1px solid var(--border-strong)', paddingTop: '10px' }}>
      <div style={{ fontSize: '0.74em', fontWeight: 'bold', color: '#f2b46b', marginBottom: '3px' }}>
        Their moves vs {playerMon.nickname || playerMon.species_name}
      </div>
      {computed.incoming.length === 0 ? (
        <div style={{ fontSize: '0.74em', color: 'var(--text-secondary)' }}>No known moves.</div>
      ) : (
        computed.incoming.map((entry, idx) => <DamageRow key={`in-${idx}`} entry={entry} accent="#f2b46b" />)
      )}

      <div style={{ fontSize: '0.74em', fontWeight: 'bold', color: '#7ec8e3', margin: '10px 0 3px' }}>
        Your best answers vs {opponentMon.species_name}
      </div>
      {computed.outgoing == null ? (
        <div style={{ fontSize: '0.74em', color: 'var(--text-secondary)' }}>Loading learnset…</div>
      ) : computed.outgoing.length === 0 ? (
        <div style={{ fontSize: '0.74em', color: 'var(--text-secondary)' }}>No damaging level-up moves at this level.</div>
      ) : (
        computed.outgoing.map((entry, idx) => <DamageRow key={`out-${idx}`} entry={entry} accent="#7ec8e3" />)
      )}

      <div style={{ marginTop: '8px', fontSize: '0.66em', color: 'var(--text-secondary)' }}>
        Assumes your team at Lvl {playerLevel || '?'}, 31 IVs where unrecorded, 0 EVs both sides, 31 IVs for the opponent. Your list is level-up moves only.
      </div>
    </div>
  )
}

export default DamagePanel
