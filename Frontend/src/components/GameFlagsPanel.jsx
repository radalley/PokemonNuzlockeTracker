import { useState } from 'react'
import { saveGate } from '../utils/dataLayer'
import { methodMeta } from '../utils/encounterTables'
import { splitInitial } from '../utils/splitFeed'
import { Button } from './Button'

// The admin Game flags panel: one row per gate the game knows (Surf, the
// rod, shaking grass), each with the split it opens in. Saving re-resolves
// every table behind that gate on the page. Future flags are new gate
// rows, not new UI.
export default function GameFlagsPanel({ gameId, gameName = '', splits = [], gates = [], index = new Map(), encounterMethods = [], onClose = null, onSaved = null }) {
  const [busy, setBusy] = useState(null)
  const [error, setError] = useState('')

  const pick = async (gate, opensIn) => {
    if (busy) return
    setBusy(gate.gate_key); setError('')
    try {
      await saveGate(gameId, gate.gate_key, opensIn)
      onSaved?.()
    } catch (err) { setError(err.message) }
    finally { setBusy(null) }
  }

  return (
    <aside className="game-flags" aria-label="Game flags">
      <div className="game-flags__head">
        <b>Game flags</b>
        <span>{gameName}</span>
        {onClose && <Button size="sm" onClick={onClose} aria-label="Close game flags">Close</Button>}
      </div>
      {gates.length === 0 ? (
        <div>No flags for this game. Flags are gates on encounter methods; this game has none configured.</div>
      ) : gates.map(gate => {
        const methods = (gate.default_methods || []).map(key => methodMeta(encounterMethods, key).label).join(' · ')
        const resolved = gate.opens_in ? index.get(gate.opens_in) : null
        return (
          <div key={gate.gate_key} className="game-flags__gate">
            <div>
              <b>{gate.label}</b>
              <small>{methods}</small>
              {gate.note && <small>{gate.note}</small>}
            </div>
            <div className="opens-in__row" role="group" aria-label={`${gate.label} opens in`}>
              <Button size="sm" tone="accent" selected={!gate.opens_in} aria-pressed={!gate.opens_in} disabled={busy === gate.gate_key} onClick={() => pick(gate, null)}>Not set</Button>
              {splits.map(split => (
                <button
                  key={split.split_key}
                  type="button"
                  className="opens-in__medal"
                  style={{ '--split-color': index.get(split.split_key)?.color || 'var(--border-strong)' }}
                  aria-pressed={gate.opens_in === split.split_key}
                  aria-label={`${gate.label} opens in ${split.label}`}
                  title={split.label}
                  disabled={busy === gate.gate_key}
                  onClick={() => pick(gate, split.split_key)}
                >
                  {splitInitial(split)}
                </button>
              ))}
            </div>
            <div className="game-flags__status">
              {busy === gate.gate_key ? 'Saving…' : resolved ? `Opens in ${resolved.label}` : 'Split not set: tables behind this gate show as “not set”.'}
            </div>
          </div>
        )
      })}
      {error && <div role="alert" style={{ color: '#e05252' }}>{error}</div>}
    </aside>
  )
}
